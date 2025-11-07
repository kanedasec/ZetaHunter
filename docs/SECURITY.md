# Security notes

- ALLOWED_TARGETS must be strictly enforced.
- Runner must be hardened (seccomp, AppArmor, non-root).
- Store OpenAI keys in a secrets manager for production.
- Audit every model call with prompt + response + tokens.
