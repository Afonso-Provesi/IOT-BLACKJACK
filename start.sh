#!/usr/bin/env bash
# ============================================================
#  Blackjack Vision IoT — Script de inicialização (Linux/Mac)
# ============================================================
set -e

echo "[1/4] Iniciando Mosquitto MQTT Broker..."
mosquitto -c mosquitto/mosquitto.conf -v &
MOSQUITTO_PID=$!
sleep 2

echo "[2/4] Configurando backend Python..."
cd backend
if [ ! -x "venv/bin/python3" ]; then
    python3 -m venv venv
fi
BACKEND_DIR="$(pwd)"
VENV_PY="$(pwd)/venv/bin/python3"
if ! "$VENV_PY" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
    "$VENV_PY" -m pip install -r requirements.txt
fi
mkdir -p logs
"$VENV_PY" -m uvicorn --app-dir "$BACKEND_DIR" app.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
cd ..

sleep 3

echo "[3/4] Configurando frontend..."
cd frontend
[ ! -d "node_modules" ] && npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================================"
echo " Serviços iniciados:"
echo "  - MQTT Broker : localhost:1883"
echo "  - Backend API : http://localhost:8001"
echo "  - Frontend    : http://localhost:5173"
echo "  - Docs API    : http://localhost:8001/docs"
echo "============================================================"
echo "Pressione Ctrl+C para encerrar todos os processos."

trap "kill $MOSQUITTO_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
