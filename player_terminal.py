#!/usr/bin/env python3
"""
Terminal interativo para um jogador de Blackjack IoT.

Uso:
    python3 player_terminal.py <player_id> [room_id]

Exemplo:
    python3 player_terminal.py p1                  # mesa padrão (mesa-principal)
    python3 player_terminal.py p1 minha-mesa

O script:
  - Assina  blackjack/rooms/<room>/players/<id>/hand   → exibe suas cartas ao vivo
  - Publica blackjack/rooms/<room>/players/<id>/action → envia 'hit' ou 'stand'

Broker: usa as mesmas variáveis de ambiente do backend
(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_TLS).
Sem elas, conecta em localhost:1883.
"""

import os
import sys
import json
import uuid
import threading
import paho.mqtt.client as mqtt

BROKER   = os.getenv("MQTT_BROKER_HOST", "localhost")
PORT     = int(os.getenv("MQTT_BROKER_PORT", "1883"))
USERNAME = os.getenv("MQTT_USERNAME") or None
PASSWORD = os.getenv("MQTT_PASSWORD") or None
USE_TLS  = os.getenv("MQTT_TLS", str(PORT == 8883)).strip().lower() in ("1", "true", "yes", "on")
CA_CERT  = os.getenv("MQTT_CA_CERT_PATH") or None
DEFAULT_ROOM = "mesa-principal"

SUITS = {"spades": "♠", "hearts": "♥", "diamonds": "♦", "clubs": "♣"}
STATUS_PT = {
    "waiting":   "aguardando",
    "playing":   "jogando",
    "stood":     "PAROU",
    "bust":      "BUST (estourou)",
    "blackjack": "BLACKJACK! 🎉",
    "win":       "GANHOU ✅",
    "lose":      "PERDEU ❌",
    "tie":       "EMPATE 🤝",
}

def render_hand(data: dict):
    name   = data.get("name", "?")
    hand   = data.get("hand", [])
    value  = data.get("hand_value", 0)
    status = STATUS_PT.get(data.get("status", ""), data.get("status", ""))

    cards_str = "  ".join(
        f"[{'?' if c.get('hidden') else c['rank'] + SUITS.get(c['suit'], c['suit'])}]"
        for c in hand
    )

    print()
    print("─" * 46)
    print(f"  Jogador : {name}")
    print(f"  Cartas  : {cards_str or '(nenhuma)'}")
    if not all(c.get("hidden") for c in hand):
        print(f"  Total   : {value}")
    print(f"  Status  : {status}")
    print("─" * 46)

    if data.get("status") == "playing":
        print("  → Digite  h  para pedir carta  |  s  para parar")
    elif data.get("status") in ("win", "lose", "tie", "bust", "blackjack"):
        print("  → Rodada encerrada. Aguarde nova rodada.")
    print()

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 player_terminal.py <player_id> [room_id]")
        sys.exit(1)

    player_id  = sys.argv[1]
    room_id    = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_ROOM
    topic_hand = f"blackjack/rooms/{room_id}/players/{player_id}/hand"
    topic_act  = f"blackjack/rooms/{room_id}/players/{player_id}/action"
    client_id  = f"terminal-{player_id}-{uuid.uuid4().hex[:6]}"

    # paho-mqtt 2.x requires CallbackAPIVersion
    try:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
    except AttributeError:
        # paho-mqtt 1.x fallback
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] Conectado. Aguardando cartas no tópico: {topic_hand}")
            c.subscribe(topic_hand, qos=1)
        else:
            print(f"[MQTT] Falha na conexão (rc={rc})")

    def on_message(c, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            render_hand(data)
        except Exception as e:
            print(f"[MQTT] Mensagem inválida: {e}")

    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD)
    if USE_TLS:
        client.tls_set(ca_certs=CA_CERT)

    client.on_connect = on_connect
    client.on_message = on_message
    print(f"[MQTT] Conectando em {BROKER}:{PORT} (TLS={'sim' if USE_TLS else 'não'})...")
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()

    print(f"╔══════════════════════════════════════════════╗")
    print(f"║     BLACKJACK IoT — Terminal do Jogador      ║")
    print(f"║  ID: {player_id:<40}║")
    print(f"║  Mesa: {room_id:<38}║")
    print(f"╚══════════════════════════════════════════════╝")
    print("  h → pedir carta   s → parar   q → sair\n")

    try:
        while True:
            cmd = input().strip().lower()
            if cmd == "q":
                break
            elif cmd == "h":
                client.publish(topic_act, "hit", qos=1)
                print("  [enviado] hit")
            elif cmd == "s":
                client.publish(topic_act, "stand", qos=1)
                print("  [enviado] stand")
            elif cmd:
                print("  Comandos: h (hit)  s (stand)  q (sair)")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        print("\n[MQTT] Desconectado.")

if __name__ == "__main__":
    main()
