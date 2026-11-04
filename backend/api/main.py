from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from core import config
from core.auth import currentUser
from core.crypto import dummyHash
from core.db import ping
from core.error import registerErrorHandlers
from core.logger import configureLogging, getLogger
from core.middleware import OriginCheckMiddleware, RequestIdMiddleware
from core.request_context import REQUEST_ID_HEADER
from core.storage import closeStorage
from modules.auth.router import router as authRouter
from modules.user.router import router as userRouter
from worker.main import startEmbeddedWorker

log = getLogger(__name__)

APP_NAME = "Utopia"
APP_VERSION = "0.1.0"
PUBLIC_ROUTES = frozenset({
    ("POST", "/auth/login"),
    ("POST", "/auth/password/reset"),
    ("GET", "/health"),
    ("GET", "/info"),
})
ALLOWED_METHODS = ["GET", "POST", "PATCH", "PUT", "DELETE"]
ALLOWED_HEADERS = ["Content-Type", REQUEST_ID_HEADER]
EMBEDDED_WORKER_STOP_SECONDS = 10

systemRouter = APIRouter()

# Names the service and its version without touching the database, as a fast liveness check.
@systemRouter.get("/info")
def info():
    return {"app": APP_NAME, "version": APP_VERSION}

# Says whether the service can reach its database, answering 503 when it cannot.
@systemRouter.get("/health")
def health():
    try:
        ping()
        return {"status": "ok", "checks": {"db": "ok"}}
    except Exception as error:
        log.error("health_check_db_failed error_type=%s", type(error).__name__)
        return JSONResponse({"status": "down", "checks": {"db": "error"}}, status_code=503)

# Returns whether a dependency tree includes the session-resolving dependency.
def requiresAuth(dependant):
    if dependant.call is currentUser:
        return True
    return any(requiresAuth(child) for child in dependant.dependencies)

# Raises when a route of any given router lacks an auth dependency and is not on the public allow list.
def assertRoutesProtected(routers, publicRoutes=PUBLIC_ROUTES):
    unprotected = []
    for router in routers:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                unprotected.append(f"{route.path} (not an API route)")
            elif not requiresAuth(route.dependant):
                unprotected.extend(f"{method} {route.path}" for method in route.methods if (method, route.path) not in publicRoutes)
    if unprotected:
        raise RuntimeError("Routes without authentication: " + ", ".join(sorted(unprotected)))

# Returns every router to register; add new feature routers here.
def featureRouters():
    return [systemRouter, authRouter, userRouter]

# Validates required settings at server start, warms the dummy password hash, and runs the worker
# in a background thread when WORKER_EMBEDDED is on, stopping it and the storage client at shutdown.
@asynccontextmanager
async def lifespan(app):
    config.requireStartupSettings()
    dummyHash()
    embedded = startEmbeddedWorker() if config.workerEmbedded() else None
    try:
        yield
    finally:
        if embedded is not None:
            worker, thread = embedded
            worker.stop()
            thread.join(EMBEDDED_WORKER_STOP_SECONDS)
        closeStorage()

# Builds the FastAPI application; run with uvicorn api.main:createApp --factory --app-dir backend.
def createApp():
    configureLogging()
    app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(OriginCheckMiddleware)
    app.add_middleware(
        CORSMiddleware, allow_origins=[config.allowedOrigin()], allow_credentials=True,
        allow_methods=ALLOWED_METHODS, allow_headers=ALLOWED_HEADERS,
    )
    app.add_middleware(RequestIdMiddleware)
    registerErrorHandlers(app)
    routers = featureRouters()
    assertRoutesProtected(routers)
    for router in routers:
        app.include_router(router)
    return app

_builtApp = {}

# Builds the module-level app on first access, so `uvicorn api.main:app` works and importing stays side-effect free.
def __getattr__(name):
    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if "app" not in _builtApp:
        _builtApp["app"] = createApp()
    return _builtApp["app"]


__all__ = ["APP_VERSION", "PUBLIC_ROUTES", "assertRoutesProtected", "createApp", "featureRouters"]
