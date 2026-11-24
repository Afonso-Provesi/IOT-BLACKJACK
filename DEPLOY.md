# Deploy

O projeto roda como **um único contêiner** (front-end React compilado + API FastAPI) conectado a um **broker MQTT**. Existem duas formas de colocar no ar:

| | Opção A: EMQX + Render | Opção B: AWS EC2 |
|---|---|---|
| Custo | Grátis, sem cartão | Créditos do plano Free da AWS |
| Broker MQTT | EMQX Cloud Serverless (TLS 8883) | Mosquitto próprio com senha |
| Duração | Permanente | Até 6 meses (fim do plano Free) |
| Observação | Dorme após 15 min sem acesso | Sempre ligado enquanto houver crédito |

Arquivos envolvidos:

- `Dockerfile`: imagem de produção (build do front + backend)
- `render.yaml`: blueprint do Render
- `deploy/aws/`: `docker-compose.yml`, `mosquitto.conf`, `setup-ubuntu.sh` e `deploy.sh`

Variáveis de ambiente do backend (veja `backend/.env.example`):

| Variável | Exemplo | Descrição |
|---|---|---|
| `MQTT_BROKER_HOST` | `xxxx.ala.us-east-1.emqxsl.com` | Endereço do broker |
| `MQTT_BROKER_PORT` | `8883` | 8883 = TLS, 1883 = sem TLS |
| `MQTT_TLS` | `true` | Liga TLS (padrão: `true` se a porta for 8883) |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | | Login criado no broker |
| `MQTT_CA_CERT_PEM` | `-----BEGIN CERTIFICATE-----...` | Opcional: CA do broker, se não for pública |
| `PORT` | `10000` | Porta HTTP (o Render define sozinho) |

---

## Opção A: EMQX Serverless + Render (grátis)

### 1. Broker no EMQX Cloud

1. Crie uma conta em <https://www.emqx.com/en/cloud> e escolha **Serverless**.
2. Crie o deployment (qualquer região AWS, por exemplo `us-east-1`).
3. Em **Spend Limit**, deixe **0**: assim nunca há cobrança, só a cota grátis.
4. Em **Access Control → Authentication**, adicione um usuário e uma senha.
5. Em **Overview**, anote o **Address** (ex.: `xxxx.ala.us-east-1.emqxsl.com`) e a porta **MQTT over TLS: 8883**.
   Se o painel oferecer o download do **CA Certificate**, guarde o arquivo; ele só é necessário se a conexão falhar com erro de certificado.

### 2. Aplicação no Render

1. Entre em <https://render.com> com a conta do GitHub.
2. **New → Web Service** → escolha o repositório `IOT-BLACKJACK`.
3. O Render detecta o `Dockerfile`. Em **Instance Type**, escolha **Free**.
4. Em **Environment Variables**, adicione:
   - `MQTT_BROKER_HOST` = endereço do EMQX
   - `MQTT_BROKER_PORT` = `8883`
   - `MQTT_TLS` = `true`
   - `MQTT_USERNAME` e `MQTT_PASSWORD` = login criado no EMQX
   - (só se der erro de certificado) `MQTT_CA_CERT_PEM` = conteúdo do arquivo `.crt` do EMQX
5. Em **Advanced → Health Check Path**, coloque `/health`.
6. Clique em **Deploy**. Ao terminar, o site fica em `https://iot-blackjack-xxxx.onrender.com`.

Nos logs do Render deve aparecer `MQTT conectado a ...:8883`. Como o plano grátis dorme após 15 minutos sem acesso, o primeiro acesso depois disso leva cerca de 1 minuto.

> Se o Render pedir cartão para criar o serviço, não cadastre: a página de Docker do Render diz que não precisa, mas alguns usuários relatam o pedido.

---

## Opção B: AWS EC2 (plano Free)

> **Proteção de custo:** na criação da conta, escolha o **Free plan** (nunca o *Paid plan*). No plano Free, o consumo sai dos créditos e o cartão não é cobrado; quando os créditos acabam ou completam 6 meses, a conta é encerrada. O cartão é pedido só para verificação (bloqueio temporário de US$ 1).

### 1. Criar a instância

1. Console AWS → região **São Paulo (sa-east-1)** → **EC2 → Launch instance**.
2. **Nome:** `iot-blackjack`.
3. **AMI:** Ubuntu Server 24.04 LTS.
4. **Instance type:** `t3.micro` (com o selo *Free tier eligible*).
5. **Key pair:** *Proceed without a key pair* (vamos usar o EC2 Instance Connect pelo navegador).
6. **Network settings → Edit → Security group**, permitir:
   - SSH (22): Anywhere (necessário para o Instance Connect)
   - HTTP (80): Anywhere
   - Custom TCP 1883: Anywhere (opcional, para terminais MQTT externos)
7. **Storage:** 16 GB gp3.
8. **Launch instance**.

### 2. Instalar e subir

Selecione a instância → **Connect → EC2 Instance Connect → Connect**. No terminal que abrir:

```bash
git clone https://github.com/Afonso-Provesi/IOT-BLACKJACK.git iot-blackjack
bash iot-blackjack/deploy/aws/setup-ubuntu.sh
```

Feche a aba, conecte de novo e rode:

```bash
cd iot-blackjack/deploy/aws
./deploy.sh
```

Ele pede um usuário e uma senha para o broker MQTT (criados na hora) e, no fim, mostra o endereço `http://<IP-público>`.

### 3. Operação

- **Atualizar** depois de mudanças no GitHub: `cd ~/iot-blackjack && git pull && cd deploy/aws && ./deploy.sh`
- **Logs:** `docker compose logs -f app`
- **Terminal de jogador pela internet:**
  ```bash
  MQTT_BROKER_HOST=<IP-público> MQTT_USERNAME=<usuário> MQTT_PASSWORD=<senha> \
    python3 player_terminal.py p1
  ```
- **Economizar créditos:** pare a instância quando não estiver usando (*Instance state → Stop*). O IP público muda ao religar.
- **Encerrar:** *Instance state → Terminate*.

---

## Desenvolvimento local

```bash
docker compose up --build        # Mosquitto + backend + frontend
# ou
./start.sh                       # sem Docker
```

Testar a imagem de produção localmente:

```bash
docker build -t iot-blackjack .
docker run -p 8001:8001 -e MQTT_BROKER_HOST=host.docker.internal iot-blackjack
```
