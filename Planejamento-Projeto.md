# Zeta Hunter — MVP structure

> Orquestrador de automação de bug bounty baseado em PentestGPT + OpenAI GPT-5.

---

## Objetivo

Criar um MVP que permita a um usuário autorizado executar *playbooks* de segurança em ambientes autorizados, utilizando:

* PentestGPT (input de passos/estratégia)
* OpenAI GPT-5 (geração de scripts PoC / scanners)
* Executor isolado (containers efêmeros) que roda o script em sandbox
* Loop de feedback entre executor -> analyzer -> PentestGPT

Este repositório contém a estrutura inicial do projeto (esqueleto), templates de prompt, e um `README.md` com instruções para rodar localmente em modo *lab* (somente targets autorizados, por padrão `localhost`).

---

## Estrutura de pastas (proposta)

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
│   │   ├── models/
│   │   │   └── models.sql (sqlite schema)
│   │   └──platbooks/
│   │       └── basic-recon.yml
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

## 🧩 Linha do tempo do que já foi feito
# Etapa	Status	Descrição
1. Setup e estrutura inicial:	Criação da base FastAPI + Docker + executor independente (executor.py).
2. Execução local de playbooks:	Implementado basic-recon.yml com http_get e run_script (rodando juice_shop_test.py).
3. Orquestração de jobs (API):	Endpoint /jobs cria e executa playbook, retornando JSON.
4. Validação de targets seguros:	Campo ALLOWED_TARGETS no .env controla onde é permitido executar.
5. Path resolving container/host:	Corrigido para funcionar tanto local quanto dentro do container.
6. Docker Compose + Juice Shop:	Ambiente completo para testes (web, runner, minio, juice-shop).
7. Persistência mínima (SQLite):	Jobs gravados em data/app.db, listagem e consulta funcionando (/jobs, /jobs/{id}).
8. Retorno estruturado JSON:	Executor retorna resultados por step, com evidências e status.

## 🚧 Etapas que ainda faltam (início da fase de IA)
9. Integração com OpenAI (GPT-5):	Fazer o backend gerar scripts automaticamente com base em prompts e contexto do target (exemplo: "escreva um script Python que teste XSS básico").
10. PentestGPT adapter:	Criar um módulo que traduz a resposta do PentestGPT em playbooks YAML — ou seja, a IA descreve o plano de ataque, e o sistema transforma isso em steps executáveis.
11. Segurança da geração:	Adicionar filtros (blacklist de comandos, sandbox, timeout, etc.) antes de executar qualquer código gerado.
12. Auditoria de IA:	Registrar cada prompt enviado, resposta do modelo e script gerado no banco (para rastreabilidade).
13. Interface web (dashboard): Painel para visualizar jobs, logs, resultados e evidências.
14. Pipeline de automação completa:	Unir: input de target → PentestGPT cria plano → OpenAI gera scripts → executor executa → resultados retornam ao PentestGPT para decisão do próximo passo.

---
## Arquivos e diretórios — explicação detalhada
### README.md

Conteúdo: instruções rápidas de quickstart, comandos Docker Compose, segurança básica e próximos passos.

Uso: primeiro ponto de referência para rodar o projeto em laboratório.

### .env.example

Variáveis de ambiente de exemplo:

OPENAI_API_KEY — chave OpenAI (opcional no MVP local).

ALLOWED_TARGETS — lista comma-separated de hosts/aliases permitidos (ex: localhost,127.0.0.1,juice-shop). Obrigatório para segurança.

RUNNER_TIMEOUT — timeout padrão (segundos) para execução de scripts.

MINIO_* — placeholders para storage de artefatos (MinIO).

Deve ser copiado para .env e ajustado conforme ambiente local.

### .gitignore

Padrões para Python, IDEs, ambientes virtuais, arquivos temporários e secrets (inclui .env).

### docker-compose.yml

Orquestra três serviços principais:

web — imagem construída a partir de infra/web/Dockerfile que executa o FastAPI (backend).

runner — imagem construída a partir de infra/runner/Dockerfile (container de suporte / runner).

minio — armazenamento de objetos (opcional, usado como artifact store).

Observações: configurado para usar env_file: .env (recomendado) e para montar ./backend:/app e ./examples:/app/examples (quando for usado). Se montar ./backend:/app, atenção: conteúdo copiado pela imagem pode ser sobrescrito pelo volume, por isso também montamos examples para tornar scripts disponíveis.

### docker-compose.juice.yml

Arquivo simples para subir o OWASP Juice Shop.

### infra/web/Dockerfile

Imagem base python:3.11-slim.

Instala dependências listadas em backend/requirements.txt.

Copia backend/ para /app e examples/ para /app/examples.

Comando de inicialização: uvicorn app.main:app --host 0.0.0.0 --port 8000.

Nota: quando você montar ./backend:/app como volume, ele substitui o conteúdo copiado na imagem — por isso a cópia de examples e o volume ./examples:/app/examples são importantes para garantir que os scripts de exemplo fiquem disponíveis em ambiente de desenvolvimento.

### infra/runner/Dockerfile

Imagem base python:3.11-slim.

Instala utilitários (bash, jq, psmisc).

Copia a pasta runner/ para /runner.

Entrypoint: runner-entrypoint.py (mantém container up; foi pensado para testes).

### backend/requirements.txt

Dependências do backend:

fastapi, uvicorn[standard], httpx, pydantic, python-dotenv, pyyaml.

Use esse arquivo para criar ambientes ou imagens.

### backend/app/main.py

Inicializa FastAPI; inclui roteador (endpoints.py) e rota /health.

Ponto de entrada da aplicação.

### backend/app/api/endpoints.py

Implementa:

POST /jobs — cria e executa um job. No MVP atual o endpoint:

valida target contra ALLOWED_TARGETS,

resolve caminhos do executor/playbook tanto para execução local quanto para container,

executa executor.py via subprocess (blocking) e retorna job_id, status e result (JSON já do executor).

GET /jobs/{job_id} — consulta o job em memória (JOBS dict).

Observações:

Jobs são mantidos em memória (dentro do processo). Se reiniciar o container, o histórico se perde — persistência em SQLite é um próximo passo.

O endpoint foi escrito para ser tolerante com dois layouts (host vs container) para facilitar desenvolvimento.

### backend/app/workers/executor.py

Executor de playbooks (script Python):

Leitura do playbook YAML (usa pyyaml).

Suporta tipos de steps:

http_get — faz GET para target + path, coleta status, título HTML e um sample do conteúdo.

run_script — executa um script local (ex.: examples/juice_shop_test.py) e espera que o script imprima JSON com evidence, stdout e exit_code.

Resolve paths de forma robusta entre container/host.

Retorna JSON consolidado com playbook, target e lista steps com resultados.

### backend/playbooks/basic-recon.yml

Exemplo de playbook YAML utilizado no MVP.

Type suportados no MVP: http_get, run_script. Novos tipos (e.g., nmap, nuclei) podem ser mapeados no executor.

### backend/app/prompts/safe_poc_template.txt

Template de prompt seguro (texto). Planejado para ser usado quando a integração com OpenAI for adicionada.

Contém restrições: no reverse shells, timeout, output JSON etc.

Onde editar: backend/app/prompts/.

### backend/app/models/models.sql

Esquema SQL inicial sugerido (placeholder) com tabelas para users, targets, jobs, job_steps, artifacts, audit_logs.

Não há integração ativa — serve de guia para quando adicionarmos persistência (SQLite/Postgres).

### runner/run_script.sh

Script shell simples usado originalmente no MVP como wrapper que executa python3 <script> com timeout.

No fluxo atual o executor.py chama diretamente o script Python (saída JSON).

### runner/runner-entrypoint.py

Mantém o container runner em execução (apenas print('runner container up') e sleep loop). Está preparado para evoluir para um serviço que executa jobs via API/queue.

### examples/juice_shop_test.py

Script de teste safe para Juice Shop (lab):

Faz GET / e GET /rest/user/login.

Extrai título HTML através de um parser simples.

Produz JSON com evidence, stdout e exit_code.

Projetado para ser não destrutivo (apenas probes).

### docs/PROMPTS.md e docs/SECURITY.md

PROMPTS.md: orientações para criação de prompts seguros (quando integrar GPT).

SECURITY.md: notas com recomendações importantes (ALLOWED_TARGETS obrigatório, runner hardened, armazenamento seguro de chaves).

## Formato do playbook (explicação)

Arquivo YAML com:

name, description — metadados.

steps — lista ordenada de ações.

Cada step contem:

id — identificador.

type — http_get ou run_script (MVP).

params — parâmetros (ex: path para http_get, script para run_script).

O executor percorre steps na ordem e agrega result para cada step.

## Onde alterar/estender o que foi feito

### Adicionar novos tipos de step:

editar backend/app/workers/executor.py e acrescentar lógica para tipos (ex: nmap, nuclei, amass) — lembre de isolar execuções.

### Integrar OpenAI (script generation):

Template: backend/app/prompts/safe_poc_template.txt.

Chamadas ao OpenAI devem ser feitas no backend (novo módulo generator.py ou dentro do worker), armazenando prompts/outputs em audit logs e aplicando validações/blacklist antes de executar.

### PentestGPT adapter:

Arquivo sugerido: backend/app/prompts/pentestgpt_adapter.py (ainda não implementado). Ele deve transformar passos em playbooks YAML.

### Persistência:

Implementar SQLite/Postgres; migrar JOBS (dict mem) para DB usando models.sql como guia.

### Fila e workers:

Atualmente o POST /jobs chama o executor de forma síncrona. Para produção, introduzir Celery/RQ + workers para não bloquear o servidor.

### Hardening do runner:

Substituir execução por microVM (Firecracker) ou usar rootless containers + seccomp profile + AppArmor.

Restringir rede: permitir apenas conexões para hosts/ips do scope.

Monitorar syscalls via eBPF para detectar comportamento malicioso.

## O que foi implementado até aqui (resumo operacional)

FastAPI backend com endpoints /jobs e /jobs/{job_id}.

Executor (executor.py) capaz de rodar playbooks com http_get e run_script.

Playbook de exemplo basic-recon.yml.

Script de teste examples/juice_shop_test.py (safe).

Docker setup (web, runner e MinIO) + compose file para Juice Shop.

Permissões e path handling entre host e container resolvidos.

Template de prompt seguro para futura integração com OpenAI.

ZIP gerado com todo esqueleto pronto para compartilhar.

## Próximos passos recomendados (prioridade)

Persistência mínima (SQLite) para jobs/resultados.

Fila assíncrona (RQ/Celery) para não bloquear FastAPI.

Implementar/validar OpenAI generation + blacklist e auditoria.

Hardening do executor (seccomp/AppArmor ou microVM).

Adicionar CI (linters, SCA, Trivy) e testes automatizados.