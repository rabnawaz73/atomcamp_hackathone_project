import logging
from pyngrok import ngrok

logger = logging.getLogger(__name__)

_public_url = None

def get_public_url(port=8501) -> str:
    """Start an ngrok tunnel and return the public URL (singleton)."""
    global _public_url
    if _public_url is None:
        try:
            # You can set NGROK_AUTHTOKEN in environment to avoid session limits
            tunnel = ngrok.connect(port)
            _public_url = tunnel.public_url
            logger.info("Ngrok tunnel established: %s", _public_url)
        except Exception as exc:
            logger.error("Failed to start ngrok: %s", exc)
            _public_url = f"http://localhost:{port}"
    return _public_url
