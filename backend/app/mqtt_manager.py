import json
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from app.config import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_CLIENT_ID
from app.logger import logger

TOPIC_HUB_STATE = 'blackjack/hub/state'
TOPIC_ROOM_GAME_STATE = 'blackjack/rooms/{room_id}/game/state'
TOPIC_ROOM_PLAYER_HAND = 'blackjack/rooms/{room_id}/players/{player_id}/hand'
TOPIC_PLAYER_ACTION = 'blackjack/rooms/+/players/+/action'
TOPIC_TABLE_ACTION = 'blackjack/rooms/+/tables/+/action'


class MQTTManager:
    """
    MQTT bridge for the blackjack game server.

        Publishes:
            blackjack/hub/state                               – resumo das mesas
            blackjack/rooms/{room_id}/game/state             – estado completo de uma mesa
            blackjack/rooms/{room_id}/players/{id}/hand      – mão individual do jogador

    Subscribes:
            blackjack/rooms/{room_id}/players/{id}/action    – ação do jogador
            blackjack/rooms/{room_id}/tables/{id}/action     – comando do terminal de mesa
    """

    def __init__(self):
        # paho-mqtt 2.x requires CallbackAPIVersion to keep the old signatures
        try:
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=MQTT_CLIENT_ID,
                protocol=mqtt.MQTTv311,
            )
        except AttributeError:
            # paho-mqtt 1.x fallback
            self._client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._connected = False
        self._player_action_callback: Optional[Callable[[str, str, str], None]] = None
        self._table_action_callback: Optional[Callable[[str, str, str, dict], None]] = None

    # ── MQTT callbacks ─────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info(f'MQTT conectado a {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}')
            client.subscribe(TOPIC_PLAYER_ACTION, qos=1)
            client.subscribe(TOPIC_TABLE_ACTION, qos=1)
            logger.info(f'Subscrito em {TOPIC_PLAYER_ACTION!r}')
            logger.info(f'Subscrito em {TOPIC_TABLE_ACTION!r}')
        else:
            logger.error(f'Falha na conexão MQTT rc={rc}')

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning(f'MQTT desconectado (rc={rc})')

    def _on_message(self, client, userdata, msg):
        try:
            parts = msg.topic.split('/')
            raw_payload = msg.payload.decode('utf-8').strip()

            if (
                len(parts) == 6
                and parts[0] == 'blackjack'
                and parts[1] == 'rooms'
                and parts[3] == 'players'
                and parts[5] == 'action'
            ):
                room_id = parts[2]
                player_id = parts[4]
                action = raw_payload.lower()
                logger.info(f'MQTT player action: room={room_id} player={player_id} action={action}')
                if self._player_action_callback and (
                    action in ('hit', 'stand', 'split', 'double') or action.startswith('bet:')
                ):
                    self._player_action_callback(room_id, player_id, action)
                return

            if (
                len(parts) == 6
                and parts[0] == 'blackjack'
                and parts[1] == 'rooms'
                and parts[3] == 'tables'
                and parts[5] == 'action'
            ):
                room_id = parts[2]
                table_id = parts[4]
                payload = self._parse_table_payload(raw_payload)
                action = payload.get('action', '').strip().lower()
                logger.info(f'MQTT table action: room={room_id} table={table_id} action={action}')
                if self._table_action_callback and action:
                    self._table_action_callback(room_id, table_id, action, payload)
        except Exception as e:
            logger.error(f'Erro processando mensagem MQTT: {e}')

    @staticmethod
    def _parse_table_payload(raw_payload: str) -> dict:
        if not raw_payload:
            return {}
        try:
            payload = json.loads(raw_payload)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass
        return {'action': raw_payload}

    # ── Connection control ─────────────────────────────────────────────────

    def connect(
        self,
        player_action_callback: Optional[Callable[[str, str, str], None]] = None,
        table_action_callback: Optional[Callable[[str, str, str, dict], None]] = None,
    ):
        self._player_action_callback = player_action_callback
        self._table_action_callback = table_action_callback
        try:
            self._client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            self._client.loop_start()
            logger.info('Loop MQTT iniciado')
        except Exception as e:
            logger.warning(f'MQTT não disponível: {e}')

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()
        logger.info('MQTT desconectado')

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Publishing ─────────────────────────────────────────────────────────

    def publish(self, topic: str, payload: dict, qos: int = 1):
        if not self._connected:
            return
        try:
            self._client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=qos)
        except Exception as e:
            logger.warning(f'Erro ao publicar em {topic!r}: {e}')

    @staticmethod
    def topic_hub_state() -> str:
        return TOPIC_HUB_STATE

    @staticmethod
    def topic_game_state(room_id: str) -> str:
        return TOPIC_ROOM_GAME_STATE.format(room_id=room_id)

    @staticmethod
    def topic_table_action(room_id: str, table_id: str) -> str:
        return f'blackjack/rooms/{room_id}/tables/{table_id}/action'

    @staticmethod
    def topic_player_hand(room_id: str, player_id: str) -> str:
        return TOPIC_ROOM_PLAYER_HAND.format(room_id=room_id, player_id=player_id)

    @staticmethod
    def topic_player_action(room_id: str, player_id: str) -> str:
        return f'blackjack/rooms/{room_id}/players/{player_id}/action'
