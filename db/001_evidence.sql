CREATE TABLE IF NOT EXISTS optic_snapshot (
    id text PRIMARY KEY,
    repo text NOT NULL,
    pr integer NOT NULL CHECK (pr > 0),
    head_sha text NOT NULL CHECK (head_sha ~ '^[0-9a-f]{40}$'),
    captured_at timestamptz NOT NULL,
    pr_author text NOT NULL,
    origin text NOT NULL CHECK (origin IN ('github', 'fixture'))
);
CREATE INDEX IF NOT EXISTS optic_latest ON optic_snapshot(repo, pr, captured_at DESC);

CREATE TABLE IF NOT EXISTS optic_run (
    snapshot_id text REFERENCES optic_snapshot ON DELETE CASCADE,
    run_id bigint NOT NULL,
    attempt integer NOT NULL CHECK (attempt > 0),
    head_sha text NOT NULL CHECK (head_sha ~ '^[0-9a-f]{40}$'),
    status text NOT NULL,
    conclusion text,
    url text NOT NULL,
    PRIMARY KEY (snapshot_id, run_id, attempt)
);

CREATE TABLE IF NOT EXISTS optic_review (
    snapshot_id text REFERENCES optic_snapshot ON DELETE CASCADE,
    review_id bigint NOT NULL,
    reviewer text NOT NULL,
    eligible boolean NOT NULL,
    state text NOT NULL,
    reviewed_sha text NOT NULL,
    submitted_at timestamptz NOT NULL,
    PRIMARY KEY (snapshot_id, review_id)
);

CREATE TABLE IF NOT EXISTS optic_case_result (
    snapshot_id text NOT NULL,
    run_id bigint NOT NULL,
    attempt integer NOT NULL,
    case_id text NOT NULL,
    verdict text NOT NULL CHECK (verdict IN ('pass','flag','error','timeout')),
    details jsonb NOT NULL,
    PRIMARY KEY (snapshot_id, run_id, attempt, case_id),
    FOREIGN KEY (snapshot_id, run_id, attempt) REFERENCES optic_run ON DELETE CASCADE
);
