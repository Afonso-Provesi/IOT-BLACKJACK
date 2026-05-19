import time
import uuid
import numpy as np
import cv2
from app.image_processing import (
    decode_image_bytes, preprocess,
    detect_card_contours, correct_perspective,
)
from app.card_detector import extract_rank_and_suit_from_corner, detect_suit_by_color
from app.mqtt_manager import mqtt_manager
from app.logger import logger
from app.history import history_store


def process_frame(raw_bytes: bytes):
    """
    Pipeline completo:
    1. Decodifica imagem
    2. Pré-processa
    3. Detecta contornos de cartas
    4. Corrige perspectiva
    5. Reconhece rank/suit
    6. Publica resultado via MQTT
    """
    start_time = time.time()
    frame_id = str(uuid.uuid4())[:8]
    logger.info(f"[{frame_id}] Processando frame ({len(raw_bytes)} bytes)...")

    try:
        img = decode_image_bytes(raw_bytes)
    except ValueError as e:
        logger.error(f"[{frame_id}] {e}")
        mqtt_manager.publish_status("error", str(e))
        return

    img = preprocess(img)
    contours = detect_card_contours(img)
    logger.info(f"[{frame_id}] Contornos detectados: {len(contours)}")

    cards = []
    for idx, contour in enumerate(contours):
        try:
            warped = correct_perspective(img, contour)
            info = extract_rank_and_suit_from_corner(warped)
            color_hint = detect_suit_by_color(warped)

            # Se OCR não detectou suit, usa hint de cor
            if info["suit"] is None:
                info["suit"] = color_hint

            cards.append({
                "card_index": idx,
                "rank": info["rank"],
                "suit": info["suit"],
                "blackjack_value": info["blackjack_value"],
                "confidence": info["confidence"],
            })
        except Exception as e:
            logger.warning(f"[{frame_id}] Erro ao processar carta {idx}: {e}")

    total_value = sum(c["blackjack_value"] for c in cards)
    # Regra Ás: se total > 21 e há ás, conta como 1
    if total_value > 21:
        for c in cards:
            if c["rank"] == "A" and total_value > 21:
                c["blackjack_value"] = 1
                total_value -= 10

    elapsed = round(time.time() - start_time, 3)

    result = {
        "frame_id": frame_id,
        "timestamp": time.time(),
        "cards_detected": len(cards),
        "cards": cards,
        "total_value": total_value,
        "processing_time_s": elapsed,
        "status": "ok" if cards else "no_cards_detected",
    }

    mqtt_manager.publish_result(result)
    history_store.add(result)
    logger.info(f"[{frame_id}] Resultado: {len(cards)} carta(s), total={total_value}, {elapsed}s")
    return result
