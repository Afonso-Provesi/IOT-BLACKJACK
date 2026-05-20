#!/usr/bin/env python3
"""
Terminal interativo para um jogador de Blackjack IoT.

Uso:
    python3 player_terminal.py <player_id>

Exemplo:
    python3 player_terminal.py p1

O script:
  - Assina  blackjack/player/<id>/hand   → exibe suas cartas ao vivo
  - Publica blackjack/player/<id>/action → enviar 'hit' ou 'stand'
"""

import sys
import json
import threading
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT   = 1883

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
        print("Uso: python3 player_terminal.py <player_id>")
        sys.exit(1)

    player_id  = sys.argv[1]
    topic_hand = f"blackjack/player/{player_id}/hand"
    topic_act  = f"blackjack/player/{player_id}/action"

    # paho-mqtt 2.x requires CallbackAPIVersion
    try:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id=f"terminal-{player_id}",
            protocol=mqtt.MQTTv311,
        )
    except AttributeError:
        # paho-mqtt 1.x fallback
        client = mqtt.Client(client_id=f"terminal-{player_id}", protocol=mqtt.MQTTv311)

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

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()

    print(f"╔══════════════════════════════════════════════╗")
    print(f"║     BLACKJACK IoT — Terminal do Jogador      ║")
    print(f"║  ID: {player_id:<40}║")
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
