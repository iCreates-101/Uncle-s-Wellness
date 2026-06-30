"""Cloud Functions HTTP entry point — bridges FastAPI (ASGI) to Cloud Functions (WSGI)."""

import sys
import os

# Add project root to path so we can import app
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from flask import Response
from a2wsgi import ASGIMiddleware
from app.main import app as fastapi_app

# Convert FastAPI (ASGI) → WSGI callable
wsgi_app = ASGIMiddleware(fastapi_app)


def function(request):
    """Cloud Functions HTTP entry point (1st & 2nd gen compatible).

    'request' is a Flask Request object from the Cloud Functions runtime.
    """
    status_code = [200]
    response_headers = {}

    def start_response(status, headers):
        status_code[0] = int(status.split(" ")[0])
        for key, value in headers:
            response_headers[key.lower()] = value

    body_iter = wsgi_app(request.environ, start_response)
    body = b"".join(body_iter)

    content_type = response_headers.get("content-type", "text/html")
    resp = Response(body, status=status_code[0], content_type=content_type)
    for key, value in response_headers.items():
        if key not in ("content-length", "content-type"):
            resp.headers[key] = value
    return resp
