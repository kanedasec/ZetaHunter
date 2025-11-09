# backend/app/core/jobs_api.py
import os
import json
import uuid
import subprocess
from datetime import datetime
from typing import Optional

# DB helpers são opcionais: use se existirem no seu projeto
try:
    from app.core.db import (
        insert_job,            # (job_id, target, playbook, status, created_at) -> None
        update_job_status,     # (job_id, status, finished_at) -> None
        update_job_result,     # (job_id, result_json) -> None
        get_job_by_id,         # (job_id) -> dict | None
        list_jobs,             # () -> list[dict]
    )
    _DB_AVAILABLE = True
except Exception:
    insert_job = update_job_status = update_job_result = get_job_by_id = list_jobs = None
    _DB_AVAILABLE = False

# Caminho do executor dentro do container 'web'
EXECUTOR_PATH = os.getenv("EXECUTOR_PATH", "/app/app/workers/executor.py")
DEFAULT_RUNNER_TIMEOUT = int(os.getenv("RUNNER_TIMEOUT", "30"))

def _safe_json_loads(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        return {"raw": (text or "")[:5000]}

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def create_job_sync(target: str, playbook_path: str, timeout: Optional[int] = None) -> dict:
    """
    Cria e executa um job sincronicamente, sem fazer chamada HTTP interna.
    1) registra job (se DB disponível)
    2) executa o executor por subprocess
    3) persiste resultado e status (se DB disponível)
    4) retorna dict com id/status/result
    """
    job_id = str(uuid.uuid4())
    created_at = _now_iso()
    status = "running"
    timeout = int(timeout or DEFAULT_RUNNER_TIMEOUT)

    # 1) Persiste criação (best-effort)
    if _DB_AVAILABLE and insert_job:
        try:
            insert_job(job_id, target, playbook_path, status, created_at)
        except Exception:
            pass

    # 2) Executa o executor
    cmd = ["python3", EXECUTOR_PATH, playbook_path, target]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        # executor.py deve imprimir um JSON com {playbook, target, steps: [...]}
        result = _safe_json_loads(stdout.strip()) if stdout.strip() else {}
        if proc.returncode == 0:
            status = "done"
        else:
            status = "error"
            result = {"error": "executor nonzero exit", "return_code": proc.returncode, "stderr": stderr[:2000], "result": result}
    except subprocess.TimeoutExpired as e:
        status = "error"
        result = {"error": "executor timeout", "timeout": timeout, "partial": _safe_json_loads((e.stdout or "") + (e.stderr or ""))}
    except Exception as e:
        status = "error"
        result = {"error": str(e)}

    finished_at = _now_iso()

    # 3) Persiste resultado e status (best-effort)
    if _DB_AVAILABLE and update_job_result:
        try:
            update_job_result(job_id, json.dumps(result))
        except Exception:
            pass
    if _DB_AVAILABLE and update_job_status:
        try:
            update_job_status(job_id, status, finished_at)
        except Exception:
            pass

    # 4) Retorno padrão
    return {
        "id": job_id,
        "job_id": job_id,
        "target": target,
        "playbook": playbook_path,
        "status": status,
        "created_at": created_at,
        "finished_at": finished_at,
        "result": result,
    }

# Auxiliares para endpoints /jobs
def get_job(job_id: str) -> Optional[dict]:
    if _DB_AVAILABLE and get_job_by_id:
        try:
            return get_job_by_id(job_id)
        except Exception:
            return None
    return None

def list_all_jobs() -> list:
    if _DB_AVAILABLE and list_jobs:
        try:
            return list_jobs()
        except Exception:
            return []
    return []
