#!/usr/bin/env bash
# Sobe (ou atualiza) o Blackjack IoT na EC2.
# Primeira execução: pergunta usuário e senha do broker MQTT e guarda em .env.
# Atualizar depois de um git pull:  ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Crie o login do broker MQTT (usado pelo backend e pelos terminais)."
  read -rp "Usuário MQTT: " MQTT_USERNAME
  read -rsp "Senha MQTT: " MQTT_PASSWORD; echo
  (umask 077; printf 'MQTT_USERNAME=%s\nMQTT_PASSWORD=%s\n' "$MQTT_USERNAME" "$MQTT_PASSWORD" > .env)
fi
set -a; . ./.env; set +a

if [ ! -d secrets ]; then
  echo "Gerando arquivo de senhas do Mosquitto..."
  mkdir -p secrets
  docker run --rm -v "$PWD/secrets:/work" eclipse-mosquitto:2.0 \
    sh -c "mosquitto_passwd -c -b /work/passwd '$MQTT_USERNAME' '$MQTT_PASSWORD' && chown -R 1883:1883 /work && chmod 700 /work && chmod 600 /work/passwd"
fi

docker compose up -d --build

TOKEN=$(curl -sf --max-time 2 -X PUT http://169.254.169.254/latest/api/token \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60" || true)
IP=$(curl -sf --max-time 2 -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/public-ipv4 || true)
[[ "$IP" =~ ^[0-9.]+$ ]] || IP=""

echo
echo "============================================================"
echo " Blackjack IoT no ar"
echo "  Site   : http://${IP:-<IP-publico-da-instancia>}"
echo "  MQTT   : ${IP:-<IP-publico>}:1883 (usuário: $MQTT_USERNAME)"
echo "  Logs   : docker compose logs -f app"
echo "============================================================"
