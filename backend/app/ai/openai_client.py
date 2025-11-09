# backend/app/ai/openai_client.py
import os
import json
import uuid
import traceback
from datetime import datetime
from app.core.db import insert_ai_request

# Try new OpenAI client (openai>=1.0)
try:
    from openai import OpenAI
    NEW_CLIENT_AVAILABLE = True
except Exception:
    OpenAI = None
    NEW_CLIENT_AVAILABLE = False

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
FORCE_MOCK = os.getenv("OPENAI_FORCE_MOCK", "false").lower() == "true"


def _has_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _safe_serializable(obj):
    try:
        json.dumps(obj)
        return obj
    except Exception:
        try:
            if hasattr(obj, "__dict__"):
                return {k: _safe_serializable(v) for k, v in obj.__dict__.items()}
        except Exception:
            pass
        return str(obj)


def generate_script(prompt: str, model: str | None = None, max_tokens: int = 1024) -> dict:
    """
    Gera um script Python via OpenAI (cliente novo quando disponível).
    Sempre retorna estrutura serializável:
    { id, model, script, raw_response }
    """
    model = model or DEFAULT_MODEL
    req_id = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat()

    # FORCE_MOCK or missing key/client -> return a safe mock script
    if FORCE_MOCK or (not _has_key()) or not NEW_CLIENT_AVAILABLE:
        script = (
            "# MOCK: forced or no client/key\n"
            "print('{\"evidence\": [], \"stdout\": \"mock\", \"exit_code\": 0}')\n"
        )
        raw = {"mock": True, "note": "FORCE_MOCK or missing config", "ts": ts}
        try:
            insert_ai_request(req_id, prompt, model, json.dumps(raw))
        except Exception:
            pass
        return {"id": req_id, "model": model, "script": script, "raw_response": raw}

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        messages = [
            {
                "role": "system",
                "content": (
                    "You are PoCGen: generate short, safe, single-file Python PoC scripts that print JSON to stdout. "
                    "Constraints: no reverse shells, no persistence, do not download remote binaries, do not open interactive shells, "
                    "do not run destructive commands. Output only the script."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2,
        )

        # Extrair conteúdo de maneira segura
        try:
            content = resp.choices[0].message.content
        except Exception:
            content = str(resp)

        if not isinstance(content, str):
            content = str(content)

        raw_serializable = _safe_serializable(
            {
                "id": getattr(resp, "id", None),
                "created": getattr(resp, "created", None),
                "model": getattr(resp, "model", None),
                "usage": getattr(resp, "usage", None),
            }
        )

        # Persistir só um resumo
        try:
            insert_ai_request(req_id, prompt, model, json.dumps({"ok": True, "ts": ts}))
        except Exception:
            pass

        return {"id": req_id, "model": model, "script": content, "raw_response": raw_serializable}

    except Exception as e:
        err = {"error": str(e), "trace": traceback.format_exc()[:2000], "ts": ts}
        try:
            insert_ai_request(req_id, prompt, model, json.dumps(err))
        except Exception:
            pass
        return {"id": req_id, "model": model, "script": "", "raw_response": _safe_serializable(err)}
