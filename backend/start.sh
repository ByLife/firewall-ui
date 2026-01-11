#!/bin/bash
# Script de démarrage du backend avec venv

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

# Créer le venv s'il n'existe pas
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activer le venv
source "$VENV_DIR/bin/activate"

# Installer/mettre à jour les dépendances
echo "Installing/updating dependencies..."
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q

# Lancer l'application
echo "Starting backend on port ${API_PORT:-8000}..."
exec python -u "$SCRIPT_DIR/main.py"
