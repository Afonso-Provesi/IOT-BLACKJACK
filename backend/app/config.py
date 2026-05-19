import os
from dotenv import load_dotenv

load_dotenv()

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_TOPIC_FRAME = os.getenv("MQTT_TOPIC_FRAME", "blackjack/camera/frame")
MQTT_TOPIC_RESULT = os.getenv("MQTT_TOPIC_RESULT", "blackjack/result")
MQTT_TOPIC_STATUS = os.getenv("MQTT_TOPIC_STATUS", "blackjack/status")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "blackjack_backend")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
