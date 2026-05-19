import asyncio
import json
import time
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import MQTT_TOPIC_RESULT, MQTT_TOPIC_STATUS
from app.mqtt_manager import mqtt_manager
from app.pipeline import process_frame
from app.history import history_store
from app.image_processing import decode_base64_image, encode_image_base64
from app.logger import logger
import threading
import cv2
import numpy as np

app = FastAPI(
    title="Blackjack Vision IoT",
    description="Backend de detecção de cartas via MQTT + OpenCV + EasyOCR",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
# WebSocket broadcaster (push de resultados para o frontend)
# ------------------------------------------------------------------ #
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self.active:
                self.active.remove(ws)

    async def broadcast(self, data: dict):
        payload = json.dumps(data)
        disconnected = []
        for ws in list(self.active):
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            await self.disconnect(ws)


ws_manager = ConnectionManager()
_loop: asyncio.AbstractEventLoop = None


def _on_frame_received(raw_bytes: bytes):
    """Callback executado em thread MQTT; despacha pipeline e broadcast."""
    result = process_frame(raw_bytes)
    if result and _loop:
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(result), _loop)


# ------------------------------------------------------------------ #
# Lifecycle
# ------------------------------------------------------------------ #
@app.on_event("startup")
async def startup():
    global _loop
    _loop = asyncio.get_event_loop()
    mqtt_manager.start(frame_callback=_on_frame_received)
    logger.info("Aplicação iniciada.")


@app.on_event("shutdown")
async def shutdown():
    mqtt_manager.stop()
    logger.info("Aplicação encerrada.")


# ------------------------------------------------------------------ #
# REST endpoints auxiliares
# ------------------------------------------------------------------ #
@app.get("/health")
def health():
    return {
        "status": "ok",
        "mqtt_connected": mqtt_manager.is_connected,
        "timestamp": time.time(),
    }


@app.get("/history")
def get_history():
    return {"results": history_store.get_all()}


@app.delete("/history")
def clear_history():
    history_store.clear()
    return {"message": "Histórico limpo."}


@app.post("/simulate/upload")
async def simulate_upload(file: UploadFile = File(...)):
    """
    Endpoint para simular envio de imagem sem câmera física.
    Lê o arquivo, publica via MQTT e retorna o resultado.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Formato não suportado. Use JPEG, PNG ou WEBP.")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    # Publica no tópico MQTT (simula câmera)
    mqtt_manager.publish_frame(raw)
    logger.info(f"Frame simulado publicado via upload ({len(raw)} bytes).")

    # Também processa diretamente para retornar resultado imediato na resposta HTTP
    result = process_frame(raw)
    return JSONResponse(content=result or {"status": "no_cards_detected"})


@app.post("/simulate/base64")
async def simulate_base64(body: dict):
    """Recebe imagem em base64 e simula publicação MQTT."""
    b64 = body.get("image")
    if not b64:
        raise HTTPException(status_code=400, detail="Campo 'image' ausente.")
    try:
        img = decode_base64_image(b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Imagem inválida: {e}")

    success, buf = cv2.imencode(".jpg", img)
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao recodificar imagem.")

    raw = buf.tobytes()
    mqtt_manager.publish_frame(raw)
    result = process_frame(raw)
    return JSONResponse(content=result or {"status": "no_cards_detected"})


# ------------------------------------------------------------------ #
# WebSocket para streaming de resultados em tempo real
# ------------------------------------------------------------------ #
@app.websocket("/ws/results")
async def websocket_results(ws: WebSocket):
    await ws_manager.connect(ws)
    logger.info("WebSocket client conectado.")
    try:
        while True:
            # Mantém conexão viva; dados são enviados via broadcast
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)
        logger.info("WebSocket client desconectado.")
