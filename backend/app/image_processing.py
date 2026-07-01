import cv2
import numpy as np
from PIL import Image
import io
import base64
from app.logger import logger


def decode_image_bytes(data: bytes) -> np.ndarray:
    """Decodifica bytes brutos (JPEG/PNG) para array OpenCV."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Não foi possível decodificar a imagem recebida.")
    return img


def decode_base64_image(b64_string: str) -> np.ndarray:
    """Decodifica uma string base64 para array OpenCV."""
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    raw = base64.b64decode(b64_string)
    return decode_image_bytes(raw)


def encode_image_base64(img: np.ndarray, ext: str = ".jpg") -> str:
    """Codifica array OpenCV para string base64."""
    success, buf = cv2.imencode(ext, img)
    if not success:
        raise ValueError("Falha ao codificar imagem.")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def preprocess(img: np.ndarray) -> np.ndarray:
    """
    Pipeline de pré-processamento:
    1. Redimensiona mantendo proporção (max 1024px).
    2. Converte para escala de cinza para OCR.
    3. Aplica limiarização adaptativa.
    """
    h, w = img.shape[:2]
    max_dim = 1024
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    return img


def correct_perspective(img: np.ndarray, contour: np.ndarray) -> np.ndarray:
    """
    Aplica correção de perspectiva dado o contorno (4 pontos) da carta.
    Retorna a carta recortada e retificada.
    """
    rect = order_points(contour.reshape(4, 2).astype("float32"))
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    if max_width <= 0 or max_height <= 0:
        return img

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1],
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (max_width, max_height))
    return warped


def order_points(pts: np.ndarray) -> np.ndarray:
    """Ordena pontos: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def detect_card_contours(img: np.ndarray):
    """
    Detecta contornos retangulares que provavelmente são cartas.
    Retorna lista de contornos (4 pontos cada).
    Suporta cartas com cantos arredondados usando epsilon progressivo.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    card_contours = []

    img_area = img.shape[0] * img.shape[1]

    for c in contours:
        area = cv2.contourArea(c)
        if area < img_area * 0.01 or area > img_area * 0.98:
            continue

        peri = cv2.arcLength(c, True)
        # Tenta epsilon crescente para lidar com cantos arredondados
        for eps_factor in [0.02, 0.04, 0.06, 0.08]:
            approx = cv2.approxPolyDP(c, eps_factor * peri, True)
            if len(approx) == 4:
                card_contours.append(approx)
                break

    # Fallback: usa o maior contorno válido com minAreaRect
    if not card_contours and contours:
        valid = [c for c in contours
                 if img_area * 0.01 < cv2.contourArea(c) < img_area * 0.98]
        if valid:
            largest = max(valid, key=cv2.contourArea)
            rect = cv2.minAreaRect(largest)
            box = cv2.boxPoints(rect)
            box = np.intp(box).reshape(4, 1, 2)
            card_contours.append(box)

    return card_contours
