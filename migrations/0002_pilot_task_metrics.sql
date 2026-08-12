BEGIN;

CREATE TABLE IF NOT EXISTS orchestrator.pilot_task_metrics (
    task_id text PRIMARY KEY,
    task_class text NOT NULL,
    result text NOT NULL,
    profiles_models jsonb NOT NULL,
    attempts integer NOT NULL CHECK (attempts > 0),
    api_calls integer NOT NULL CHECK (api_calls >= 0),
    latency_seconds double precision NOT NULL CHECK (latency_seconds >= 0),
    cost_usd numeric(18, 12) NOT NULL CHECK (cost_usd >= 0),
    evidence jsonb NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO orchestrator.schema_migrations (version)
VALUES ('0002_pilot_task_metrics')
ON CONFLICT (version) DO NOTHING;

COMMIT;
