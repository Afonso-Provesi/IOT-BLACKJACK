import cv2
import numpy as np
import pytesseract

img = cv2.imread('/home/neto/Documentos/IOT-BLACKJACK/teste1.jpg')
h, w = img.shape[:2]
corner = img[0:int(h*0.30), 0:int(w*0.30)]

up = cv2.resize(corner, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)

# Isola região branca da carta
_, white_mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(white_mask, connectivity=8)
if num_labels > 1:
    largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    x, y, ww, hh = (stats[largest, cv2.CC_STAT_LEFT], stats[largest, cv2.CC_STAT_TOP],
                    stats[largest, cv2.CC_STAT_WIDTH], stats[largest, cv2.CC_STAT_HEIGHT])
    card_region = gray[y:y+hh, x:x+ww]
else:
    card_region = gray

print(f"card_region shape: {card_region.shape}")

# Usa a regiao COMPLETA e aplica threshold 120
_, thresh_bin = cv2.threshold(card_region, 120, 255, cv2.THRESH_BINARY)
thresh_inv = cv2.bitwise_not(thresh_bin)  # texto branco em fundo preto

# Encontra contornos externos e imprime info
contours, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"Contornos encontrados: {len(contours)}")
for i, c in enumerate(contours):
    area = cv2.contourArea(c)
    x_, y_, wc, hc = cv2.boundingRect(c)
    print(f"  Contorno {i}: area={area:.0f}, bbox=({x_},{y_},{wc},{hc})")

# Filtra por tamanho minimo e preenche
min_area = card_region.shape[0] * card_region.shape[1] * 0.005
filled = np.zeros_like(thresh_inv)
for c in contours:
    if cv2.contourArea(c) > min_area:
        cv2.drawContours(filled, [c], -1, 255, thickness=cv2.FILLED)

result = cv2.bitwise_not(filled)

for psm in [6, 7, 8, 11]:
    text = pytesseract.image_to_string(result, config=f'--psm {psm} -c tessedit_char_whitelist=A123456789JQK0').strip()
    print(f"PSM {psm}: {repr(text)}")

cv2.imwrite('/tmp/card_region_full.jpg', card_region)
cv2.imwrite('/tmp/filled_full.jpg', filled)
cv2.imwrite('/tmp/result_full.jpg', result)
print("Salvo em /tmp/")
