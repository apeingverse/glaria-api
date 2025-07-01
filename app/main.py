from fastapi import FastAPI
from app.routers import auth, user_routes, project
from app.database import engine
from app.models import user  # Make sure models are imported so tables get created

from fastapi.security import HTTPBearer

# Create the FastAPI app
app = FastAPI()

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "GLARIA backend running 🚀"}

# Include routers
app.include_router(auth.router)
app.include_router(user_routes.router)
app.include_router(project.router)



# Create database tables
user.Base.metadata.create_all(bind=engine)



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