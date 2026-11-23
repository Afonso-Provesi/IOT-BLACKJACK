import os
import uuid

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


# ── Broker MQTT ────────────────────────────────────────────────────────────
# Local (docker compose / start.sh): host=localhost, porta 1883, sem TLS.
# Nuvem (EMQX Serverless, por ex.): host do deployment, porta 8883, MQTT_TLS=true
# e usuário/senha criados no painel do broker.
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME') or None
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD') or None
MQTT_TLS = _env_bool('MQTT_TLS', default=MQTT_BROKER_PORT == 8883)

# Certificado da CA do broker (opcional). Use quando o broker não usa um
# certificado de CA pública: MQTT_CA_CERT_PATH aponta para um arquivo .crt,
# ou MQTT_CA_CERT_PEM recebe o conteúdo do certificado (útil no Render).
MQTT_CA_CERT_PATH = os.getenv('MQTT_CA_CERT_PATH') or None
MQTT_CA_CERT_PEM = os.getenv('MQTT_CA_CERT_PEM') or None

# Brokers compartilhados derrubam conexões com client_id repetido, então
# cada instância ganha um sufixo aleatório.
MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'blackjack_backend') + '-' + uuid.uuid4().hex[:6]

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
