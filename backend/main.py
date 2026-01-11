"""
Linux Firewall & Network Manager - Backend
Main entry point for the FastAPI application
"""

import os
import uvicorn
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
