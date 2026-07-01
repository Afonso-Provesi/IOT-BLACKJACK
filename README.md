# Blackjack IoT (Multi-Room + MQTT)

Servidor e dashboard de Blackjack em tempo real, com arquitetura de terminais:

- Hub: gerencia mesas (salas)
- Terminal de mesa: controla rodada
- Terminais de jogador: enviam ações e recebem estado da mão

Comunicacao principal:

```text
Browser Hub/Table/Player  <->  FastAPI + WebSocket  <->  MQTT (Mosquitto)
```

Importante: este projeto nao usa mais reconhecimento de cartas por camera/OCR no fluxo principal do jogo.

---

## Stack

| Camada | Tecnologias |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn, Paho-MQTT |
| Frontend | React 18, Vite, Axios |
| Broker | Mosquitto 2.x |
| Containers | Docker + Docker Compose |

---

## Arquitetura Atual

Cada sala possui:

- `room_id` unico
- `table_terminal_id` (ex.: `table-mesa-principal`)
- estado completo do jogo
- ate 5 jogadores por mesa

O backend:

- publica estado consolidado no MQTT por sala
- publica estado individual de cada jogador
- recebe acao de jogador e de mesa via topicos MQTT
- transmite estado para UI via WebSocket (`/ws?room_id=...`)

Controle de propriedade dos terminais:

- cada browser recebe um `device_id`
- requests enviam `X-Device-ID`
- o backend bloqueia controle de jogador criado por outro dispositivo (403)
- um mesmo dispositivo pode criar/controlar varios jogadores proprios

---

## Estrutura do Projeto

```text
IOT-BLACKJACK/
├── backend/
│   ├── app/
│   │   ├── main.py          # API REST + WS + bridge MQTT
│   │   ├── game_engine.py   # Motor do blackjack (server-driven)
│   │   ├── room_manager.py  # Registro e ciclo de vida das salas
│   │   ├── mqtt_manager.py  # Pub/Sub MQTT por topicos de sala
│   │   ├── config.py
│   │   └── logger.py
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── hooks/useWebSocket.js
│   │   ├── components/
│   │   │   ├── HubView.jsx
│   │   │   ├── Table.jsx
│   │   │   ├── CreateRoomModal.jsx
│   │   │   └── AddPlayerModal.jsx
│   │   └── utils/deviceId.js
│   ├── vite.config.js
│   └── Dockerfile
├── mosquitto/mosquitto.conf
├── docker-compose.yml
├── start.sh
├── start.bat
└── README.md
```

---

## Topicos MQTT

### Publicados pelo backend

| Topico | Conteudo |
|---|---|
| `blackjack/hub/state` | Resumo de todas as salas |
| `blackjack/rooms/{room_id}/game/state` | Estado completo da mesa |
| `blackjack/rooms/{room_id}/players/{player_id}/hand` | Estado individual do jogador |

### Assinados pelo backend

| Topico | Conteudo |
|---|---|
| `blackjack/rooms/{room_id}/players/{player_id}/action` | Acoes do jogador (`hit`, `stand`, `split`, `double`, `bet:valor`) |
| `blackjack/rooms/{room_id}/tables/{table_id}/action` | Acoes da mesa (`start_round`, `dealer_play`, `reset`, `new_game`, etc.) |

---

## Endpoints Principais

### Infra

- `GET /health`
- `GET /docs`
- `WS /ws?room_id={id}`

### Salas

- `GET /rooms`
- `POST /rooms`
- `GET /rooms/{room_id}`
- `DELETE /rooms/{room_id}` (exceto `mesa-principal`)

### Jogo por sala

- `GET /rooms/{room_id}/game/state`
- `POST /rooms/{room_id}/game/players`
- `DELETE /rooms/{room_id}/game/players/{player_id}`
- `POST /rooms/{room_id}/game/players/{player_id}/bet`
- `POST /rooms/{room_id}/game/start`
- `POST /rooms/{room_id}/game/players/{player_id}/hit`
- `POST /rooms/{room_id}/game/players/{player_id}/stand`
- `POST /rooms/{room_id}/game/players/{player_id}/split`
- `POST /rooms/{room_id}/game/players/{player_id}/double`
- `POST /rooms/{room_id}/game/dealer/play`
- `POST /rooms/{room_id}/game/reset`
- `POST /rooms/{room_id}/game/new-game`

Obs.: tambem existem rotas equivalentes sem `room_id`, operando na sala padrao `mesa-principal`.

---

## Pre-requisitos

- Python 3.11+
- Node.js 20+
- Mosquitto (broker MQTT)
- opcional: Docker + Docker Compose

### Instalar Mosquitto

Linux (Debian/Ubuntu):

```bash
sudo apt install mosquitto mosquitto-clients
```

macOS:

```bash
brew install mosquitto
```

Windows:

- https://mosquitto.org/download/

---

## Execucao em Desenvolvimento

### Script automatico (recomendado)

Linux/macOS:

```bash
chmod +x start.sh
./start.sh
```

Windows:

```bat
start.bat
```

### Manual (3 terminais)

1. Broker MQTT

```bash
mosquitto -c mosquitto/mosquitto.conf -v
```

2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

3. Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Docker

```bash
docker-compose up --build
```

Servicos:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8001`
- Docs: `http://localhost:8001/docs`
- MQTT: `localhost:1883`

---

## Monitoramento MQTT

Escutar estado global + estado de salas/jogadores:

```bash
mosquitto_sub -h localhost -p 1883 -t "blackjack/hub/state" -t "blackjack/rooms/#" -v
```

Escutar somente a sala `mesa-principal`:

```bash
mosquitto_sub -h localhost -p 1883 -t "blackjack/rooms/mesa-principal/#" -v
```

Publicar acao manual de jogador:

```bash
mosquitto_pub -h localhost -p 1883 \
  -t "blackjack/rooms/mesa-principal/players/p1/action" \
  -m "hit"
```

Publicar acao de mesa manualmente:

```bash
mosquitto_pub -h localhost -p 1883 \
  -t "blackjack/rooms/mesa-principal/tables/table-mesa-principal/action" \
  -m '{"action":"start_round"}'
```

---

## Acesso Online com Ngrok

1. Autenticar ngrok (uma vez):

```bash
ngrok authtoken SEU_TOKEN
```

2. Com backend rodando em `8001`, abrir tunel:

```bash
ngrok http 8001
```

3. Compartilhar a URL HTTPS gerada (ex.: `https://xxxx-xxxx.ngrok.io`).

Notas:

- no plano gratuito a URL pode mudar a cada execucao
- para o frontend funcionar via tunel, as chamadas API/WS devem usar o mesmo host publico

---

## Variaveis de Ambiente (backend/.env)

```env
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_CLIENT_ID=blackjack_backend
LOG_LEVEL=INFO
```

---

## Status do Projeto

- Multi-room implementado
- Fluxo hub -> mesa -> jogadores implementado
- Controle de ownership por dispositivo implementado
- Limite de 5 jogadores por mesa implementado
- Exclusao de mesa implementada

---

## Licenca

MIT
