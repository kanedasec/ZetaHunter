-- simple sqlite schema placeholder
CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT, role TEXT);
CREATE TABLE targets (id TEXT PRIMARY KEY, name TEXT, domain TEXT, allowed_ips TEXT, owner_id TEXT);
CREATE TABLE jobs (id TEXT PRIMARY KEY, target_id TEXT, status TEXT, created_at TEXT, created_by TEXT);
CREATE TABLE job_steps (id TEXT PRIMARY KEY, job_id TEXT, step_type TEXT, prompt TEXT, model_response TEXT, status TEXT, output TEXT);
CREATE TABLE artifacts (id TEXT PRIMARY KEY, job_id TEXT, path TEXT, type TEXT);
CREATE TABLE audit_logs (id TEXT PRIMARY KEY, job_id TEXT, event TEXT, metadata TEXT);
