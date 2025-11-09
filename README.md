# ZetaHunter — Pentest Automation com Ollama + PentestGPT Wrapper

## 🚀 Visão Geral

ZetaHunter é um orquestrador modular de testes de segurança automatizados.  
Ele integra modelos **LLMs locais (Ollama)** e **PentestGPT** para gerar, revisar e executar *playbooks* e *scripts Python* em ambientes controlados, retornando os resultados de forma auditável.

---

## 🧩 Componentes

### 1. `ollama`
Servidor local de IA generativa, compatível com API OpenAI.  
Permite rodar modelos como `llama3.2:3b` offline.

### 2. `pentestgpt`
Wrapper em FastAPI que encapsula a CLI do [PentestGPT](https://github.com/GreyDGL/PentestGPT)  
- Recebe `prompt` e retorna *playbooks YAML*.
- Faz fallback para o Ollama se o PentestGPT falhar.

### 3. `web`
Backend principal (`FastAPI`) responsável por:
- Chamar o PentestGPT e o provedor de IA (Ollama/OpenAI).
- Sanitizar e validar os scripts.
- Criar e executar *jobs* locais com o Runner.
- Retornar resultados e enviar *feedbacks*.

### 4. `runner`
Executa os playbooks gerados, interpretando instruções YAML (ex.: `http_get`, `run_script`).
Inclui controle de segurança com `ALLOWED_TARGETS` e `RUNNER_TIMEOUT`.

### 5. `minio`
Armazena resultados, artefatos e relatórios.

---

## ⚙️ Estrutura Docker Compose

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ./ollama:/root/.ollama
    restart: unless-stopped

  pentestgpt:
    build:
      context: ./infra/pentestgpt
    env_file: .env
    environment:
      OLLAMA_BASE_URL: http://ollama:11434
      OLLAMA_MODEL: llama3.2:3b
    ports:
      - "8080:8080"
    depends_on:
      - ollama

  web:
    build:
      context: .
      dockerfile: infra/web/Dockerfile
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./data:/app/data
    depends_on:
      - runner
      - pentestgpt
      - ollama

  runner:
    build:
      context: .
      dockerfile: infra/runner/Dockerfile
    env_file: .env
    volumes:
      - ./runner:/runner

  minio:
    image: minio/minio:latest
    command: server /data
    ports:
      - "9000:9000"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data

volumes:
  minio_data:
```

---

## 🧠 Variáveis de Ambiente (.env)

```bash
AI_PROVIDER=ollama
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
PENTESTGPT_URL=http://pentestgpt:8080
ALLOWED_TARGETS=localhost,127.0.0.1,juice-shop
RUNNER_TIMEOUT=30
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
DB_PATH=/app/data/app.db
```

---

## 🧪 Testando a Integração

### 1️⃣ Suba o ambiente
```bash
sudo docker compose up -d
```

### 2️⃣ Teste o PentestGPT isoladamente
```bash
curl -s -X POST "http://localhost:8080/generate_playbook"   -H "Content-Type: application/json"   -d '{"prompt":"Generate a YAML playbook to test XSS on http://juice-shop:3000"}' | jq
```

### 3️⃣ Teste o orquestrador completo
```bash
curl -s -X POST "http://localhost:8000/ai/pentest-orchestrate"   -H "Content-Type: application/json"   -d '{
    "pentest_prompt": "Produce a minimal YAML playbook to check reflected XSS on the target homepage.",
    "provider": "ollama",
    "target": "http://juice-shop:3000",
    "filename": "xss_from_pentestgpt.py",
    "force_save": false,
    "run_timeout": 20
  }' | jq
```

### 4️⃣ Verifique os resultados
```bash
sudo docker compose exec web sh -lc 'ls -l /app/examples && cat /app/examples/xss_from_pentestgpt.py'
sudo docker compose exec web sh -lc 'cat /app/playbooks/tmp/*.yml'
```

---

## 🧹 Sanitização e Segurança

Os scripts gerados passam por `backend/app/ai/sanitizer.py`, que:
- Remove cercas Markdown (```python ... ```).
- Extrai código Python de strings tipo `python -c "..."`.
- Bloqueia padrões perigosos (`os.system`, `socket`, `eval`, etc).
- Valida via `ast` e `compile()`.
- Exige que haja `import json` e apenas **um único `print(...)`** para saída JSON.

---

## 🧾 Logs e Depuração

```bash
sudo docker compose logs --no-color --tail=200 web
sudo docker compose logs --no-color --tail=200 pentestgpt
```

---

## ✅ Fluxo de Execução Simplificado

```
User Prompt
   ↓
PentestGPT (gera YAML)
   ↓
Provider (gera script Python)
   ↓
Sanitizer (limpa e valida)
   ↓
Runner (executa script no alvo permitido)
   ↓
Resultados (JSON + feedback ao PentestGPT)
```

---

## 📂 Estrutura Simplificada

```
backend/
├── app/
│   ├── api/endpoints.py
│   ├── ai/sanitizer.py
│   ├── core/jobs_api.py
│   ├── workers/executor.py
│   └── main.py
infra/
├── pentestgpt/Dockerfile
├── web/Dockerfile
├── runner/Dockerfile
```

---

## 🧱 Roadmap
- [x] Integração PentestGPT + Ollama  
- [x] Fallback automático e sanitização avançada  
- [ ] Frontend Web minimalista  
- [ ] Relatórios e métricas no MinIO  
- [ ] Cache de prompts/playbooks  

---

## ⚠️ Aviso Legal
O uso é destinado **exclusivamente para pesquisa e ambientes controlados**.  
O autor e colaboradores não se responsabilizam por qualquer uso indevido.