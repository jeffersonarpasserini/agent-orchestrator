BEGIN;

CREATE TABLE IF NOT EXISTS orchestrator.deepseek_reserve_grants (
    grant_id text PRIMARY KEY,
    task_id text NOT NULL,
    profile text NOT NULL,
    role text NOT NULL,
    primary_model text NOT NULL,
    reserve_model text NOT NULL,
    primary_failure_reason text NOT NULL,
    approved_by text NOT NULL,
    max_cost_usd numeric(18, 12) NOT NULL CHECK (max_cost_usd > 0),
    max_calls integer NOT NULL CHECK (max_calls = 1),
    expires_at timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'approved'
        CHECK (status IN ('approved', 'consumed', 'revoked')),
    created_at timestamptz NOT NULL DEFAULT now(),
    consumed_at timestamptz,
    revoked_at timestamptz,
    CHECK (length(btrim(grant_id)) > 0),
    CHECK (length(btrim(task_id)) > 0),
    CHECK (length(btrim(profile)) > 0),
    CHECK (length(btrim(approved_by)) > 0),
    CHECK ((status = 'consumed') = (consumed_at IS NOT NULL)),
    CHECK ((status = 'revoked') = (revoked_at IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS deepseek_reserve_grants_task_idx
    ON orchestrator.deepseek_reserve_grants (task_id, profile, status);

INSERT INTO orchestrator.schema_migrations (version)
VALUES ('0003_deepseek_reserve_grants')
ON CONFLICT (version) DO NOTHING;

COMMIT;
