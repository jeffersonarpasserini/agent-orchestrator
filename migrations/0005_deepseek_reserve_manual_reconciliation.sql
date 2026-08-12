BEGIN;

CREATE TABLE IF NOT EXISTS orchestrator.deepseek_reserve_manual_reconciliations (
    grant_id text PRIMARY KEY
        REFERENCES orchestrator.deepseek_reserve_costs(grant_id),
    resolution text NOT NULL
        CHECK (resolution IN ('confirmed_charged', 'confirmed_not_charged')),
    resolved_by text NOT NULL,
    evidence_reference text NOT NULL,
    actual_cost_usd numeric(18, 12) NOT NULL CHECK (actual_cost_usd >= 0),
    prompt_cache_hit_tokens bigint NOT NULL CHECK (prompt_cache_hit_tokens >= 0),
    prompt_cache_miss_tokens bigint NOT NULL CHECK (prompt_cache_miss_tokens >= 0),
    completion_tokens bigint NOT NULL CHECK (completion_tokens >= 0),
    resolved_at timestamptz NOT NULL DEFAULT now(),
    CHECK (length(btrim(resolved_by)) > 0),
    CHECK (length(btrim(evidence_reference)) > 0),
    CHECK (
        resolution <> 'confirmed_not_charged'
        OR (
            actual_cost_usd = 0
            AND prompt_cache_hit_tokens = 0
            AND prompt_cache_miss_tokens = 0
            AND completion_tokens = 0
        )
    )
);

INSERT INTO orchestrator.schema_migrations (version)
VALUES ('0005_deepseek_reserve_manual_reconciliation')
ON CONFLICT (version) DO NOTHING;

COMMIT;
