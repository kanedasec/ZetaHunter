# Zeta Hunter — Quickstart (Lab)


**Aviso:** somente para uso em ambientes controlados e targets autorizados (ex.: Juice Shop local). Não utilize essa ferramenta contra alvos sem permissão explícita.


## Requisitos
- Docker & Docker Compose
- Python 3.11+ (apenas para desenvolvimento local se não usar containers)
- Conta e chave OpenAI (para geração de scripts) — opcional para testes (vai gerar falha se não configurar)


## 1) Copiar arquivos
Crie a árvore de diretórios conforme a estrutura acima e salve os arquivos fornecidos neste documento.


## 2) Configurar variáveis de ambiente
Copie `.env.example` para `.env` e preencha:
- OPENAI_API_KEY (opcional para testes offline)
- ALLOWED_TARGETS=localhost


## 3) Rodar com Docker Compose
```bash
docker-compose up --build