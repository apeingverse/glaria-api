from dotenv import load_dotenv
from fastapi import FastAPI
from app.routers import auth, quest_routes, user_routes, project, glaria_quest
from app.database import engine
from app.models import user
from app.models.twitter_token import TwitterToken  # ✅ explicitly imports the model class
from app.database import Base
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware

# Create the FastAPI app
app = FastAPI()

load_dotenv()

# ✅ Allow requests from your frontend (localhost or deployed frontend)
origins = [
    "http://localhost:5173",
    "https://www.glaria.xyz",
    "https://glaria-api.onrender.com"  # optional
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # or use ["*"] for all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
def read_root():
    return {"message": "GLARIA backend running 🚀"}

# Include routers
app.include_router(auth.router)
app.include_router(user_routes.router)
app.include_router(project.router)
app.include_router(quest_routes.router)
app.include_router(glaria_quest.router)


# Create database tables
Base.metadata.create_all(bind=engine)

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your API Name",
        version="1.0.0",
        description="Paste your access_token from /callback into the Authorize button.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi