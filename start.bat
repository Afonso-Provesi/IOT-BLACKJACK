@echo off
REM ============================================================
REM  Blackjack Vision IoT — Script de inicialização (Windows)
REM ============================================================

echo [1/4] Iniciando Mosquitto MQTT Broker...
start "Mosquitto" mosquitto -c mosquitto\mosquitto.conf -v

timeout /t 2 /nobreak >nul

echo [2/4] Ativando ambiente Python e iniciando backend...
cd backend
if not exist venv (
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)
start "Backend" uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
cd ..

timeout /t 3 /nobreak >nul

echo [3/4] Instalando dependências do frontend (se necessário)...
cd frontend
if not exist node_modules (
    npm install
)

echo [4/4] Iniciando frontend React...
start "Frontend" npm run dev
cd ..

echo.
echo ============================================================
echo  Servicos iniciados:
echo   - MQTT Broker : localhost:1883
echo   - Backend API : http://localhost:8000
echo   - Frontend     : http://localhost:5173
echo   - Docs API     : http://localhost:8000/docs
echo ============================================================
pause
