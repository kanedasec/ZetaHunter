import os
import json
import uuid
from pathlib import Path
import re
import requests
from requests.exceptions import ReadTimeout
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.provider import generate_script as generate_with_provider
from app.ai.provider import build_script_prompt
from app.core.db import insert_ai_request  # opcional
from app.core.jobs_api import create_job_sync
from app.ai.sanitizer import sanitize_and_validate_script

router = APIRouter()

EXAMPLES_DIR = Path("/app/examples")
TEMP_PLAYBOOK_DIR = Path("/app/playbooks/tmp")
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
TEMP_PLAYBOOK_DIR.mkdir(parents=True, exist_ok=True)

PENTESTGPT_URL = os.getenv("PENTESTGPT_URL", "http://pentestgpt:8080").rstrip("/")
PENTESTGPT_API_KEY = os.getenv("PENTESTGPT_API_KEY")
JOB_POLL_TIMEOUT = float(os.getenv("JOB_POLL_TIMEOUT", "30"))

class PentestOrchestrateRequest(BaseModel):
    pentest_prompt: str
    provider: str | None = None
    target: str | None = None
    filename: str | None = None
    force_save: bool = False
    run_timeout: int = 20

class PentestOrchestrateResponse(BaseModel):
    request_id: str
    playbook: str
    script_path: str | None
    job_id: str | None
    job_result: dict | None
    pentestgpt_response: dict | None
    warnings: list

def call_pentestgpt(prompt: str) -> dict:
    if not PENTESTGPT_URL:
        raise HTTPException(status_code=500, detail="PENTESTGPT_URL not configured")
    headers = {"Authorization": f"Bearer {PENTESTGPT_API_KEY}"} if PENTESTGPT_API_KEY else {}
    payload = {"prompt": prompt}
    try:
        # model local pode demorar na 1ª inferência
        resp = requests.post(
            f"{PENTESTGPT_URL}/generate_playbook",
            json=payload, headers=headers, timeout=120
        )
        resp.raise_for_status()
        return resp.json()
    except ReadTimeout:
        raise HTTPException(status_code=504, detail="pentestgpt timeout")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"pentestgpt error: {str(e)}")

def create_runner_playbook_for_script(script_path: str, run_timeout: int = 20) -> str:
    """
    Gera um playbook temporário que chama 'run_script' (params.script) apontando para script_path.
    """
    import yaml
    if not isinstance(script_path, str) or not script_path.strip():
        raise HTTPException(status_code=500, detail="invalid script_path for runner playbook")

    pid = uuid.uuid4().hex[:8]
    pb = {
        "playbook": f"auto-run-{pid}",
        "steps": [
            {
                "id": "run_generated",
                "type": "run_script",
                "params": { "script": script_path },
                "timeout": int(run_timeout),
            }
        ],
    }
    fname = TEMP_PLAYBOOK_DIR / f"auto_run_{pid}.yml"
    with open(fname, "w", encoding="utf-8") as fh:
        yaml.safe_dump(pb, fh, sort_keys=False)
    return str(fname)

def _safe_filename(name: str) -> str:
    base = "".join(c for c in name if c.isalnum() or c in ("_", "-", "."))
    return base if base.endswith(".py") else base + ".py"

@router.post("/ai/pentest-orchestrate", response_model=PentestOrchestrateResponse)
async def pentest_orchestrate(req: PentestOrchestrateRequest):
    """
    1) PentestGPT -> playbook (fallback se indisponível)
    2) Provider -> script (usando playbook+target como prompt)
    3) Sanitiza e salva script
    4) Cria playbook runner
    5) Executa job internamente (create_job_sync)
    6) Feedback ao PentestGPT (best-effort)
    """
    request_id = str(uuid.uuid4())

    # 1) PentestGPT com fallback
    try:
        pentest_resp = call_pentestgpt(req.pentest_prompt)
        playbook_text = pentest_resp.get("playbook") if isinstance(pentest_resp, dict) else None
    except HTTPException as he:
        pentest_resp = {"note": f"pentestgpt skipped: {he.detail}"}
        playbook_text = None

    if not playbook_text:
        playbook_text = "playbook: direct-script\nsteps:\n  - id: run-generated\n    type: run_script"

    # 2) script via provider
    provider = req.provider
    prompt = build_script_prompt(playbook_text, req.target)
    gen = generate_with_provider(prompt, model=None, provider=provider)
    script = gen.get("script", "") or ""
    try:
        insert_ai_request(
            request_id,
            playbook_text,
            provider or os.getenv("AI_PROVIDER", "unknown"),
            json.dumps({"gen_raw": gen.get("raw_response")}),
        )
    except Exception:
        pass

    # 3) sanitização e salvamento
    sanitized_script, ok, warnings = sanitize_and_validate_script(script)
    filename = _safe_filename(req.filename or f"generated_{request_id[:8]}.py")
    script_path = str(EXAMPLES_DIR / filename)

    if not ok and not req.force_save:
        return PentestOrchestrateResponse(
            request_id=request_id,
            playbook=playbook_text,
            script_path=None,
            job_id=None,
            job_result=None,
            pentestgpt_response=pentest_resp,
            warnings=warnings,
        )

    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(sanitized_script + ("\n" if not sanitized_script.endswith("\n") else ""))

    # 4) playbook runner
    runner_playbook_path = create_runner_playbook_for_script(script_path, run_timeout=req.run_timeout)

    # 5) executa job internamente
    try:
        job = create_job_sync(req.target or "", runner_playbook_path, timeout=int(JOB_POLL_TIMEOUT))
        job_id = job.get("job_id")
        job_result = job.get("result")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"job execution error: {str(e)}")

    # 6) feedback (best-effort)
    feedback_resp = {}
    try:
        headers = {"Authorization": f"Bearer {PENTESTGPT_API_KEY}"} if PENTESTGPT_API_KEY else {}
        payload = {"playbook": playbook_text, "result": job}
        r = requests.post(f"{PENTESTGPT_URL}/feedback", json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        feedback_resp = r.json()
    except Exception:
        feedback_resp = {"note": "feedback skipped or failed"}

    return PentestOrchestrateResponse(
        request_id=request_id,
        playbook=playbook_text,
        script_path=script_path,
        job_id=job_id,
        job_result=job_result,
        pentestgpt_response=feedback_resp,
        warnings=warnings,
    )
