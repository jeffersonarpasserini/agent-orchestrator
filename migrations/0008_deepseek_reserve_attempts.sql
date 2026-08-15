BEGIN;

CREATE TABLE IF NOT EXISTS orchestrator.deepseek_reserve_attempts (
    attempt_id text PRIMARY KEY,
    task_id text NOT NULL,
    grant_id text NOT NULL UNIQUE
        REFERENCES orchestrator.deepseek_reserve_grants(grant_id),
    approved_by text NOT NULL,
    billing_route text NOT NULL
        CHECK (billing_route = 'deepseek_reserve'),
    primary_failure_reason text NOT NULL,
    requested_model text NOT NULL,
    effective_model text,
    primary_session_id text,
    reserve_session_id text,
    latency_ms bigint CHECK (latency_ms >= 0),
    status text NOT NULL
        CHECK (status IN (
            'reserve_running', 'completed', 'reserve_failed',
            'reserve_outcome_unknown', 'budget_blocked'
        )),
    prompt_cache_hit_tokens bigint
        CHECK (prompt_cache_hit_tokens >= 0),
    prompt_cache_miss_tokens bigint
        CHECK (prompt_cache_miss_tokens >= 0),
    completion_tokens bigint
        CHECK (completion_tokens >= 0),
    direct_cost_usd numeric(18, 12)
        CHECK (direct_cost_usd >= 0),
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    CHECK (length(btrim(attempt_id)) > 0),
    CHECK (length(btrim(task_id)) > 0),
    CHECK (length(btrim(approved_by)) > 0),
    CHECK (length(btrim(primary_failure_reason)) > 0),
    CHECK (length(btrim(requested_model)) > 0),
    CHECK ((status = 'reserve_running') = (finished_at IS NULL)),
    CHECK (
        status <> 'completed'
        OR (
            effective_model IS NOT NULL
            AND prompt_cache_hit_tokens IS NOT NULL
            AND prompt_cache_miss_tokens IS NOT NULL
            AND completion_tokens IS NOT NULL
            AND direct_cost_usd IS NOT NULL
        )
    )
);

CREATE INDEX IF NOT EXISTS deepseek_reserve_attempts_task_idx
    ON orchestrator.deepseek_reserve_attempts (task_id, status, started_at);

INSERT INTO orchestrator.schema_migrations (version)
VALUES ('0008_deepseek_reserve_attempts')
ON CONFLICT (version) DO NOTHING;

COMMIT;
