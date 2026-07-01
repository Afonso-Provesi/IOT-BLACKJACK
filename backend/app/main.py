import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.game_engine import GameStatus
from app.mqtt_manager import MQTTManager
from app.logger import logger
from app.room_manager import DEFAULT_ROOM_ID, RoomRegistry, RoomState

# ── Singletons ─────────────────────────────────────────────────────────────
rooms = RoomRegistry()
mqtt = MQTTManager()
_ws_clients: Dict[str, Set[WebSocket]] = {}
_loop: Optional[asyncio.AbstractEventLoop] = None


# ── Helpers ────────────────────────────────────────────────────────────────
def _get_room(room_id: str) -> RoomState:
    room = rooms.get_room(room_id)
    if room is None:
        raise HTTPException(404, 'Sala não encontrada')
    return room


def _player_terminal_payload(room: RoomState, player: dict) -> dict:
    player_id = player['player_id']
    return {
        'terminal_id': f'player-{room.room_id}-{player_id}',
        'player_id': player_id,
        'name': player.get('name'),
        'status': player.get('status'),
        'topics': {
            'state': mqtt.topic_player_hand(room.room_id, player_id),
            'action': mqtt.topic_player_action(room.room_id, player_id),
        },
    }


def _room_payload(room: RoomState) -> dict:
    state = room.to_dict()
    player_terminals = [_player_terminal_payload(room, player) for player in state.get('players', [])]
    state['mqtt'] = {
        'hub_state_topic': mqtt.topic_hub_state(),
        'room_state_topic': mqtt.topic_game_state(room.room_id),
        'table_terminal': {
            'terminal_id': room.table_terminal_id,
            'topics': {
                'state': mqtt.topic_game_state(room.room_id),
                'action': mqtt.topic_table_action(room.room_id, room.table_terminal_id),
            },
        },
        'player_terminals': player_terminals,
    }
    return state


def _room_summary_payload(room: RoomState) -> dict:
    state = _room_payload(room)
    return {
        'room_id': room.room_id,
        'name': room.name,
        'table_terminal_id': room.table_terminal_id,
        'status': state['status'],
        'player_count': state['player_count'],
        'active_player_count': state['active_player_count'],
        'deck_remaining': state['deck_remaining'],
        'game_over_reason': state['game_over_reason'],
        'game_over_winner': state['game_over_winner'],
        'mqtt': state['mqtt'],
    }


def _publish_hub_state():
    mqtt.publish(mqtt.topic_hub_state(), {'rooms': [_room_summary_payload(room) for room in rooms.all_rooms()]})


async def _publish_player_state(room: RoomState, player_id: str):
    player = room.game.get_player(player_id)
    if player:
        payload = player.to_dict()
        payload.update(
            {
                'room_id': room.room_id,
                'parent_table_terminal_id': room.table_terminal_id,
                'terminal_id': f'player-{room.room_id}-{player_id}',
                'topics': {
                    'state': mqtt.topic_player_hand(room.room_id, player_id),
                    'action': mqtt.topic_player_action(room.room_id, player_id),
                },
            }
        )
        mqtt.publish(mqtt.topic_player_hand(room.room_id, player_id), payload)


# ── WebSocket broadcast ────────────────────────────────────────────────────
async def broadcast(room: RoomState, event_type: str):
    room_state = _room_payload(room)
    payload = json.dumps({'type': event_type, 'room_id': room.room_id, 'data': room_state})
    dead = set()
    for ws in _ws_clients.get(room.room_id, set()):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _ws_clients.setdefault(room.room_id, set()).difference_update(dead)
    try:
        mqtt.publish(mqtt.topic_game_state(room.room_id), room_state)
        _publish_hub_state()
    except Exception as e:
        logger.warning(f'MQTT publish error: {e}')


def _mqtt_player_action_callback(room_id: str, player_id: str, action: str):
    if _loop is None:
        return
    if action == 'hit':
        asyncio.run_coroutine_threadsafe(_handle_hit(room_id, player_id), _loop)
    elif action == 'stand':
        asyncio.run_coroutine_threadsafe(_handle_stand(room_id, player_id), _loop)
    elif action == 'split':
        asyncio.run_coroutine_threadsafe(_handle_split(room_id, player_id), _loop)
    elif action == 'double':
        asyncio.run_coroutine_threadsafe(_handle_double(room_id, player_id), _loop)
    elif action.startswith('bet:'):
        try:
            amount = int(action.split(':', 1)[1])
            asyncio.run_coroutine_threadsafe(_handle_bet(room_id, player_id, amount), _loop)
        except ValueError:
            pass


def _mqtt_table_action_callback(room_id: str, table_id: str, action: str, payload: dict):
    if _loop is None:
        return

    if action == 'start_round':
        asyncio.run_coroutine_threadsafe(_handle_start_round(room_id), _loop)
    elif action == 'dealer_play':
        asyncio.run_coroutine_threadsafe(_handle_dealer_play(room_id), _loop)
    elif action == 'reset':
        asyncio.run_coroutine_threadsafe(_handle_reset(room_id), _loop)
    elif action == 'new_game':
        asyncio.run_coroutine_threadsafe(_handle_new_game(room_id), _loop)
    elif action == 'add_player':
        name = str(payload.get('name', '')).strip()
        player_id = str(payload.get('player_id') or uuid.uuid4())[:8]
        owner_token = payload.get('owner_token')
        if name:
            asyncio.run_coroutine_threadsafe(
                _handle_add_player(room_id, name, player_id=player_id, owner_token=owner_token),
                _loop,
            )
    elif action == 'remove_player':
        player_id = str(payload.get('player_id', '')).strip()
        if player_id:
            asyncio.run_coroutine_threadsafe(_handle_remove_player(room_id, player_id), _loop)


async def _handle_hit(room_id: str, player_id: str):
    room = _get_room(room_id)
    card = room.game.player_hit(player_id)
    if card:
        event = 'all_players_done' if room.game.all_players_done() else 'player_hit'
        await broadcast(room, event)
        await _publish_player_state(room, player_id)


async def _handle_stand(room_id: str, player_id: str):
    room = _get_room(room_id)
    if room.game.player_stand(player_id):
        event = 'all_players_done' if room.game.all_players_done() else 'player_stood'
        await broadcast(room, event)
        await _publish_player_state(room, player_id)


async def _handle_split(room_id: str, player_id: str):
    room = _get_room(room_id)
    if room.game.player_split(player_id):
        event = 'all_players_done' if room.game.all_players_done() else 'player_split'
        await broadcast(room, event)
        await _publish_player_state(room, player_id)


async def _handle_double(room_id: str, player_id: str):
    room = _get_room(room_id)
    card = room.game.player_double(player_id)
    if card is not None:
        event = 'all_players_done' if room.game.all_players_done() else 'player_doubled'
        await broadcast(room, event)
        await _publish_player_state(room, player_id)


async def _handle_bet(room_id: str, player_id: str, amount: int):
    room = _get_room(room_id)
    if room.game.place_bet(player_id, amount):
        await broadcast(room, 'bet_placed')
        await _publish_player_state(room, player_id)


async def _handle_add_player(
    room_id: str,
    name: str,
    player_id: Optional[str] = None,
    owner_token: Optional[str] = None,
):
    room = _get_room(room_id)
    player_id = player_id or str(uuid.uuid4())[:8]
    if not room.game.add_player(player_id, name, owner_token=owner_token):
        raise HTTPException(400, 'Não foi possível adicionar jogador (jogo em andamento, mesa cheia ou ID duplicado)')
    await broadcast(room, 'player_joined')
    return {'player_id': player_id, 'name': name, 'room_id': room.room_id}


async def _handle_remove_player(room_id: str, player_id: str):
    room = _get_room(room_id)
    if not room.game.remove_player(player_id):
        raise HTTPException(400, 'Não foi possível remover jogador')
    await broadcast(room, 'player_removed')
    return {'ok': True}


async def _handle_start_round(room_id: str):
    room = _get_room(room_id)
    if not room.game.start_round():
        raise HTTPException(400, 'Todos os jogadores precisam apostar antes de iniciar')
    await broadcast(room, 'round_started')
    for player in room.to_dict()['players']:
        mqtt.publish(mqtt.topic_player_hand(room.room_id, player['player_id']), player)
    return room.to_dict()


async def _handle_dealer_play(room_id: str):
    room = _get_room(room_id)
    if not room.game.all_players_done():
        raise HTTPException(400, 'Nem todos os jogadores terminaram')
    room.game.dealer_play()
    await broadcast(room, 'dealer_playing')
    await asyncio.sleep(1.0)
    room.game.calculate_results()
    await broadcast(room, 'round_finished')
    for player in room.to_dict()['players']:
        mqtt.publish(mqtt.topic_player_hand(room.room_id, player['player_id']), player)
    return room.to_dict()


async def _handle_reset(room_id: str):
    room = _get_room(room_id)
    room.game.reset()
    await broadcast(room, 'game_reset')
    return room.to_dict()


async def _handle_new_game(room_id: str):
    room = _get_room(room_id)
    room.game.new_game()
    await broadcast(room, 'new_game')
    return room.to_dict()


# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app_: FastAPI):
    global _loop
    _loop = asyncio.get_event_loop()
    rooms.get_or_create_default()
    mqtt.connect(
        player_action_callback=_mqtt_player_action_callback,
        table_action_callback=_mqtt_table_action_callback,
    )
    _publish_hub_state()
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
async def websocket_endpoint(websocket: WebSocket, room_id: str = DEFAULT_ROOM_ID):
    room = rooms.get_room(room_id)
    await websocket.accept()
    if room is None:
        await websocket.send_text(json.dumps({'type': 'error', 'data': {'detail': 'Sala não encontrada'}}))
        await websocket.close(code=1008)
        return

    room_clients = _ws_clients.setdefault(room_id, set())
    room_clients.add(websocket)
    # Send current state immediately on connect
    await websocket.send_text(
        json.dumps({'type': 'game_state', 'room_id': room_id, 'data': _room_payload(room)})
    )
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        room_clients.discard(websocket)


# ── REST API ───────────────────────────────────────────────────────────────

class AddPlayerRequest(BaseModel):
    name: str
    player_id: Optional[str] = None
    owner_token: Optional[str] = None


class CreateRoomRequest(BaseModel):
    name: str
    room_id: Optional[str] = None


class BetRequest(BaseModel):
    amount: int


def _assert_owner(room: RoomState, player_id: str, device_id: Optional[str]):
    """Raise 403 if device_id doesn't match the player's owner_token."""
    player = room.game.get_player(player_id)
    if player and player.owner_token and player.owner_token != device_id:
        raise HTTPException(403, 'Não autorizado — este jogador pertence a outro dispositivo')


@app.get('/health')
async def health():
    default_room = rooms.get_or_create_default()
    return {'status': 'ok', 'game_status': default_room.game.status.value, 'room_count': len(rooms.list_rooms())}


@app.get('/rooms')
async def list_rooms():
    return {'rooms': [_room_summary_payload(room) for room in rooms.all_rooms()]}


@app.post('/rooms')
async def create_room(req: CreateRoomRequest):
    room = rooms.create_room(req.name, room_id=req.room_id)
    _publish_hub_state()
    return {
        'room': _room_summary_payload(room),
        'mqtt': {
            'hub_state_topic': mqtt.topic_hub_state(),
            'game_state_topic': mqtt.topic_game_state(room.room_id),
            'table_action_topic': mqtt.topic_table_action(room.room_id, room.table_terminal_id),
        },
    }


@app.get('/rooms/{room_id}')
async def get_room(room_id: str):
    return _room_payload(_get_room(room_id))


@app.delete('/rooms/{room_id}')
async def delete_room(room_id: str):
    if room_id == DEFAULT_ROOM_ID:
        raise HTTPException(400, 'A mesa principal não pode ser excluída')

    room = rooms.delete_room(room_id)
    if room is None:
        raise HTTPException(404, 'Sala não encontrada')

    for ws in _ws_clients.pop(room_id, set()):
        try:
            await ws.close(code=1000)
        except Exception:
            pass

    _publish_hub_state()
    return {'ok': True, 'room_id': room_id}


@app.get('/game/state')
async def get_state():
    return _room_payload(rooms.get_or_create_default())


@app.get('/rooms/{room_id}/game/state')
async def get_room_state(room_id: str):
    return _room_payload(_get_room(room_id))


@app.post('/game/players')
async def add_player(req: AddPlayerRequest):
    room = rooms.get_or_create_default()
    return await _handle_add_player(room.room_id, req.name, player_id=req.player_id, owner_token=req.owner_token)


@app.post('/rooms/{room_id}/game/players')
async def add_room_player(room_id: str, req: AddPlayerRequest):
    return await _handle_add_player(room_id, req.name, player_id=req.player_id, owner_token=req.owner_token)


@app.delete('/game/players/{player_id}')
async def remove_player(player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = rooms.get_or_create_default()
    _assert_owner(room, player_id, x_device_id)
    return await _handle_remove_player(room.room_id, player_id)


@app.delete('/rooms/{room_id}/game/players/{player_id}')
async def remove_room_player(room_id: str, player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = _get_room(room_id)
    _assert_owner(room, player_id, x_device_id)
    return await _handle_remove_player(room_id, player_id)


@app.post('/game/players/{player_id}/bet')
async def place_bet(player_id: str, req: BetRequest, x_device_id: Optional[str] = Header(default=None)):
    room = rooms.get_or_create_default()
    _assert_owner(room, player_id, x_device_id)
    if not room.game.place_bet(player_id, req.amount):
        raise HTTPException(400, 'Aposta inválida (valor fora do saldo ou jogo em andamento)')
    await broadcast(room, 'bet_placed')
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/rooms/{room_id}/game/players/{player_id}/bet')
async def place_room_bet(room_id: str, player_id: str, req: BetRequest, x_device_id: Optional[str] = Header(default=None)):
    room = _get_room(room_id)
    _assert_owner(room, player_id, x_device_id)
    if not room.game.place_bet(player_id, req.amount):
        raise HTTPException(400, 'Aposta inválida (valor fora do saldo ou jogo em andamento)')
    await broadcast(room, 'bet_placed')
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/game/start')
async def start_round():
    return await _handle_start_round(rooms.get_or_create_default().room_id)


@app.post('/rooms/{room_id}/game/start')
async def start_room_round(room_id: str):
    return await _handle_start_round(room_id)


@app.post('/game/players/{player_id}/hit')
async def player_hit(player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = rooms.get_or_create_default()
    _assert_owner(room, player_id, x_device_id)
    card = room.game.player_hit(player_id)
    if card is None:
        raise HTTPException(400, 'Não foi possível pedir carta')
    event = 'all_players_done' if room.game.all_players_done() else 'player_hit'
    await broadcast(room, event)
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/rooms/{room_id}/game/players/{player_id}/hit')
async def player_room_hit(room_id: str, player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = _get_room(room_id)
    _assert_owner(room, player_id, x_device_id)
    card = room.game.player_hit(player_id)
    if card is None:
        raise HTTPException(400, 'Não foi possível pedir carta')
    event = 'all_players_done' if room.game.all_players_done() else 'player_hit'
    await broadcast(room, event)
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/game/players/{player_id}/stand')
async def player_stand(player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = rooms.get_or_create_default()
    _assert_owner(room, player_id, x_device_id)
    if not room.game.player_stand(player_id):
        raise HTTPException(400, 'Não foi possível parar')
    event = 'all_players_done' if room.game.all_players_done() else 'player_stood'
    await broadcast(room, event)
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/rooms/{room_id}/game/players/{player_id}/stand')
async def player_room_stand(room_id: str, player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = _get_room(room_id)
    _assert_owner(room, player_id, x_device_id)
    if not room.game.player_stand(player_id):
        raise HTTPException(400, 'Não foi possível parar')
    event = 'all_players_done' if room.game.all_players_done() else 'player_stood'
    await broadcast(room, event)
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/game/players/{player_id}/split')
async def player_split(player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = rooms.get_or_create_default()
    _assert_owner(room, player_id, x_device_id)
    if not room.game.player_split(player_id):
        raise HTTPException(400, 'Não foi possível fazer split')
    event = 'all_players_done' if room.game.all_players_done() else 'player_split'
    await broadcast(room, event)
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/rooms/{room_id}/game/players/{player_id}/split')
async def player_room_split(room_id: str, player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = _get_room(room_id)
    _assert_owner(room, player_id, x_device_id)
    if not room.game.player_split(player_id):
        raise HTTPException(400, 'Não foi possível fazer split')
    event = 'all_players_done' if room.game.all_players_done() else 'player_split'
    await broadcast(room, event)
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/game/players/{player_id}/double')
async def player_double(player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = rooms.get_or_create_default()
    _assert_owner(room, player_id, x_device_id)
    card = room.game.player_double(player_id)
    if card is None:
        raise HTTPException(400, 'Não foi possível dobrar')
    event = 'all_players_done' if room.game.all_players_done() else 'player_doubled'
    await broadcast(room, event)
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/rooms/{room_id}/game/players/{player_id}/double')
async def player_room_double(room_id: str, player_id: str, x_device_id: Optional[str] = Header(default=None)):
    room = _get_room(room_id)
    _assert_owner(room, player_id, x_device_id)
    card = room.game.player_double(player_id)
    if card is None:
        raise HTTPException(400, 'Não foi possível dobrar')
    event = 'all_players_done' if room.game.all_players_done() else 'player_doubled'
    await broadcast(room, event)
    await _publish_player_state(room, player_id)
    return room.to_dict()


@app.post('/game/dealer/play')
async def dealer_play():
    return await _handle_dealer_play(rooms.get_or_create_default().room_id)


@app.post('/rooms/{room_id}/game/dealer/play')
async def dealer_room_play(room_id: str):
    return await _handle_dealer_play(room_id)


@app.post('/game/reset')
async def reset_game():
    return await _handle_reset(rooms.get_or_create_default().room_id)


@app.post('/rooms/{room_id}/game/reset')
async def reset_room_game(room_id: str):
    return await _handle_reset(room_id)


@app.post('/game/new-game')
async def new_game():
    return await _handle_new_game(rooms.get_or_create_default().room_id)


@app.post('/rooms/{room_id}/game/new-game')
async def new_room_game(room_id: str):
    return await _handle_new_game(room_id)


# ── Serve React frontend (static build) ───────────────────────────────────
_DIST = Path(__file__).resolve().parent.parent.parent / 'frontend' / 'dist'

if _DIST.exists():
    _assets = _DIST / 'assets'
    if _assets.exists():
        app.mount('/assets', StaticFiles(directory=_assets), name='assets')

    @app.get('/{full_path:path}')
    async def serve_spa(full_path: str):
        return FileResponse(_DIST / 'index.html')

