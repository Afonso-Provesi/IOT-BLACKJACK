import cv2
import numpy as np
import pytesseract
from PIL import Image

img = cv2.imread('/home/neto/Documentos/IOT-BLACKJACK/teste1.jpg')
h, w = img.shape[:2]
corner = img[0:int(h*0.30), 0:int(w*0.30)]

# Testa com 2x upscale (menor que 4x)
for scale in [2, 3, 4]:
    up = cv2.resize(corner, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)

    _, white_mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(white_mask, connectivity=8)
    if num_labels > 1:
        largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        x0, y0, ww, hh = (stats[largest, cv2.CC_STAT_LEFT], stats[largest, cv2.CC_STAT_TOP],
                          stats[largest, cv2.CC_STAT_WIDTH], stats[largest, cv2.CC_STAT_HEIGHT])
        card_region = gray[y0:y0+hh, x0:x0+ww]
    else:
        card_region = gray

    cr_h, cr_w = card_region.shape
    rank_zone = card_region[:int(cr_h*0.60), :int(cr_w*0.60)]

    _, thresh_bin = cv2.threshold(rank_zone, 120, 255, cv2.THRESH_BINARY)
    thresh_inv = cv2.bitwise_not(thresh_bin)

    contours, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filtra contornos relevantes (nao muito pequenos, nao canto arredondado)
    min_area = rank_zone.shape[0] * rank_zone.shape[1] * 0.003
    valid_contours = []
    for c in contours:
        area = cv2.contourArea(c)
        bx, by, bw, bh = cv2.boundingRect(c)
        # Exclui canto arredondado (perto de (0,0) e pequeno) 
        if area > min_area and not (bx < 5 and by < 5):
            valid_contours.append(c)

    filled = np.zeros_like(thresh_inv)
    for c in valid_contours:
        cv2.drawContours(filled, [c], -1, 255, thickness=cv2.FILLED)
    result = cv2.bitwise_not(filled)
    
    pad = 15
    result_pad = cv2.copyMakeBorder(result, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)

    texts = []
    for psm in [6, 7, 8, 11, 13]:
        t = pytesseract.image_to_string(result_pad, config=f'--psm {psm} -c tessedit_char_whitelist=A123456789JQK0').strip()
        if t:
            texts.append(f'PSM{psm}={repr(t)}')
    print(f"Scale {scale}x ({rank_zone.shape}): {texts if texts else 'tudo vazio'}")
    
    if scale == 2:
        cv2.imwrite('/tmp/result_2x.jpg', result_pad)
        # image_to_data sem whitelist para diagnostico
        data = pytesseract.image_to_data(result_pad, config='--psm 6', output_type=pytesseract.Output.DICT)
        print(f"  image_to_data (scale 2): {list(zip(data['text'], data['conf']))}")

print("\n--- Teste sem whitelist ---")
up = cv2.resize(corner, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
_, white_mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(white_mask, connectivity=8)
if num_labels > 1:
    largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    x0, y0, ww, hh = (stats[largest, cv2.CC_STAT_LEFT], stats[largest, cv2.CC_STAT_TOP],
                      stats[largest, cv2.CC_STAT_WIDTH], stats[largest, cv2.CC_STAT_HEIGHT])
    card_region = gray[y0:y0+hh, x0:x0+ww]
cr_h, cr_w = card_region.shape
rank_zone = card_region[:int(cr_h*0.60), :int(cr_w*0.60)]
_, thresh_bin = cv2.threshold(rank_zone, 120, 255, cv2.THRESH_BINARY)
for psm in [6, 11]:
    t = pytesseract.image_to_string(thresh_bin, config=f'--psm {psm}').strip()
    print(f"No whitelist PSM{psm}: {repr(t)}")
    
# Testa com OEM 0 (legacy engine)
print("\n--- Teste OEM 0 ---")
_, thresh_bin = cv2.threshold(rank_zone, 120, 255, cv2.THRESH_BINARY)
thresh_inv = cv2.bitwise_not(thresh_bin)
contours, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
filled = np.zeros_like(thresh_inv)
for c in contours:
    if cv2.contourArea(c) > 100:
        cv2.drawContours(filled, [c], -1, 255, thickness=cv2.FILLED)
result = cv2.bitwise_not(filled)
result_pad = cv2.copyMakeBorder(result, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
for psm in [6, 11]:
    t = pytesseract.image_to_string(result_pad, config=f'--oem 0 --psm {psm} -c tessedit_char_whitelist=A123456789JQK0').strip()
    print(f"OEM0 PSM{psm}: {repr(t)}")
