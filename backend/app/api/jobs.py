# backend/app/api/jobs.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.jobs_api import create_job_sync, get_job, list_all_jobs

router = APIRouter()

class JobCreate(BaseModel):
    target: str
    playbook: str
    timeout: Optional[int] = None

@router.post("/jobs")
def create_job(payload: JobCreate):
    if not payload.target or not payload.playbook:
        raise HTTPException(status_code=400, detail="target and playbook are required")
    result = create_job_sync(payload.target, payload.playbook, timeout=payload.timeout)
    return {"job_id": result["job_id"], "status": result["status"], "result": result.get("result")}

@router.get("/jobs")
def list_jobs():
    return list_all_jobs()

@router.get("/jobs/{job_id}")
def get_job_by_id(job_id: str):
    row = get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return row
