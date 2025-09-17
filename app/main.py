# app/main.py
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, farcaster, quest_routes, user_routes, project, glaria_quest, farcaster_quests
from app.database import engine, Base

load_dotenv()

app = FastAPI(title=settings.APP_NAME)

# CORS with credentials (for cookie sessions)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=settings.ALLOW_CREDENTIALS,
    allow_methods=settings.ALLOW_METHODS,
    allow_headers=settings.ALLOW_HEADERS,
)

@app.get("/")
def read_root():
    return {"message": "GLARIA backend running 🚀"}

# Routers
app.include_router(auth.router)
app.include_router(user_routes.router)
app.include_router(project.router)
app.include_router(quest_routes.router)
app.include_router(glaria_quest.router)
app.include_router(farcaster.router)
app.include_router(farcaster_quests.router)

# Create DB tables
Base.metadata.create_all(bind=engine)

# OpenAPI: keep your existing helper
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your API",
        version="1.0.0",
        description="Paste your access_token into the Authorize button to test secured routes.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
