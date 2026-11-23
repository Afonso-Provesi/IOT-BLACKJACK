#!/usr/bin/env bash
# Prepara uma instância EC2 Ubuntu nova: memória swap + Docker.
# Uso (uma vez só):  bash setup-ubuntu.sh
set -euo pipefail

# 2 GB de swap: a t3.micro tem só 1 GB de RAM e o build do front precisa de mais.
if ! swapon --show | grep -q /swapfile; then
  echo "[1/2] Criando 2 GB de swap..."
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[2/2] Instalando Docker..."
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

echo
echo "Pronto. Feche esta janela e abra uma nova conexão (para o grupo docker valer),"
echo "depois rode:  cd iot-blackjack/deploy/aws && ./deploy.sh"
