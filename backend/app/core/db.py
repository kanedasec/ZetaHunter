import os, json, sqlite3
from pathlib import Path
from datetime import datetime

def _default_db_path() -> str:
    # Usa DB_PATH se existir (ex.: dentro do container: /app/data/app.db)
    env_path = os.getenv("DB_PATH")
    if env_path:
        return env_path
    # Fallback para execução no host (repo_root/data/app.db)
    here = Path(__file__).resolve()
    repo_root = here.parents[4] if len(here.parents) >= 5 else here.parents[0]
    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "app.db")

def get_conn():
    dbp = _default_db_path()
    os.makedirs(os.path.dirname(dbp), exist_ok=True)
    conn = sqlite3.connect(dbp)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        target TEXT NOT NULL,
        playbook TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        finished_at TEXT,
        result_json TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS job_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        step_id TEXT,
        step_type TEXT,
        result_json TEXT,
        FOREIGN KEY(job_id) REFERENCES jobs(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_requests (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    model TEXT,
    response TEXT,
    created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def insert_job(job_id: str, target: str, playbook: str, status: str, result: dict | None):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    finished = now if status in ("done","error") else None
    cur.execute(
        "INSERT OR REPLACE INTO jobs (id, target, playbook, status, created_at, finished_at, result_json) VALUES (?,?,?,?,?,?,?)",
        (job_id, target, playbook, status, now, finished, json.dumps(result) if result is not None else None)
    )
    conn.commit()
    conn.close()

def update_job(job_id: str, status: str, result: dict | None):
    conn = get_conn()
    cur = conn.cursor()
    finished = datetime.utcnow().isoformat() if status in ("done","error") else None
    cur.execute(
        "UPDATE jobs SET status = ?, finished_at = COALESCE(?, finished_at), result_json = ? WHERE id = ?",
        (status, finished, json.dumps(result) if result is not None else None, job_id)
    )
    conn.commit()
    conn.close()

def insert_job_steps(job_id: str, steps: list[dict]):
    conn = get_conn()
    cur = conn.cursor()
    for s in steps:
        cur.execute(
            "INSERT INTO job_steps (job_id, step_id, step_type, result_json) VALUES (?,?,?,?)",
            (job_id, s.get("id"), s.get("type"), json.dumps(s.get("result")))
        )
    conn.commit()
    conn.close()

def get_job(job_id: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        conn.close()
        return None
    job = {
        "id": row["id"],
        "target": row["target"],
        "playbook": row["playbook"],
        "status": row["status"],
        "created_at": row["created_at"],
        "finished_at": row["finished_at"],
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
    }
    steps = cur.execute(
        "SELECT step_id, step_type, result_json FROM job_steps WHERE job_id = ? ORDER BY id",
        (job_id,)
    ).fetchall()
    job["steps"] = [
        {"id": r["step_id"], "type": r["step_type"], "result": json.loads(r["result_json"]) if r["result_json"] else None}
        for r in steps
    ]
    conn.close()
    return job

def list_jobs(limit: int = 50, offset: int = 0) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, target, playbook, status, created_at, finished_at FROM jobs ORDER BY datetime(created_at) DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def insert_ai_request(req_id: str, prompt: str, model: str, response: str):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT OR REPLACE INTO ai_requests (id, prompt, model, response, created_at) VALUES (?,?,?,?,?)",
        (req_id, prompt, model, response, now)
    )
    conn.commit()
    conn.close()

def get_ai_request(req_id: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM ai_requests WHERE id = ?", (req_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row["id"], "prompt": row["prompt"], "model": row["model"], "response": row["response"], "created_at": row["created_at"]}
