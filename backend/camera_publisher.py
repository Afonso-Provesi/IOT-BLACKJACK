"""
Camera Publisher simulado.
Lê uma imagem (ou pasta de imagens) e publica periodicamente no tópico MQTT.
Uso:
    python camera_publisher.py --image path/to/card.jpg --interval 3
    python camera_publisher.py --folder path/to/images/ --interval 5
"""
import argparse
import time
import os
import sys
import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
TOPIC_FRAME = os.getenv("MQTT_TOPIC_FRAME", "blackjack/camera/frame")
TOPIC_STATUS = os.getenv("MQTT_TOPIC_STATUS", "blackjack/status")


def publish_image(client: mqtt.Client, path: str):
    with open(path, "rb") as f:
        data = f.read()
    client.publish(TOPIC_FRAME, data, qos=1)
    print(f"[publisher] Frame publicado: {path} ({len(data)} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Blackjack Camera MQTT Publisher")
    parser.add_argument("--image", type=str, help="Caminho para uma imagem.")
    parser.add_argument("--folder", type=str, help="Pasta com imagens (JPEG/PNG).")
    parser.add_argument("--interval", type=float, default=3.0, help="Intervalo em segundos.")
    parser.add_argument("--loop", action="store_true", help="Repetir em loop.")
    args = parser.parse_args()

    if not args.image and not args.folder:
        parser.error("Informe --image ou --folder.")

    client = mqtt.Client(client_id="blackjack_camera_publisher", protocol=mqtt.MQTTv311)

    connected = False

    def on_connect(c, u, f, rc):
        nonlocal connected
        if rc == 0:
            connected = True
            print(f"[publisher] Conectado ao broker {BROKER_HOST}:{BROKER_PORT}")
        else:
            print(f"[publisher] Falha na conexão: {rc}")
            sys.exit(1)

    client.on_connect = on_connect
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    # Aguarda conexão
    timeout = 10
    while not connected and timeout > 0:
        time.sleep(0.5)
        timeout -= 0.5

    if not connected:
        print("[publisher] Timeout ao conectar ao broker.")
        sys.exit(1)

    # Coleta imagens
    images = []
    if args.image:
        images = [args.image]
    elif args.folder:
        exts = (".jpg", ".jpeg", ".png", ".webp")
        images = sorted([
            os.path.join(args.folder, f)
            for f in os.listdir(args.folder)
            if f.lower().endswith(exts)
        ])
        if not images:
            print(f"[publisher] Nenhuma imagem encontrada em {args.folder}")
            sys.exit(1)

    print(f"[publisher] {len(images)} imagem(ns) encontrada(s). Intervalo: {args.interval}s")

    try:
        while True:
            for img_path in images:
                if not os.path.isfile(img_path):
                    print(f"[publisher] Arquivo não encontrado: {img_path}")
                    continue
                publish_image(client, img_path)
                time.sleep(args.interval)
            if not args.loop:
                break
    except KeyboardInterrupt:
        print("\n[publisher] Interrompido pelo usuário.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("[publisher] Desconectado.")


if __name__ == "__main__":
    main()
