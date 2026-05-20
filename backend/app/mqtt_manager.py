import json
import threading
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from app.config import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_CLIENT_ID
from app.logger import logger

# Topics
TOPIC_GAME_STATE = 'blackjack/game/state'
TOPIC_PLAYER_ACTION = 'blackjack/player/+/action'  # + = player_id wildcard


class MQTTManager:
    """
    MQTT bridge for the blackjack game server.

    Publishes:
      blackjack/game/state              – full game state on every change
      blackjack/player/{id}/hand        – individual player hand

    Subscribes:
      blackjack/player/{id}/action      – player hit/stand from MQTT terminals
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
        self._action_callback: Optional[Callable[[str, str], None]] = None

    # ── MQTT callbacks ─────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info(f'MQTT conectado a {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}')
            client.subscribe(TOPIC_PLAYER_ACTION, qos=1)
            logger.info(f'Subscrito em {TOPIC_PLAYER_ACTION!r}')
        else:
            logger.error(f'Falha na conexão MQTT rc={rc}')

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning(f'MQTT desconectado (rc={rc})')

    def _on_message(self, client, userdata, msg):
        """
        Handles player action messages from MQTT terminals.
        Expected topic: blackjack/player/{player_id}/action
        Expected payload: "hit" or "stand"
        """
        try:
            parts = msg.topic.split('/')
            if len(parts) == 4 and parts[0] == 'blackjack' and parts[1] == 'player' and parts[3] == 'action':
                player_id = parts[2]
                action = msg.payload.decode('utf-8').strip().lower()
                logger.info(f'MQTT action: player={player_id} action={action}')
                if self._action_callback and (
                    action in ('hit', 'stand', 'split', 'double') or action.startswith('bet:')
                ):
                    self._action_callback(player_id, action)
        except Exception as e:
            logger.error(f'Erro processando mensagem MQTT: {e}')

    # ── Connection control ─────────────────────────────────────────────────

    def connect(self, action_callback: Optional[Callable[[str, str], None]] = None):
        self._action_callback = action_callback
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
