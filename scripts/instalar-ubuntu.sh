#!/usr/bin/env bash
# Instalação do Docker + Docker Compose em Ubuntu Server para rodar este projeto.
set -euo pipefail

if command -v docker &> /dev/null; then
  echo "Docker já instalado."
else
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "$USER"
  echo "Docker instalado. Talvez seja necessário reabrir a sessão para usar docker sem sudo."
fi

echo "Pronto. Em seguida: cp .env.example .env, preencher credenciais e rodar 'docker compose up -d --build'."
