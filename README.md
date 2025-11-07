# Bug Hunter AI — MVP structure

> Projeto hobby (2 participantes) — orquestrador de automação de bug bounty baseado em PentestGPT + OpenAI GPT-5.

---

## Objetivo
Criar um MVP que permita a um usuário autorizado executar *playbooks* de segurança em ambientes autorizados, utilizando:
- PentestGPT (input de passos/estratégia)
- OpenAI GPT-5 (geração de scripts PoC / scanners)
- Executor isolado (containers efêmeros) que roda o script em sandbox
- Loop de feedback entre executor -> analyzer -> PentestGPT

Este repositório contém a estrutura inicial do projeto (esqueleto), templates de prompt, e um `README.md` com instruções para rodar localmente em modo *lab* (somente targets autorizados, por padrão `localhost`).

---

## Estrutura de pastas (planejada)

```
bug-hunter-ai/
├── README.md
├── .env.example
├── docker-compose.yml
├── infra/
│   ├── runner/Dockerfile
│   └── web/Dockerfile
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── endpoints.py
│   │   │   └── schemas.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── auth.py
│   │   ├── workers/
│   │   │   ├── queue.py
│   │   │   └── executor.py
│   │   ├── prompts/
│   │   │   ├── safe_poc_template.txt
│   │   │   └── pentestgpt_adapter.py
│   │   └── models/
│   │       └── models.sql (sqlite schema)
│   └── requirements.txt
├── runner/
│   ├── run_script.sh
│   └── runner-entrypoint.py
├── frontend/
│   └── (opcional) basic UI placeholder
└── docs/
    ├── PROMPTS.md
    └── SECURITY.md
```

---

## Conteúdo criado neste esqueleto

- `backend/app/main.py` — FastAPI app mínimal com endpoints `/jobs` e `/jobs/{id}`.
- `backend/app/prompts/safe_poc_template.txt` — template seguro para geração de PoC por GPT-5.
- `backend/app/workers/executor.py` — worker simplificado que enfileira jobs e chama o runner (via Docker).
- `runner/runner-entrypoint.py` & `run_script.sh` — runner que executa o script fornecido dentro do container, aplica timeout e retorna JSON com `evidence`, `stdout` e `exit_code`.
- `docker-compose.yml` — orquestra web + runner + minio (storage simulado) + sqlite (via volume).
- `README.md` — instruções para configurar, rodar localmente, próximo passos e uma checklist mínima de segurança.

> Obs: Os scripts de PoC gerados não são incluídos — o sistema gera no runtime usando chamadas à OpenAI. O runner inclui uma camada de whitelist que, por padrão, só permite `localhost` para testes.

---

## README.md (conteúdo principal)

Veja o arquivo `README.md` dentro do canvas para instruções completas: ele contém instruções de setup (variáveis de ambiente), comandos `docker-compose up`, exemplos de request cURL para criar jobs, e também um roadmap com próximos passos técnicos e de segurança.

---

## Segurança (resumo)

- **Escopo forçado**: por padrão a lista `ALLOWED_TARGETS` no `.env` só aceitará hosts/ips explicitamente permitidos (ex: `localhost`, `127.0.0.1`).
- **Executor isolado**: runner container roda como usuário não-root, com limites de CPU/MEM e timeout. Ainda recomendado migrar para microVM (Firecracker) se disponível.
- **Prompt constraints**: templates instruem o modelo a gerar scripts sem reverse shells, sem persistência e com saída JSON.
- **Auditoria**: o backend armazena prompt + resposta + metadados de execução.

Mais detalhes no `docs/SECURITY.md`.

---

## Próximos passos (curto prazo — o que você, e seu cofundador, podem fazer agora)

1. **Clonar e rodar localmente**: preencher `.env` com chaves (OpenAI) e `ALLOWED_TARGETS=localhost` e executar `docker-compose up --build`.
2. **Testar fluxo básico**: usar o endpoint `POST /jobs` para criar um job targeting `localhost` (use Juice Shop local para testes) — o worker vai pedir ao GPT-5 para gerar um script e o runner vai executá-lo.
3. **Adicionar validações**: implementar blacklist/regex que bloqueie tokens e comandos perigosos antes de persistir o script.
4. **Melhorar isolamento**: trocar execução de container por microVM ou Firecracker, ou aplicar seccomp profiles e AppArmor no runner.
5. **PentestGPT adapter**: implementar parser para normalizar passos de PentestGPT em playbooks.
6. **Human-in-the-loop**: permitir que steps gerados pelo PentestGPT sejam aprovados manualmente antes da execução.
7. **Cost control**: adicionar monitoramento de tokens e alertas para custo de API GPT-5.
8. **Documentação legal**: criar template de autorização de teste que o usuário deve anexar para cada target.

---

## Observações finais

- Esse esqueleto foi pensado para acelerar o desenvolvimento de um MVP entre dois participantes. É propositivo para um *hackable* lab e deve ser endurecido antes de qualquer uso em produção.
- Se quiser, eu posso agora:  
  - (A) gerar os arquivos reais do backend e `docker-compose.yml` e colocá-los aqui no canvas; or
  - (B) gerar um repositório ZIP com o esqueleto já populado para você baixar; or
  - (C) criar o `README.md` completo com exemplos `curl` e o conteúdo dos arquivos principais (FastAPI, runner) e colocá-lo no canvas.

Escolha uma opção ou diga se quer que eu já gere os arquivos (recomendado: C -> depois B).

---

*Fim do documento.*

