#!/bin/bash
# Script de démarrage du frontend

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Installer les dépendances si node_modules n'existe pas
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Build si dist n'existe pas
if [ ! -d "dist" ]; then
    echo "Building frontend..."
    npm run build
fi

# Lancer le serveur de preview
PORT="${PORT:-4173}"
echo "Starting frontend on port $PORT..."
exec npx vite preview --host --port "$PORT"
