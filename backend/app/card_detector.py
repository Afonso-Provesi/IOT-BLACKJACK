import cv2
import numpy as np
import re
from typing import Optional
from app.logger import logger

# EasyOCR é carregado sob demanda para economizar memória na inicialização
_ocr_reader = None

# Mapeamentos de blackjack
RANK_VALUES = {
    "A": 11, "2": 2, "3": 3, "4": 4, "5": 5,
    "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10,
}

SUIT_SYMBOLS = {
    "♠": "spades", "♥": "hearts", "♦": "diamonds", "♣": "clubs",
    "S": "spades", "H": "hearts", "D": "diamonds", "C": "clubs",
}


def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            logger.info("Inicializando EasyOCR (pode demorar na primeira vez)...")
            _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            logger.info("EasyOCR pronto.")
        except Exception as e:
            logger.error(f"Falha ao carregar EasyOCR: {e}")
            _ocr_reader = None
    return _ocr_reader


def extract_rank_and_suit_from_corner(card_img: np.ndarray) -> dict:
    """
    Recorta o canto superior-esquerdo da carta (onde está o rank/suit),
    aplica OCR e retorna rank, suit e valor de blackjack.
    """
    h, w = card_img.shape[:2]
    # Canto superior-esquerdo: ~20% da altura e ~25% da largura
    corner = card_img[0: int(h * 0.3), 0: int(w * 0.3)]

    # Upscale para melhorar OCR
    corner_up = cv2.resize(corner, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(corner_up, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    reader = _get_ocr_reader()
    rank = None
    suit = None
    confidence = 0.0

    if reader:
        try:
            results = reader.readtext(thresh, detail=1, paragraph=False)
            all_text = " ".join([r[1] for r in results]).upper().strip()
            confidences = [r[2] for r in results]
            confidence = float(np.mean(confidences)) if confidences else 0.0

            rank = _parse_rank(all_text)
            suit = _parse_suit(all_text)
        except Exception as e:
            logger.warning(f"Erro no OCR: {e}")

    if rank is None:
        rank = _fallback_rank_detection(card_img)

    bj_value = RANK_VALUES.get(rank, 0) if rank else 0

    return {
        "rank": rank,
        "suit": suit,
        "blackjack_value": bj_value,
        "confidence": round(confidence, 3),
    }


def _parse_rank(text: str) -> Optional[str]:
    """Extrai o rank da string de OCR."""
    # Tenta identificar 10 primeiro (dois dígitos)
    if "10" in text:
        return "10"
    for token in re.split(r"[\s,;]", text):
        token = token.strip().upper()
        if token in RANK_VALUES:
            return token
    # Tentativa por caractere único
    for ch in text.replace(" ", ""):
        if ch in RANK_VALUES:
            return ch
    return None


def _parse_suit(text: str) -> Optional[str]:
    """Extrai o naipe da string de OCR."""
    for sym, name in SUIT_SYMBOLS.items():
        if sym in text:
            return name
    return None


def _fallback_rank_detection(card_img: np.ndarray) -> Optional[str]:
    """
    Fallback simples baseado em análise de cor:
    detecta se é carta vermelha (hearts/diamonds) ou preta.
    Retorna None (não consegue determinar rank sem OCR).
    """
    hsv = cv2.cvtColor(card_img, cv2.COLOR_BGR2HSV)
    red_mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
    red_mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
    red_pixels = cv2.countNonZero(red_mask1 + red_mask2)
    total_pixels = card_img.shape[0] * card_img.shape[1]
    logger.debug(f"Fallback: {red_pixels}/{total_pixels} pixels vermelhos")
    return None


def detect_suit_by_color(card_img: np.ndarray) -> str:
    """Detecta naipe provável por análise de cor (vermelho=hearts/diamonds, preto=spades/clubs)."""
    hsv = cv2.cvtColor(card_img, cv2.COLOR_BGR2HSV)
    red_mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
    red_mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
    red_pixels = cv2.countNonZero(red_mask1 + red_mask2)
    total = card_img.shape[0] * card_img.shape[1]
    ratio = red_pixels / total if total > 0 else 0
    return "hearts_or_diamonds" if ratio > 0.05 else "spades_or_clubs"
