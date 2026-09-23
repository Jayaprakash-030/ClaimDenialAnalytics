-- operations views

CREATE OR REPLACE VIEW warehouse.v_ops_claims_by_month AS
SELECT
    DATE_TRUNC('month', f.decision_date)::date AS decision_month,
    COUNT(*) AS claims_submitted,
    COUNT(*) FILTER (WHERE f.status = 'rejected') AS claims_rejected,
    COUNT(*) FILTER (WHERE f.status = 'paid') AS claims_paid,
    COUNT(*) FILTER (WHERE f.status = 'denied') AS claims_denied,
    COUNT(*) FILTER (WHERE f.status IN ('paid', 'denied')) AS claims_adjudicable,
    ROUND(
        COUNT(*) FILTER (WHERE f.status = 'denied')::numeric
        / NULLIF(COUNT(*) FILTER (WHERE f.status IN ('paid', 'denied')), 0),
        4
    ) AS denial_rate
FROM warehouse.fact_claim AS f
GROUP BY decision_month
ORDER BY decision_month;

CREATE OR REPLACE VIEW warehouse.v_ops_sla AS
SELECT
    DATE_TRUNC('month', f.decision_date)::date AS decision_month,
    lob.lob_id,
    lob.lob_name,
    COUNT(*) AS claims_adjudicable,
    ROUND(AVG(f.turnaround_days)::numeric, 2) AS avg_turnaround_days,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.turnaround_days)::numeric,
        2
    ) AS median_turnaround_days,
    ROUND(
        AVG(CASE WHEN f.turnaround_days <= lob.sla_days THEN 1.0 ELSE 0.0 END)::numeric,
        4
    ) AS sla_met_rate
FROM warehouse.fact_claim AS f
JOIN warehouse.dim_member AS m ON f.member_id = m.member_id
JOIN warehouse.dim_line_of_business AS lob ON m.lob_id = lob.lob_id
WHERE f.status IN ('paid', 'denied')
GROUP BY decision_month, lob.lob_id, lob.lob_name
ORDER BY decision_month, lob.lob_id;

--adjudication quality

-- 1. Denials by CARC / category

CREATE OR REPLACE VIEW warehouse.v_quality_denials_by_carc AS
SELECT
    f.denial_carc,
    d.cause_category,
    d.description,
    COUNT(*) AS denial_count,
    SUM(f.billed_amount) AS denied_billed_amount
FROM warehouse.fact_claim AS f
JOIN warehouse.dim_carc AS d
    ON f.denial_carc = d.carc_code
WHERE f.status = 'denied'
GROUP BY f.denial_carc, d.cause_category, d.description
ORDER BY denial_count DESC;

-- Overturn rate by CARC / category

CREATE OR REPLACE VIEW warehouse.v_quality_overturn_by_carc AS
SELECT
    a.denial_carc,
    d.cause_category,
    COUNT(*) AS appeals_decided,
    COUNT(*) FILTER (WHERE a.outcome = 'overturned') AS appeals_overturned,
    COUNT(*) FILTER (WHERE a.outcome = 'upheld') AS appeals_upheld,
    ROUND(
        COUNT(*) FILTER (WHERE a.outcome = 'overturned')::numeric
        / NULLIF(COUNT(*), 0),
        4
    ) AS overturn_rate
FROM warehouse.fact_appeal AS a
JOIN warehouse.dim_carc AS d
    ON a.denial_carc = d.carc_code
GROUP BY a.denial_carc, d.cause_category
ORDER BY overturn_rate DESC, appeals_decided DESC;

-- Denials never appealed

CREATE OR REPLACE VIEW warehouse.v_quality_denials_appeal_status AS
SELECT
    f.claim_id,
    f.denial_carc,
    d.cause_category,
    f.billed_amount,
    f.decision_date,
    CASE WHEN a.appeal_id IS NULL THEN 'never_appealed' ELSE 'appealed' END AS appeal_status,
    a.outcome
FROM warehouse.fact_claim AS f
JOIN warehouse.dim_carc AS d
    ON f.denial_carc = d.carc_code
LEFT JOIN warehouse.fact_appeal AS a
    ON f.claim_id = a.claim_id
WHERE f.status = 'denied';

CREATE OR REPLACE VIEW warehouse.v_quality_denials_appeal_summary AS
SELECT
    CASE WHEN a.appeal_id IS NULL THEN 'never_appealed' ELSE 'appealed' END AS appeal_status,
    COUNT(*) AS denial_count
FROM warehouse.fact_claim AS f
LEFT JOIN warehouse.fact_appeal AS a ON f.claim_id = a.claim_id
WHERE f.status = 'denied'
GROUP BY 1;

-- CO-197 split by PA match

CREATE OR REPLACE VIEW warehouse.v_quality_co197_by_pa AS
SELECT
    pa.status AS pa_status,
    pa.match_quality,
    COUNT(DISTINCT f.claim_id) AS denied_claims,
    COUNT(DISTINCT a.appeal_id) AS appeals,
    COUNT(DISTINCT a.appeal_id) FILTER (WHERE a.outcome = 'overturned') AS overturned,
    ROUND(
        COUNT(DISTINCT a.appeal_id) FILTER (WHERE a.outcome = 'overturned')::numeric
        / NULLIF(COUNT(DISTINCT a.appeal_id), 0),
        4
    ) AS overturn_rate
FROM warehouse.fact_claim AS f
LEFT JOIN warehouse.fact_appeal AS a
    ON f.claim_id = a.claim_id
LEFT JOIN warehouse.fact_prior_auth AS pa
    ON f.event_id = pa.event_id
WHERE f.status = 'denied'
  AND f.denial_carc = 'CO-197'
GROUP BY pa.status, pa.match_quality
ORDER BY pa.status, pa.match_quality;

-- Provider abrasion

CREATE OR REPLACE VIEW warehouse.v_provider_abrasion AS
WITH claim_stats AS (
    SELECT
        f.provider_id,
        COUNT(*) AS claims_submitted,
        COUNT(*) FILTER (WHERE f.status IN ('paid', 'denied')) AS claims_adjudicable,
        COUNT(*) FILTER (WHERE f.status = 'denied') AS claims_denied,
        ROUND(
            COUNT(*) FILTER (WHERE f.status = 'denied')::numeric
            / NULLIF(COUNT(*) FILTER (WHERE f.status IN ('paid', 'denied')), 0),
            4
        ) AS denial_rate
    FROM warehouse.fact_claim AS f
    GROUP BY f.provider_id
),
appeal_stats AS (
    SELECT
        a.provider_id,
        COUNT(*) AS appeals_filed,
        COUNT(*) FILTER (WHERE a.outcome = 'overturned') AS appeals_overturned,
        ROUND(
            COUNT(*) FILTER (WHERE a.outcome = 'overturned')::numeric
            / NULLIF(COUNT(*), 0),
            4
        ) AS overturn_rate
    FROM warehouse.fact_appeal AS a
    GROUP BY a.provider_id
)
SELECT
    p.provider_id,
    p.provider_name,
    p.provider_type,
    p.specialty,
    p.in_network,
    p.is_problem_provider,
    c.claims_submitted,
    c.claims_adjudicable,
    c.claims_denied,
    c.denial_rate,
    COALESCE(a.appeals_filed, 0) AS appeals_filed,
    ROUND(
        COALESCE(a.appeals_filed, 0)::numeric
        / NULLIF(c.claims_denied, 0),
        4
    ) AS appeal_rate,
    COALESCE(a.appeals_overturned, 0) AS appeals_overturned,
    a.overturn_rate,
    RANK() OVER (ORDER BY c.denial_rate DESC NULLS LAST) AS denial_rate_rank,
    NTILE(10) OVER (ORDER BY c.denial_rate DESC NULLS LAST) AS denial_rate_decile
FROM warehouse.dim_provider AS p
JOIN claim_stats AS c ON p.provider_id = c.provider_id
LEFT JOIN appeal_stats AS a ON p.provider_id = a.provider_id
ORDER BY c.denial_rate DESC NULLS LAST;


-- Integrity

-- 1.Duplicate claim share

CREATE OR REPLACE VIEW warehouse.v_integrity_duplicates AS
SELECT
    COUNT(*) AS claims_submitted,
    COUNT(*) FILTER (WHERE is_duplicate) AS duplicate_claims,
    ROUND(
        AVG(CASE WHEN is_duplicate THEN 1.0 ELSE 0.0 END)::numeric,
        4
    ) AS duplicate_share
FROM warehouse.fact_claim;

-- 2.Paid-row reconciliation

CREATE OR REPLACE VIEW warehouse.v_integrity_paid_reconciliation AS
SELECT
    claim_id,
    billed_amount,
    paid_amount,
    contractual_adjustment,
    patient_responsibility,
    ROUND(
        (paid_amount + contractual_adjustment + patient_responsibility - billed_amount)::numeric,
        2
    ) AS reconciliation_diff,
    ROUND(
        ABS(paid_amount + contractual_adjustment + patient_responsibility - billed_amount)::numeric,
        2
    ) AS reconciliation_abs_error
FROM warehouse.fact_claim
WHERE status = 'paid';

CREATE OR REPLACE VIEW warehouse.v_integrity_paid_reconciliation_summary AS
SELECT
    COUNT(*) AS paid_claims,
    ROUND(MAX(ABS(paid_amount + contractual_adjustment + patient_responsibility - billed_amount))::numeric, 4)
        AS max_abs_error,
    COUNT(*) FILTER (
        WHERE ABS(paid_amount + contractual_adjustment + patient_responsibility - billed_amount) >= 0.01
    ) AS rows_over_penny
FROM warehouse.fact_claim
WHERE status = 'paid';