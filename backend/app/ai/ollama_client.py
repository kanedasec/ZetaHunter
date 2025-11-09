# backend/app/ai/ollama_client.py
import os
import json
import uuid
import requests
from datetime import datetime
from app.core.db import insert_ai_request

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
FORCE_MOCK = os.getenv("OPENAI_FORCE_MOCK", "false").lower() == "true"  # reaproveitamos a flag

def _safe(obj):
    try:
        json.dumps(obj); return obj
    except Exception:
        return str(obj)

def generate_script_with_ollama(prompt: str, model: str | None = None, max_tokens: int = 1024) -> dict:
    """
    Usa Ollama /api/generate (não-stream) para gerar um script Python.
    Retorna { id, model, script, raw_response } com campos serializáveis.
    """
    req_id = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat()
    model = model or DEFAULT_OLLAMA_MODEL

    if FORCE_MOCK:
        script = (
            "# MOCK (FORCE_MOCK=true)\n"
            "print('{\"evidence\": [], \"stdout\": \"mock (ollama)\", \"exit_code\": 0}')\n"
        )
        raw = {"mock": True, "provider": "ollama", "ts": ts}
        try: insert_ai_request(req_id, prompt, model, json.dumps(raw))
        except Exception: pass
        return {"id": req_id, "model": model, "script": script, "raw_response": raw}

    # prompt com instruções de segurança
    sys_prompt = (
        "You are PoCGen: generate a short, safe, single-file Python PoC that prints JSON to stdout. "
        "Constraints: no reverse shells, no persistence, do not download remote binaries, "
        "do not open interactive shells, and do not run destructive commands. Output only the script."
    )
    composed = f"{sys_prompt}\n\nUSER:\n{prompt}\n\nOUTPUT:"

    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": composed,
                "stream": False,
                # tokens & temperature dependem do modelo; ollama ignora alguns campos
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("response", "")
        if not isinstance(content, str):
            content = str(content)

        raw_small = _safe({k: data.get(k) for k in ("model", "created_at", "done")})
        try: insert_ai_request(req_id, prompt, model, json.dumps({"ok": True, "ts": ts}))
        except Exception: pass

        return {"id": req_id, "model": model, "script": content, "raw_response": raw_small}
    except Exception as e:
        err = {"error": str(e), "provider": "ollama", "ts": ts}
        try: insert_ai_request(req_id, prompt, model, json.dumps(err))
        except Exception: pass
        # fallback mock p/ não quebrar fluxo
        script = (
            "# MOCK (ollama error)\n"
            "print('{\"evidence\": [], \"stdout\": \"mock (ollama error)\", \"exit_code\": 0}')\n"
        )
        return {"id": req_id, "model": model, "script": script, "raw_response": err}
