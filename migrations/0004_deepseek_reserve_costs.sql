BEGIN;

CREATE TABLE IF NOT EXISTS orchestrator.deepseek_reserve_costs (
    grant_id text PRIMARY KEY REFERENCES orchestrator.deepseek_reserve_grants(grant_id),
    task_id text NOT NULL,
    model text NOT NULL,
    price_snapshot text NOT NULL,
    estimated_max_cost_usd numeric(18, 12) NOT NULL CHECK (estimated_max_cost_usd > 0),
    actual_cost_usd numeric(18, 12) CHECK (actual_cost_usd >= 0),
    prompt_cache_hit_tokens bigint CHECK (prompt_cache_hit_tokens >= 0),
    prompt_cache_miss_tokens bigint CHECK (prompt_cache_miss_tokens >= 0),
    completion_tokens bigint CHECK (completion_tokens >= 0),
    status text NOT NULL CHECK (status IN ('committed', 'reconciled', 'outcome_unknown')),
    committed_at timestamptz NOT NULL DEFAULT now(),
    reconciled_at timestamptz,
    CHECK (length(btrim(task_id)) > 0),
    CHECK (length(btrim(model)) > 0),
    CHECK (length(btrim(price_snapshot)) > 0),
    CHECK ((status = 'reconciled') = (reconciled_at IS NOT NULL)),
    CHECK ((status = 'reconciled') = (actual_cost_usd IS NOT NULL))
);

INSERT INTO orchestrator.schema_migrations (version)
VALUES ('0004_deepseek_reserve_costs')
ON CONFLICT (version) DO NOTHING;

COMMIT;
