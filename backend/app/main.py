from fastapi import FastAPI
from app.api.endpoints import router as jobs_router
from app.core.db import init_db

app = FastAPI(title="Bug Hunter AI - MVP")
init_db()
app.include_router(jobs_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
