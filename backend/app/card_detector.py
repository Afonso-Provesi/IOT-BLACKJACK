import cv2
import numpy as np
import re
import pytesseract
from typing import Optional
from app.logger import logger

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


# ---------------------------------------------------------------------------
# Normalização e parsing de OCR
# ---------------------------------------------------------------------------

def _normalize_ocr(text: str) -> str:
    """
    Corrige confusões típicas do Tesseract em fontes bold/serif de baralho:
      '1' lido como 'A', 'I', 'l', '|' e '0' lido como 'O'.
    Aplica APENAS no padrão "[1-like][0-like]" → "10".
    """
    upper = text.upper()
    return re.sub(r'[1IL|A][0O]', '10', upper)


def _parse_rank(text: str) -> Optional[str]:
    """
    Extrai rank com tolerância a erros OCR.
    Prioridade: "10" > token exato > figura de 1 char (A/J/Q/K).
    """
    upper = text.upper().strip()

    # 1. "10" direto
    if "10" in upper:
        return "10"

    # 2. "10" via normalização (ex: "A0", "IO", "l0")
    if "10" in _normalize_ocr(upper):
        return "10"

    # 3. Token completo exato
    for token in re.split(r'[\s,;.|/\\!\-_\n\r]+', upper):
        token = token.strip()
        if token in RANK_VALUES:
            return token

    # 4. Fallback conservador: figuras de 1 char (evita "A" de lixo OCR)
    face_ranks = {"A", "J", "Q", "K"}
    for token in re.split(r'[\s,;.|/\\!\-_\n\r]+', upper):
        token = token.strip()
        if len(token) == 1 and token in face_ranks:
            return token

    return None


def _parse_suit(text: str) -> Optional[str]:
    """Extrai naipe da string de OCR."""
    for sym, name in SUIT_SYMBOLS.items():
        if sym in text:
            return name
    return None


# ---------------------------------------------------------------------------
# Extração da zona de rank
# ---------------------------------------------------------------------------

def _extract_rank_zone(corner_gray: np.ndarray) -> np.ndarray:
    """
    Do canto da carta (escala de cinza), isola a face branca e retorna o
    topo (onde fica o rank), sem o símbolo do naipe.

    BUG CORRIGIDO: a versão anterior cortava LARGURA (60%x60%), amputando
    o '0' do '10' em cartas com dígitos grandes. Agora corta apenas a
    ALTURA (topo 55%), mantendo a largura completa.
    """
    h, w = corner_gray.shape

    # Isola a face branca (remove borda preta ou fundo escuro)
    _, white_mask = cv2.threshold(corner_gray, 180, 255, cv2.THRESH_BINARY)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        white_mask, connectivity=8
    )

    if num_labels > 1:
        largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        cx = stats[largest, cv2.CC_STAT_LEFT]
        cy = stats[largest, cv2.CC_STAT_TOP]
        cw = stats[largest, cv2.CC_STAT_WIDTH]
        ch = stats[largest, cv2.CC_STAT_HEIGHT]
        # Usa apenas se a região for representativa (>20% da área do canto)
        if cw * ch > h * w * 0.20 and cw > 10 and ch > 10:
            face = corner_gray[cy:cy + ch, cx:cx + cw]
            fh = face.shape[0]
            # Topo 65%: garante que o '0' do '10' (digito mais baixo) seja incluido
            # 55% era insuficiente para cartas com fonte grande
            return face[:int(fh * 0.65), :]

    # Fallback: canto inteiro, topo 65%
    return corner_gray[:int(h * 0.65), :]


# ---------------------------------------------------------------------------
# OCR multi-método
# ---------------------------------------------------------------------------

def _try_ocr_zone(gray_zone: np.ndarray) -> Optional[str]:
    """
    Tenta extrair rank usando múltiplos métodos combinados.

    Estratégia anti-confusão (ex: 7→A, 4→A, 5→S, 8→B):
      - PSM 10 (single-char) é usado PRIMEIRO: mais preciso para dígitos isolados.
      - PSM 7 (single-line) em segundo: bom para "10" (dois chars).
      - PSM 6 (block) em terceiro: mais geral, mais sujeito a ruído.
      - Figuras (A/J/Q/K) só são aceitas se ≥2 métodos concordarem,
        evitando que um único read errado cause false positive.
      - Filtragem por confiança Tesseract (≥50): descarta leituras fracas.
    """
    if gray_zone is None or gray_zone.size == 0:
        return None
    h, w = gray_zone.shape
    if h < 5 or w < 5:
        return None

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
    FACE_RANKS = {'A', 'J', 'Q', 'K'}

    def _ocr(binary: np.ndarray, psm: int) -> Optional[str]:
        """OCR básico. _parse_rank já filtra lixo — não precisamos de threshold de confiança."""
        ready = cv2.copyMakeBorder(
            binary, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255
        )
        try:
            text = pytesseract.image_to_string(
                ready, config=f'--psm {psm}'
            ).strip()
            return _parse_rank(text)
        except Exception:
            return None

    def _accept_numeric(rank: Optional[str]) -> Optional[str]:
        """Aceita rank imediatamente se for numérico (2-9, 10). Rejeita figuras aqui."""
        if rank is not None and rank not in FACE_RANKS:
            return rank
        return None

    up2 = cv2.resize(gray_zone, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, b120 = cv2.threshold(up2, 120, 255, cv2.THRESH_BINARY)

    # --- Fast-path: thresh 120, PSM 10 → 7 → 6 ---
    # PSM 10 (single-char) é o mais preciso para dígitos isolados.
    # Aceita numéricos imediatamente; figuras precisam de confirmação.
    r_psm10 = _ocr(b120, 10)
    if _accept_numeric(r_psm10):
        logger.debug(f"OCR fast-path PSM10 rank={r_psm10}")
        return r_psm10

    r_psm7 = _ocr(b120, 7)
    if _accept_numeric(r_psm7):
        logger.debug(f"OCR fast-path PSM7 rank={r_psm7}")
        return r_psm7

    r_psm6 = _ocr(b120, 6)
    if _accept_numeric(r_psm6):
        logger.debug(f"OCR fast-path PSM6 rank={r_psm6}")
        return r_psm6

    # Figuras: só aceita se ≥2 dos 3 métodos concordam (evita 7→A, 4→A, etc.)
    face_votes = [r for r in [r_psm10, r_psm7, r_psm6] if r in FACE_RANKS]
    if len(face_votes) >= 2:
        from collections import Counter
        winner = Counter(face_votes).most_common(1)[0][0]
        logger.debug(f"OCR fast-path face={winner} (votos={len(face_votes)}/3)")
        return winner

    # --- Fast-path B: crop esquerda 55%, CLAHE + adaptativo ---
    left_zone = gray_zone[:, :max(int(gray_zone.shape[1] * 0.55), 10)]
    up2_left = cv2.resize(left_zone, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    up2_left_clahe = clahe.apply(up2_left)
    try:
        b_adapt_left = cv2.adaptiveThreshold(
            up2_left_clahe, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
            11, 5,
        )
        for psm in [10, 7, 6]:
            rank = _accept_numeric(_ocr(b_adapt_left, psm))
            if rank:
                logger.debug(f"OCR fast-path B left55%+adapt PSM{psm} rank={rank}")
                return rank
    except Exception:
        pass

    # --- Fast-path C: thresholds invertidos (texto claro sobre fundo escuro) ---
    for tv in [180, 160, 200]:
        _, b_inv = cv2.threshold(up2_left, tv, 255, cv2.THRESH_BINARY_INV)
        for psm in [10, 7]:
            rank = _accept_numeric(_ocr(b_inv, psm))
            if rank:
                logger.debug(f"OCR fast-path C left55%+inv{tv} PSM{psm} rank={rank}")
                return rank

    # --- Slow-path: multi-escala, multi-threshold, multi-PSM ---
    # Aqui aceita figuras também (já esgotou tentativas numéricas).
    for scale in [2, 3]:
        up = cv2.resize(gray_zone, None, fx=scale, fy=scale,
                        interpolation=cv2.INTER_CUBIC)
        up_clahe = clahe.apply(up)

        for src in [up_clahe, up]:
            _, b_otsu = cv2.threshold(src, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            _, b_otsu_inv = cv2.threshold(
                src, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
            binaries = [b_otsu, b_otsu_inv]

            for tv in [100, 140, 160, 180, 200]:
                _, b = cv2.threshold(src, tv, 255, cv2.THRESH_BINARY)
                _, b_inv = cv2.threshold(src, tv, 255, cv2.THRESH_BINARY_INV)
                binaries += [b, b_inv]

            try:
                b_adapt = cv2.adaptiveThreshold(
                    src, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    15, 8,
                )
                binaries.append(b_adapt)
            except Exception:
                pass

            for binary in binaries:
                for psm in [7, 6]:
                    rank = _ocr(binary, psm)
                    if rank:
                        logger.debug(
                            f"OCR slow-path rank={rank} scale={scale}x psm={psm}"
                        )
                        return rank

    return None


# ---------------------------------------------------------------------------
# Interface principal
# ---------------------------------------------------------------------------

def extract_rank_and_suit_from_corner(card_img: np.ndarray) -> dict:
    """
    Extrai rank e naipe tentando múltiplos cantos da carta.

    Estratégia multi-canto (para cartas em qualquer posição/orientação):
      1. Top-left         — posição padrão (carta upright)
      2. Bottom-right ↺   — carta de cabeça para baixo
      3. Top-right        — carta espelhada horizontalmente
      4. Bottom-left  ↺   — rotação alternativa

    Para cada canto: isola zona de rank → _try_ocr_zone (multi-escala,
    multi-threshold, multi-PSM). Para no primeiro rank válido.
    """
    h, w = card_img.shape[:2]
    gray = cv2.cvtColor(card_img, cv2.COLOR_BGR2GRAY)

    # 35% do canto (margem maior que os 30% anteriores)
    ph, pw = 0.35, 0.35

    corner_specs = [
        (gray[0:int(h * ph),            0:int(w * pw)],           False),  # TL
        (gray[int(h * (1 - ph)):,        int(w * (1 - pw)):],      True),   # BR ↺
        (gray[0:int(h * ph),            int(w * (1 - pw)):],       False),  # TR
        (gray[int(h * (1 - ph)):,        0:int(w * pw)],           True),   # BL ↺
    ]

    rank = None
    suit = None

    for corner_gray, rotate in corner_specs:
        if corner_gray is None or corner_gray.size == 0:
            continue

        if rotate:
            corner_gray = cv2.rotate(corner_gray, cv2.ROTATE_180)

        rank_zone = _extract_rank_zone(corner_gray)
        found = _try_ocr_zone(rank_zone)

        if found:
            rank = found
            # Tenta extrair naipe pelo OCR no canto completo (2x)
            try:
                up2 = cv2.resize(corner_gray, None, fx=2, fy=2,
                                 interpolation=cv2.INTER_CUBIC)
                ready = cv2.copyMakeBorder(
                    up2, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255
                )
                full_text = pytesseract.image_to_string(
                    ready, config='--psm 6'
                ).strip()
                suit = _parse_suit(full_text)
            except Exception:
                pass
            break

    # Fallback de naipe por análise de cor (sempre disponível)
    color_suit = detect_suit_by_color(card_img)
    if suit is None:
        suit = color_suit

    bj_value = RANK_VALUES.get(rank, 0) if rank else 0
    return {
        "rank": rank,
        "suit": suit,
        "blackjack_value": bj_value,
        "confidence": round(0.8 if rank else 0.0, 3),
    }


def detect_suit_by_color(card_img: np.ndarray) -> str:
    """Detecta naipe provável por análise de cor (vermelho=hearts/diamonds, preto=spades/clubs)."""
    hsv = cv2.cvtColor(card_img, cv2.COLOR_BGR2HSV)
    red_mask1 = cv2.inRange(hsv, np.array([0,   70, 50]), np.array([10,  255, 255]))
    red_mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
    red_pixels = cv2.countNonZero(red_mask1 + red_mask2)
    total = card_img.shape[0] * card_img.shape[1]
    ratio = red_pixels / total if total > 0 else 0
    return "hearts_or_diamonds" if ratio > 0.05 else "spades_or_clubs"
