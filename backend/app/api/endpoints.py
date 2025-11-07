from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
import subprocess
import os
import json
from pathlib import Path

router = APIRouter()
JOBS = {}

class JobCreate(BaseModel):
    target: str
    playbook: str = "basic-recon"

def resolve_paths():
    """Resolve executor and playbook paths for both container and host layouts.
    Container layout (web image):
        /app/app/api/endpoints.py   (this file)
        /app/app/workers/executor.py
        /app/playbooks/basic-recon.yml
    Host layout (repo root):
        backend/app/api/endpoints.py (this file)
        backend/app/workers/executor.py
        backend/playbooks/basic-recon.yml
    """
    this_file = Path(__file__).resolve()

    # Container-first guess
    try_root = this_file.parents[2]  # /app
    exec_path = try_root / "app" / "workers" / "executor.py"
    pb_path   = try_root / "playbooks" / "basic-recon.yml"
    if exec_path.exists() and pb_path.exists():
        return exec_path, pb_path

    # Host-layout fallback
    try_root2 = this_file.parents[3]  # repo root when running on host
    exec_path2 = try_root2 / "backend" / "app" / "workers" / "executor.py"
    pb_path2   = try_root2 / "backend" / "playbooks" / "basic-recon.yml"
    return exec_path2, pb_path2

@router.post("/jobs")
async def create_job(j: JobCreate):
    allowed = os.getenv("ALLOWED_TARGETS", "localhost,127.0.0.1").split(",")
    if not any(a.strip() and a.strip() in j.target for a in allowed):
        raise HTTPException(status_code=400, detail="target not allowed")

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "running", "target": j.target}

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
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["stderr"] = res.stderr
            return {"job_id": job_id, "status": "error", "stderr": res.stderr, "stdout": res.stdout}

        try:
            parsed = json.loads(res.stdout)
        except Exception:
            parsed = {"raw_stdout": res.stdout}

        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["result"] = parsed
        return {"job_id": job_id, "status": "done", "result": parsed}

    except Exception as e:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="job not found")
    return JOBS[job_id]
