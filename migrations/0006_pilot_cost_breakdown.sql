BEGIN;

ALTER TABLE orchestrator.pilot_task_metrics
    ADD COLUMN IF NOT EXISTS simulated_cost_usd numeric(18, 12),
    ADD COLUMN IF NOT EXISTS billed_cost_usd numeric(18, 12);

UPDATE orchestrator.pilot_task_metrics
   SET simulated_cost_usd = cost_usd,
       billed_cost_usd = cost_usd
 WHERE simulated_cost_usd IS NULL OR billed_cost_usd IS NULL;

ALTER TABLE orchestrator.pilot_task_metrics
    ALTER COLUMN simulated_cost_usd SET NOT NULL,
    ALTER COLUMN billed_cost_usd SET NOT NULL;

DO $$ BEGIN
    ALTER TABLE orchestrator.pilot_task_metrics
        ADD CONSTRAINT pilot_task_metrics_simulated_cost_nonnegative
            CHECK (simulated_cost_usd >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE orchestrator.pilot_task_metrics
        ADD CONSTRAINT pilot_task_metrics_billed_cost_nonnegative
            CHECK (billed_cost_usd >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE orchestrator.pilot_task_metrics
        ADD CONSTRAINT pilot_task_metrics_billed_not_above_simulated
            CHECK (billed_cost_usd <= simulated_cost_usd);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE orchestrator.pilot_task_metrics
        ADD CONSTRAINT pilot_task_metrics_legacy_cost_is_billed
            CHECK (cost_usd = billed_cost_usd);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

INSERT INTO orchestrator.schema_migrations (version)
VALUES ('0006_pilot_cost_breakdown')
ON CONFLICT (version) DO NOTHING;

COMMIT;
