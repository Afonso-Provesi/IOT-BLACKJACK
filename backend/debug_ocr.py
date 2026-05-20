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

# Toma só o top 40% da carta (onde está o rank, sem o naipe)
rank_region = card_region[:int(card_region.shape[0]*0.40), :]

# Threshold
_, thresh_bin = cv2.threshold(rank_region, 120, 255, cv2.THRESH_BINARY)

# Inverte (texto preto em bg branco → texto branco em bg preto)
thresh_inv = cv2.bitwise_not(thresh_bin)

# Preenche contornos externos (resolve "0" oco)
contours, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
filled = np.zeros_like(thresh_inv)
cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)

# Inverte de volta: texto preto em fundo branco
result = cv2.bitwise_not(filled)

for psm in [6, 7, 8, 11, 12]:
    text = pytesseract.image_to_string(result, config=f'--psm {psm} -c tessedit_char_whitelist=A123456789JQK0').strip()
    print(f"PSM {psm}: {repr(text)}")

cv2.imwrite('/tmp/rank_region.jpg', rank_region)
cv2.imwrite('/tmp/thresh_inv.jpg', thresh_inv)
cv2.imwrite('/tmp/filled_result.jpg', result)
print("Imagens salvas em /tmp/"

cv2.imwrite('/tmp/rank_region.jpg', rank_region)
cv2.imwrite('/tmp/thresh_inv.jpg', thresh_inv)
cv2.imwrite('/tmp/filled_result.jpg', result)
print("Imagens salvas em /tmp/")
