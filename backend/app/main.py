import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Set, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.game_engine import GameEngine, GameStatus, PlayerStatus
from app.mqtt_manager import MQTTManager
from app.logger import logger

# ── Singletons ─────────────────────────────────────────────────────────────
game = GameEngine()
mqtt = MQTTManager()
_ws_clients: Set[WebSocket] = set()
_loop: Optional[asyncio.AbstractEventLoop] = None


# ── WebSocket broadcast ────────────────────────────────────────────────────
async def broadcast(event_type: str):
    payload = json.dumps({'type': event_type, 'data': game.to_dict()})
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)
    try:
        mqtt.publish('blackjack/game/state', game.to_dict())
    except Exception as e:
        logger.warning(f'MQTT publish error: {e}')


def _mqtt_action_callback(player_id: str, action: str):
    """Called from MQTT thread when a player terminal sends hit/stand/bet:N/split/double."""
    if _loop is None:
        return
    if action == 'hit':
        asyncio.run_coroutine_threadsafe(_handle_hit(player_id), _loop)
    elif action == 'stand':
        asyncio.run_coroutine_threadsafe(_handle_stand(player_id), _loop)
    elif action == 'split':
        asyncio.run_coroutine_threadsafe(_handle_split(player_id), _loop)
    elif action == 'double':
        asyncio.run_coroutine_threadsafe(_handle_double(player_id), _loop)
    elif action.startswith('bet:'):
        try:
            amount = int(action.split(':', 1)[1])
            asyncio.run_coroutine_threadsafe(_handle_bet(player_id, amount), _loop)
        except ValueError:
            pass


async def _handle_hit(player_id: str):
    card = game.player_hit(player_id)
    if card:
        event = 'all_players_done' if game.all_players_done() else 'player_hit'
        await broadcast(event)
        player = game.get_player(player_id)
        if player:
            mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())


async def _handle_stand(player_id: str):
    if game.player_stand(player_id):
        event = 'all_players_done' if game.all_players_done() else 'player_stood'
        await broadcast(event)
        player = game.get_player(player_id)
        if player:
            mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())


async def _handle_split(player_id: str):
    if game.player_split(player_id):
        event = 'all_players_done' if game.all_players_done() else 'player_split'
        await broadcast(event)
        player = game.get_player(player_id)
        if player:
            mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())


async def _handle_double(player_id: str):
    card = game.player_double(player_id)
    if card is not None:
        event = 'all_players_done' if game.all_players_done() else 'player_doubled'
        await broadcast(event)
        player = game.get_player(player_id)
        if player:
            mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())


async def _handle_bet(player_id: str, amount: int):
    if game.place_bet(player_id, amount):
        await broadcast('bet_placed')
        player = game.get_player(player_id)
        if player:
            mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())


# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app_: FastAPI):
    global _loop
    _loop = asyncio.get_event_loop()
    mqtt.connect(action_callback=_mqtt_action_callback)
    logger.info('Blackjack game server started')
    yield
    mqtt.disconnect()


# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title='Blackjack IoT', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ── WebSocket endpoint ─────────────────────────────────────────────────────
@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    # Send current state immediately on connect
    await websocket.send_text(
        json.dumps({'type': 'game_state', 'data': game.to_dict()})
    )
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        _ws_clients.discard(websocket)


# ── REST API ───────────────────────────────────────────────────────────────

class AddPlayerRequest(BaseModel):
    name: str
    player_id: Optional[str] = None
    owner_token: Optional[str] = None


class BetRequest(BaseModel):
    amount: int


def _assert_owner(player_id: str, device_id: Optional[str]):
    """Raise 403 if device_id doesn't match the player's owner_token."""
    player = game.get_player(player_id)
    if player and player.owner_token and player.owner_token != device_id:
        raise HTTPException(403, 'Não autorizado — este jogador pertence a outro dispositivo')


@app.get('/health')
async def health():
    return {'status': 'ok', 'game_status': game.status.value}


@app.get('/game/state')
async def get_state():
    return game.to_dict()


@app.post('/game/players')
async def add_player(req: AddPlayerRequest):
    player_id = req.player_id or str(uuid.uuid4())[:8]
    if req.owner_token and game.get_player_by_owner(req.owner_token):
        raise HTTPException(409, 'Este dispositivo já possui um jogador nesta partida')
    if not game.add_player(player_id, req.name, owner_token=req.owner_token):
        raise HTTPException(400, 'Não foi possível adicionar jogador (jogo em andamento ou ID duplicado)')
    await broadcast('player_joined')
    return {'player_id': player_id, 'name': req.name}


@app.delete('/game/players/{player_id}')
async def remove_player(player_id: str):
    if not game.remove_player(player_id):
        raise HTTPException(400, 'Não foi possível remover jogador')
    await broadcast('player_removed')
    return {'ok': True}


@app.post('/game/players/{player_id}/bet')
async def place_bet(player_id: str, req: BetRequest, x_device_id: Optional[str] = Header(default=None)):
    _assert_owner(player_id, x_device_id)
    if not game.place_bet(player_id, req.amount):
        raise HTTPException(400, 'Aposta inválida (valor fora do saldo ou jogo em andamento)')
    await broadcast('bet_placed')
    player = game.get_player(player_id)
    if player:
        mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())
    return game.to_dict()


@app.post('/game/start')
async def start_round():
    if not game.start_round():
        raise HTTPException(400, 'Todos os jogadores precisam apostar antes de iniciar')
    await broadcast('round_started')
    # Notify each player of their hand via MQTT
    for p in game.to_dict()['players']:
        mqtt.publish(f"blackjack/player/{p['player_id']}/hand", p)
    return game.to_dict()


@app.post('/game/players/{player_id}/hit')
async def player_hit(player_id: str, x_device_id: Optional[str] = Header(default=None)):
    _assert_owner(player_id, x_device_id)
    card = game.player_hit(player_id)
    if card is None:
        raise HTTPException(400, 'Não foi possível pedir carta')
    event = 'all_players_done' if game.all_players_done() else 'player_hit'
    await broadcast(event)
    player = game.get_player(player_id)
    if player:
        mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())
    return game.to_dict()


@app.post('/game/players/{player_id}/stand')
async def player_stand(player_id: str, x_device_id: Optional[str] = Header(default=None)):
    _assert_owner(player_id, x_device_id)
    if not game.player_stand(player_id):
        raise HTTPException(400, 'Não foi possível parar')
    event = 'all_players_done' if game.all_players_done() else 'player_stood'
    await broadcast(event)
    player = game.get_player(player_id)
    if player:
        mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())
    return game.to_dict()


@app.post('/game/players/{player_id}/split')
async def player_split(player_id: str, x_device_id: Optional[str] = Header(default=None)):
    _assert_owner(player_id, x_device_id)
    if not game.player_split(player_id):
        raise HTTPException(400, 'Não foi possível fazer split')
    event = 'all_players_done' if game.all_players_done() else 'player_split'
    await broadcast(event)
    player = game.get_player(player_id)
    if player:
        mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())
    return game.to_dict()


@app.post('/game/players/{player_id}/double')
async def player_double(player_id: str, x_device_id: Optional[str] = Header(default=None)):
    _assert_owner(player_id, x_device_id)
    card = game.player_double(player_id)
    if card is None:
        raise HTTPException(400, 'Não foi possível dobrar')
    event = 'all_players_done' if game.all_players_done() else 'player_doubled'
    await broadcast(event)
    player = game.get_player(player_id)
    if player:
        mqtt.publish(f'blackjack/player/{player_id}/hand', player.to_dict())
    return game.to_dict()


@app.post('/game/dealer/play')
async def dealer_play():
    if not game.all_players_done():
        raise HTTPException(400, 'Nem todos os jogadores terminaram')
    game.dealer_play()
    await broadcast('dealer_playing')
    await asyncio.sleep(1.0)   # small pause for animation feel
    game.calculate_results()
    await broadcast('round_finished')
    # Notify each player of their final result via MQTT
    for p in game.to_dict()['players']:
        mqtt.publish(f"blackjack/player/{p['player_id']}/hand", p)
    return game.to_dict()


@app.post('/game/reset')
async def reset_game():
    game.reset()
    await broadcast('game_reset')
    return game.to_dict()


@app.post('/game/new-game')
async def new_game():
    game.new_game()
    await broadcast('new_game')
    return game.to_dict()


# ── Serve React frontend (static build) ───────────────────────────────────
_DIST = Path(__file__).resolve().parent.parent.parent / 'frontend' / 'dist'

if _DIST.exists():
    _assets = _DIST / 'assets'
    if _assets.exists():
        app.mount('/assets', StaticFiles(directory=_assets), name='assets')

    @app.get('/{full_path:path}')
    async def serve_spa(full_path: str):
        return FileResponse(_DIST / 'index.html')

