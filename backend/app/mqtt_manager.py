import json
import threading
import time
import base64
from typing import Callable, Optional
import paho.mqtt.client as mqtt
from app.config import (
    MQTT_BROKER_HOST, MQTT_BROKER_PORT,
    MQTT_TOPIC_FRAME, MQTT_TOPIC_RESULT, MQTT_TOPIC_STATUS,
    MQTT_CLIENT_ID,
)
from app.logger import logger


class MQTTManager:
    """
    Gerencia conexão MQTT do backend:
    - Subscreve blackjack/camera/frame
    - Publica em blackjack/result e blackjack/status
    """

    def __init__(self):
        self._client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._frame_callback: Optional[Callable[[bytes], None]] = None
        self._connected = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Callbacks MQTT
    # ------------------------------------------------------------------ #
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info(f"MQTT conectado ao broker {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
            client.subscribe(MQTT_TOPIC_FRAME, qos=1)
            logger.info(f"Subscrito em '{MQTT_TOPIC_FRAME}'")
            self.publish_status("online")
        else:
            logger.error(f"Falha na conexão MQTT, código: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning(f"MQTT desconectado (rc={rc}). Reconectando em 5s...")

    def _on_message(self, client, userdata, msg):
        logger.debug(f"Mensagem recebida em '{msg.topic}' ({len(msg.payload)} bytes)")
        if msg.topic == MQTT_TOPIC_FRAME:
            if self._frame_callback:
                try:
                    self._frame_callback(msg.payload)
                except Exception as e:
                    logger.error(f"Erro no frame_callback: {e}")

    # ------------------------------------------------------------------ #
    # Controle de conexão
    # ------------------------------------------------------------------ #
    def start(self, frame_callback: Callable[[bytes], None]):
        self._frame_callback = frame_callback
        self._client.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
        self._client.loop_start()
        logger.info("Loop MQTT iniciado.")

    def stop(self):
        self.publish_status("offline")
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT desconectado.")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------ #
    # Publicação
    # ------------------------------------------------------------------ #
    def publish_result(self, result: dict):
        payload = json.dumps(result, ensure_ascii=False)
        self._client.publish(MQTT_TOPIC_RESULT, payload, qos=1)
        logger.info(f"Resultado publicado: {payload[:120]}")

    def publish_status(self, status: str, detail: str = ""):
        payload = json.dumps({"status": status, "detail": detail, "timestamp": time.time()})
        self._client.publish(MQTT_TOPIC_STATUS, payload, qos=0)

    def publish_frame(self, image_bytes: bytes):
        """Publica frame de imagem (usado pelo publisher simulado)."""
        self._client.publish(MQTT_TOPIC_FRAME, image_bytes, qos=1)
        logger.debug(f"Frame publicado ({len(image_bytes)} bytes)")


# Instância global
mqtt_manager = MQTTManager()
