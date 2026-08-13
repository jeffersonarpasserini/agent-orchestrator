BEGIN;

CREATE TABLE IF NOT EXISTS orchestrator.tasks (
    request_id text PRIMARY KEY,
    principal text NOT NULL,
    origin text NOT NULL,
    envelope_hash text NOT NULL CHECK (envelope_hash ~ '^[0-9a-f]{64}$'),
    envelope jsonb NOT NULL,
    state text NOT NULL CHECK (state IN (
        'received', 'rejected', 'planned', 'awaiting_approval', 'running',
        'cancelled', 'blocked', 'completed', 'resumed'
    )),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orchestrator.task_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id text NOT NULL REFERENCES orchestrator.tasks(request_id),
    principal text NOT NULL,
    event text NOT NULL CHECK (event IN (
        'received', 'rejected', 'planned', 'awaiting_approval', 'running',
        'cancelled', 'blocked', 'completed', 'resumed'
    )),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS task_events_request_id_created_at_idx
    ON orchestrator.task_events (request_id, created_at, id);

INSERT INTO orchestrator.schema_migrations (version)
VALUES ('0007_task_intake')
ON CONFLICT (version) DO NOTHING;

COMMIT;
