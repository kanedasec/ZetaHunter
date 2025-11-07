from fastapi import FastAPI
from app.api.endpoints import router as jobs_router

app = FastAPI(title="Bug Hunter AI - MVP")
app.include_router(jobs_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
