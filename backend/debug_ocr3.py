import cv2
import numpy as np
import pytesseract

img = cv2.imread('/home/neto/Documentos/IOT-BLACKJACK/teste1.jpg')
h, w = img.shape[:2]
corner = img[0:int(h*0.30), 0:int(w*0.30)]

up = cv2.resize(corner, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)

# Isola regiao branca da carta
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
cr_h, cr_w = card_region.shape

# Usa apenas o quadrante superior-esquerdo (top-left 60%x60%) para pegar so o rank
rank_zone = card_region[:int(cr_h*0.60), :int(cr_w*0.60)]
print(f"rank_zone shape: {rank_zone.shape}")

_, thresh_bin = cv2.threshold(rank_zone, 120, 255, cv2.THRESH_BINARY)
thresh_inv = cv2.bitwise_not(thresh_bin)

# Encontra e preenche contornos (resolve "0" oco)
contours, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"Contornos: {len(contours)}")
for i, c in enumerate(contours):
    print(f"  {i}: area={cv2.contourArea(c):.0f}, bbox={cv2.boundingRect(c)}")

min_area = rank_zone.shape[0] * rank_zone.shape[1] * 0.003
filled = np.zeros_like(thresh_inv)
for c in contours:
    if cv2.contourArea(c) > min_area:
        cv2.drawContours(filled, [c], -1, 255, thickness=cv2.FILLED)

result = cv2.bitwise_not(filled)

# Adiciona padding branco para Tesseract
pad = 20
result_pad = cv2.copyMakeBorder(result, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)

for psm in [6, 7, 8, 11]:
    text = pytesseract.image_to_string(result_pad, config=f'--psm {psm} -c tessedit_char_whitelist=A123456789JQK0').strip()
    print(f"PSM {psm}: {repr(text)}")

cv2.imwrite('/tmp/rank_zone.jpg', rank_zone)
cv2.imwrite('/tmp/result_rankzone.jpg', result_pad)
print("Salvo em /tmp/")
