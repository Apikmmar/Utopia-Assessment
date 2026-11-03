from fastapi import FastAPI

from backend.api.middleware import RequestIdMiddleware
from backend.core.logger import configureLogging

# Builds the FastAPI application with request-id middleware and shared logging.
def createApp():
    configureLogging()
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    return app

app = createApp()
