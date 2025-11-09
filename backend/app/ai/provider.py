# backend/app/ai/provider.py
import os
from app.ai.openai_client import generate_script as generate_with_openai
from app.ai.ollama_client import generate_script_with_ollama

AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()

def generate_script(prompt: str, model: str | None = None, max_tokens: int = 1024, provider: str | None = None) -> dict:
    """
    Escolhe o provedor: 'openai' | 'ollama' | 'mock'
    """
    prov = (provider or AI_PROVIDER).lower()
    if prov == "ollama":
        return generate_script_with_ollama(prompt, model=model, max_tokens=max_tokens)
    if prov == "mock":
        # força caminho de mock via openai_client (ele já respeita FORCE_MOCK)
        from app.ai.openai_client import DEFAULT_MODEL
        return {"id": "mock", "model": model or DEFAULT_MODEL, "script":
                "# MOCK\nprint('{\"evidence\": [], \"stdout\": \"mock (provider)\", \"exit_code\": 0}')\n",
                "raw_response": {"mock": True, "provider": "mock"}}
    # default: openai
    return generate_with_openai(prompt, model=model, max_tokens=max_tokens)

def build_script_prompt(playbook_text: str, target_hint: str | None) -> str:
    target_line = f"Target: {target_hint}" if target_hint else "Target: http://localhost:3000"
    return f"""
You are PoCGen. Generate a SAFE, single-file Python 3.11+ script that:

- Reads the target base URL from sys.argv[1] (default to http://localhost:3000 if missing).
- Uses only the 'requests' library.
- Sends only HTTP requests to the same host (no external IPs/domínios).
- Tries a minimal reflected XSS probe on the homepage ('/').
- Prints EXACTLY ONE JSON object to stdout with keys:
  - "evidence": list (e.g., matched URLs or signals),
  - "stdout": short textual summary,
  - "exit_code": 0 for no finding / 1 if something suspicious found.
- No file writes, no subprocess/shell, no interactive input, no imports beyond stdlib + requests.
- Keep under 120 lines. No comments or explanations in output — output ONLY the script.

Context (playbook draft):
---
{playbook_text}
---
{target_line}
""".strip()
