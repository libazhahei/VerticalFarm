from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from uvicorn import run

from route.history import history_router
from route.others import other_router

app = FastAPI()
app.include_router(other_router, prefix="/api", tags=["others"])
app.include_router(history_router, prefix="/api/history", tags=["history"])
# CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Serve static files from the 'static' directory
app.mount("/static", StaticFiles(directory="static"), name="static")
# Serve the index.html file at the root path
@app.get("/")
async def read_index(request: Request) -> dict:
    """Hello World endpoint."""
    return {"message": "Welcome to the API"}

if __name__ == "__main__":
    run(app, host="127.0.0.1", port=8000)
