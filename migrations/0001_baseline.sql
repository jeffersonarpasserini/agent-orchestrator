BEGIN;

CREATE SCHEMA IF NOT EXISTS orchestrator AUTHORIZATION agent_orchestrator;

CREATE TABLE IF NOT EXISTS orchestrator.schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO orchestrator.schema_migrations (version)
VALUES ('0001_baseline')
ON CONFLICT (version) DO NOTHING;

COMMIT;
