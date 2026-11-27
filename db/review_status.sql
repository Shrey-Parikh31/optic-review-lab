WITH latest AS (
    SELECT * FROM optic_snapshot WHERE repo = %(repo)s AND pr = %(pr)s AND origin = %(origin)s
    ORDER BY captured_at DESC, id DESC LIMIT 1
), run AS (
    SELECT r.* FROM optic_run r JOIN latest s ON r.snapshot_id = s.id AND r.head_sha = s.head_sha
    ORDER BY run_id DESC, attempt DESC LIMIT 1
), decisions AS (
    SELECT DISTINCT ON (lower(reviewer)) reviewer, state, reviewed_sha
    FROM optic_review r JOIN latest s ON r.snapshot_id = s.id
    WHERE eligible AND lower(reviewer) <> lower(s.pr_author)
      AND state IN ('APPROVED','CHANGES_REQUESTED','DISMISSED')
    ORDER BY lower(reviewer), submitted_at DESC, review_id DESC
)
SELECT s.head_sha, s.captured_at, s.origin, r.run_id, r.attempt, r.url AS run_url,
       ARRAY(SELECT reviewer FROM decisions WHERE state='APPROVED' AND reviewed_sha=s.head_sha
             ORDER BY reviewer) AS approvers,
       CASE WHEN s.head_sha <> %(sha)s THEN
              CASE WHEN EXISTS (SELECT FROM optic_snapshot h WHERE h.repo=s.repo AND h.pr=s.pr
                                AND h.origin=s.origin AND h.head_sha=%(sha)s)
                   THEN 'superseded' ELSE 'unknown' END
            WHEN EXISTS (SELECT FROM decisions WHERE state='CHANGES_REQUESTED') THEN 'changes_requested'
            WHEN r.status = 'completed' AND r.conclusion IS DISTINCT FROM 'success' THEN 'checks_failed'
            WHEN r.status IS DISTINCT FROM 'completed' THEN 'checks_pending'
            WHEN EXISTS (SELECT FROM decisions WHERE state='APPROVED' AND reviewed_sha=s.head_sha)
              THEN 'reviewed'
            ELSE 'review_pending' END AS decision
FROM latest s LEFT JOIN run r ON true
