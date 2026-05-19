# ♠ Blackjack Vision IoT

Sistema fullstack de **detecção de cartas de blackjack** usando visão computacional, com comunicação exclusiva via **MQTT**.

```
Camera Publisher ──► MQTT Broker ──► Backend Subscriber ──► Frontend Dashboard
                  (Mosquitto)      (FastAPI + OpenCV)       (React + Vite)
```

---

## Tecnologias

| Camada | Stack |
|--------|-------|
| Broker | Mosquitto 2.0 |
| Backend | Python 3.11, FastAPI, OpenCV, EasyOCR, PyTorch, Paho-MQTT |
| Frontend | React 18, Vite, TailwindCSS, Axios |
| Containerização | Docker + Docker Compose |

---

## Estrutura do Projeto

```
IOT-BLACKJACK/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI + WebSocket + lifecycle
│   │   ├── config.py            # Variáveis de ambiente
│   │   ├── mqtt_manager.py      # Cliente MQTT (pub/sub)
│   │   ├── pipeline.py          # Pipeline de detecção completo
│   │   ├── image_processing.py  # OpenCV: pré-proc, contornos, perspectiva
│   │   ├── card_detector.py     # EasyOCR: rank, suit, valor BJ
│   │   ├── history.py           # Armazenamento em memória
│   │   └── logger.py            # Loguru
│   ├── camera_publisher.py      # Publisher MQTT simulado
│   ├── generate_sample_cards.py # Gera imagens de exemplo com PIL
│   ├── run.py                   # Entry point uvicorn
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Layout principal
│   │   ├── api.js               # Axios client
│   │   ├── hooks/
│   │   │   └── useWebSocket.js  # Hook WebSocket com reconexão
│   │   ├── components/
│   │   │   ├── CardBadge.jsx    # Exibe uma carta detectada
│   │   │   ├── ResultPanel.jsx  # Painel de resultado atual
│   │   │   ├── ImageUploader.jsx# Upload/drag-and-drop
│   │   │   ├── HistoryList.jsx  # Histórico de detecções
│   │   │   └── StatusBar.jsx    # Indicadores MQTT/WS
│   │   └── utils/
│   │       └── cardUtils.js     # Helpers de formatação
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
├── mosquitto/
│   └── mosquitto.conf
├── docker-compose.yml
├── start.bat                    # Windows
├── start.sh                     # Linux/macOS
└── README.md
```

---

## Tópicos MQTT

| Tópico | Direção | Conteúdo |
|--------|---------|----------|
| `blackjack/camera/frame` | Publisher → Broker → Backend | Bytes brutos da imagem (JPEG/PNG) |
| `blackjack/result` | Backend → Broker → Frontend | JSON com cartas, valores e metadados |
| `blackjack/status` | Backend → Broker | JSON com status online/offline/erro |

---

## Pré-requisitos

- Python 3.11+
- Node.js 20+
- Mosquitto MQTT Broker
- (Opcional) Docker + Docker Compose

### Instalar Mosquitto

**Windows:** https://mosquitto.org/download/  
**Ubuntu/Debian:**
```bash
sudo apt install mosquitto mosquitto-clients
```
**macOS:**
```bash
brew install mosquitto
```

---

## Execução — Modo Desenvolvimento

### 1. Iniciar automaticamente (recomendado)

**Windows:**
```bat
start.bat
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

---

### 2. Iniciar manualmente (passo a passo)

#### Mosquitto
```bash
mosquitto -c mosquitto/mosquitto.conf -v
```

#### Backend
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
mkdir logs
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Execução — Docker Compose

```bash
docker-compose up --build
```

---

## Serviços e Endpoints

| Serviço | URL |
|---------|-----|
| Frontend (Dashboard) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Documentação interativa (Swagger) | http://localhost:8000/docs |
| WebSocket resultados | ws://localhost:8000/ws/results |
| MQTT Broker | localhost:1883 |

### Endpoints REST auxiliares

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Status do sistema e conexão MQTT |
| GET | `/history` | Últimos 100 resultados |
| DELETE | `/history` | Limpa histórico |
| POST | `/simulate/upload` | Envia imagem (multipart) via MQTT |
| POST | `/simulate/base64` | Envia imagem base64 via MQTT |

---

## Simular Câmera (Publisher MQTT)

### Gerar imagens de exemplo
```bash
cd backend
python generate_sample_cards.py
# Cria backend/sample_cards/*.jpg
```

### Publicar uma imagem
```bash
cd backend
python camera_publisher.py --image sample_cards/A_spades.jpg
```

### Publicar pasta em loop (intervalo de 3s)
```bash
python camera_publisher.py --folder sample_cards/ --interval 3 --loop
```

---

## Pipeline de Detecção

```
Bytes MQTT (blackjack/camera/frame)
        │
        ▼
1. Decodificação (OpenCV)
        │
        ▼
2. Pré-processamento
   - Redimensionamento (max 1024px)
        │
        ▼
3. Detecção de contornos
   - Canny + morphology
   - Filtragem por área e forma
        │
        ▼
4. Correção de perspectiva (warpPerspective)
        │
        ▼
5. OCR do canto superior (EasyOCR)
   - Rank (A, 2-10, J, Q, K)
   - Naipe (♠ ♥ ♦ ♣)
        │
        ▼
6. Cálculo do valor de Blackjack
   - Regra do Ás (11 → 1 se total > 21)
        │
        ▼
7. Publicação do resultado (blackjack/result)
   + Broadcast WebSocket → Frontend
```

---

## Formato do Resultado (JSON)

```json
{
  "frame_id": "a1b2c3d4",
  "timestamp": 1716123456.789,
  "cards_detected": 2,
  "cards": [
    {
      "card_index": 0,
      "rank": "A",
      "suit": "spades",
      "blackjack_value": 11,
      "confidence": 0.923
    },
    {
      "card_index": 1,
      "rank": "K",
      "suit": "hearts",
      "blackjack_value": 10,
      "confidence": 0.871
    }
  ],
  "total_value": 21,
  "processing_time_s": 0.342,
  "status": "ok"
}
```

---

## Variáveis de Ambiente (backend/.env)

```env
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_TOPIC_FRAME=blackjack/camera/frame
MQTT_TOPIC_RESULT=blackjack/result
MQTT_TOPIC_STATUS=blackjack/status
MQTT_CLIENT_ID=blackjack_backend
LOG_LEVEL=INFO
```

---

## Expansões Futuras

- **YOLOv8 customizado**: treinar modelo para detecção de cartas com dataset próprio.
- **Múltiplas câmeras**: adicionar identificador de câmera no payload MQTT.
- **Banco de dados**: persistir histórico em SQLite/PostgreSQL.
- **Autenticação MQTT**: TLS + usuário/senha no Mosquitto.
- **Dashboard de estatísticas**: gráficos de distribuição de mãos.
- **Modo jogo**: lógica completa de blackjack contra dealer virtual.

---

## Licença

MIT
