from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import uuid
import subprocess
import os
import json
from pathlib import Path
from app.core.db import insert_job, update_job, insert_job_steps,get_ai_request, get_job as db_get_job, list_jobs as db_list_jobs
from app.ai.openai_client import generate_script

router = APIRouter()

class JobCreate(BaseModel):
    target: str
    playbook: str = "basic-recon"

def resolve_paths():
    this_file = Path(__file__).resolve()
    # Layout do container
    try_root = this_file.parents[2]  # /app
    exec_path = try_root / "app" / "workers" / "executor.py"
    pb_path   = try_root / "playbooks" / "basic-recon.yml"
    if exec_path.exists() and pb_path.exists():
        return exec_path, pb_path
    # Layout do host
    try_root2 = this_file.parents[3]  # repo root
    exec_path2 = try_root2 / "backend" / "app" / "workers" / "executor.py"
    pb_path2   = try_root2 / "backend" / "playbooks" / "basic-recon.yml"
    return exec_path2, pb_path2

@router.post("/jobs")
async def create_job(j: JobCreate):
    allowed = os.getenv("ALLOWED_TARGETS", "localhost,127.0.0.1").split(",")
    if not any(a.strip() and a.strip() in j.target for a in allowed):
        raise HTTPException(status_code=400, detail="target not allowed")

    job_id = str(uuid.uuid4())
    insert_job(job_id, j.target, j.playbook, "running", None)

    try:
        executor, playbook_file = resolve_paths()
        if not executor.exists():
            raise RuntimeError(f"executor not found at {executor}")
        if not playbook_file.exists():
            raise RuntimeError(f"playbook not found at {playbook_file}")

        res = subprocess.run(
            ["python3", str(executor), str(playbook_file), j.target],
            capture_output=True, text=True, timeout=180
        )

        if res.returncode != 0:
            update_job(job_id, "error", {"stderr": res.stderr, "stdout": res.stdout})
            return {"job_id": job_id, "status": "error", "stderr": res.stderr, "stdout": res.stdout}

        try:
            parsed = json.loads(res.stdout)
        except Exception:
            parsed = {"raw_stdout": res.stdout}

        steps = parsed.get("steps") or []
        insert_job_steps(job_id, steps)

        update_job(job_id, "done", parsed)
        return {"job_id": job_id, "status": "done", "result": parsed}

    except Exception as e:
        update_job(job_id, "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = db_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job

@router.get("/jobs")
async def list_jobs(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return db_list_jobs(limit=limit, offset=offset)

# ---------------- AI endpoints ----------------

class AIGenerateRequest(BaseModel):
    prompt: str
    model: str = None

@router.post("/ai/generate")
async def ai_generate(req: AIGenerateRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt required")
    out = generate_script(req.prompt, model=req.model)
    # retorna sempre JSON serializável
    return {
        "request_id": out.get("id"),
        "model": out.get("model"),
        "script": out.get("script"),
        "raw": out.get("raw_response"),
    }


@router.get("/ai/requests/{req_id}")
async def ai_get(req_id: str):
    r = get_ai_request(req_id)
    if not r:
        raise HTTPException(status_code=404, detail="not found")
    return r
