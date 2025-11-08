# Zeta Hunter — Quickstart (Lab)

**Aviso:** somente para uso em ambientes controlados e targets autorizados (ex.: Juice Shop local). Não utilize essa ferramenta contra alvos sem permissão explícita.

## Requisitos
- Docker & Docker Compose
- Python 3.11+ (apenas para desenvolvimento local se não usar containers)
- Conta e chave OpenAI (para geração de scripts) — opcional para testes (vai gerar falha se não configurar)

## 1) Copiar arquivos
Crie a árvore de diretórios conforme a estrutura do projeto ou extraia o ZIP fornecido.

## 2) Configurar variáveis de ambiente
Copie `.env.example` para `.env` e preencha:
- OPENAI_API_KEY (opcional para testes offline)
- ALLOWED_TARGETS=localhost

## 3) Rodar com Docker Compose
```bash
docker-compose up --build
```

Isso irá subir:
- backend (FastAPI)
- runner (container que executa os scripts em sandbox)
- minio (opcional, usado como armazenamento de artefatos)

## 4) Testar fluxo (exemplo cURL)
Crie um job — exemplo de payload (target deve estar em ALLOWED_TARGETS):

```bash
curl -X POST "http://localhost:8000/jobs"           -H "Content-Type: application/json"           -d '{ "target": "http://localhost:3000", "playbook": "basic-recon" }'
```

Resposta: `{"job_id": "..."}`. Consulte status:

```bash
curl http://localhost:8000/jobs/<job_id>
```

## 5) Próximos passos
- Implementar parser de resposta do GPT-5 e validações (blacklist/regex) no worker.
- Substituir runner por microVM (Firecracker) ou aplicar seccomp/AppArmor.
- Adicionar persistência (Postgres) e autenticação OIDC.
- Implementar PentestGPT adapter.

## Observações de segurança
- ALLOWED_TARGETS **obrigatório**. Nunca rode com ALLOWED_TARGETS aberto.
- Salve chaves da OpenAI apenas em Vault (aqui usamos `.env` apenas para desenvolvimento local).
- Revise scripts gerados pelo modelo antes de executar em ambientes sensíveis.
