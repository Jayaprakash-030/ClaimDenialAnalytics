CREATE TABLE IF NOT EXISTS staging.stg_lines_of_business (
    lob_id              TEXT PRIMARY KEY,
    lob_name            TEXT NOT NULL,
    member_share        NUMERIC(6, 4) NOT NULL,
    denial_rate_target  NUMERIC(6, 4) NOT NULL,
    sla_days            INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.stg_service_lines (
    service_line_id   TEXT PRIMARY KEY,
    service_line_name TEXT NOT NULL,
    volume_share      NUMERIC(6, 4) NOT NULL,
    allowed_min       NUMERIC(12, 2) NOT NULL,
    allowed_max       NUMERIC(12, 2) NOT NULL,
    pa_required       BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.stg_cpt_codes (
    cpt_code        TEXT PRIMARY KEY,
    description     TEXT NOT NULL,
    service_line_id TEXT NOT NULL,
    base_allowed    NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.stg_icd10_codes (
    icd10_code  TEXT PRIMARY KEY,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.stg_carc_codes (
    carc_code               TEXT PRIMARY KEY,
    description             TEXT NOT NULL,
    cause_category          TEXT NOT NULL,
    is_denial               BOOLEAN NOT NULL,
    expected_overturn_rate  NUMERIC(6, 4) NOT NULL,
    defensibility           TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Entities
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS staging.stg_members (
    member_id             TEXT PRIMARY KEY,
    first_name            TEXT NOT NULL,
    last_name             TEXT NOT NULL,
    sex                   TEXT NOT NULL,
    date_of_birth         DATE NOT NULL,
    lob_id                TEXT NOT NULL,
    enrollment_start      DATE NOT NULL,
    enrollment_end        DATE,              -- often blank → NULL
    has_enrollment_churn  BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.stg_providers (
    provider_id         TEXT PRIMARY KEY,
    provider_name       TEXT NOT NULL,
    provider_type       TEXT NOT NULL,
    specialty           TEXT NOT NULL,
    facility_name       TEXT NOT NULL,
    npi                 TEXT NOT NULL,
    in_network          BOOLEAN NOT NULL,
    billing_quality     NUMERIC(4, 3) NOT NULL CHECK (billing_quality BETWEEN 0 AND 1),
    is_problem_provider BOOLEAN NOT NULL
);

-- ---------------------------------------------------------------------------
-- Events / transactions
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS staging.stg_service_events (
    event_id        TEXT PRIMARY KEY,
    member_id       TEXT NOT NULL,
    provider_id     TEXT NOT NULL,
    service_line_id TEXT NOT NULL,
    service_date    DATE NOT NULL,           
    cpt_code        TEXT NOT NULL,
    icd10_code      TEXT NOT NULL,
    pa_required     BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.stg_prior_auths (
    pa_id           TEXT PRIMARY KEY,
    event_id        TEXT NOT NULL,
    member_id       TEXT NOT NULL,
    provider_id     TEXT NOT NULL,
    service_line_id TEXT NOT NULL,
    cpt_code        TEXT NOT NULL,
    status          TEXT NOT NULL,           -- approved | denied | never_requested
    match_quality   TEXT NOT NULL,           -- exact | unmatched | none
    decision_date   DATE,                   -- NULL when never_requested
    auth_start      DATE,                   -- NULL when denied / never_requested
    auth_end        DATE
);

-- Submitted bills (staging/lineage only — fact_claim uses adjudicated)
CREATE TABLE IF NOT EXISTS staging.stg_claims (
    claim_id        TEXT PRIMARY KEY,
    event_id        TEXT NOT NULL,
    member_id       TEXT NOT NULL,
    provider_id     TEXT NOT NULL,
    service_line_id TEXT NOT NULL,
    cpt_code        TEXT NOT NULL,
    icd10_code      TEXT NOT NULL,
    service_date    DATE NOT NULL,
    received_date   DATE NOT NULL,
    allowed_amount  NUMERIC(12, 2) NOT NULL,
    billed_amount   NUMERIC(12, 2) NOT NULL,
    pa_required     BOOLEAN NOT NULL,
    is_duplicate    BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.stg_adjudicated_claims (
    claim_id                  TEXT PRIMARY KEY,
    event_id                  TEXT NOT NULL,
    member_id                 TEXT NOT NULL,
    provider_id               TEXT NOT NULL,
    service_line_id           TEXT NOT NULL,
    cpt_code                  TEXT NOT NULL,
    icd10_code                TEXT NOT NULL,
    service_date              DATE NOT NULL,
    received_date             DATE NOT NULL,
    allowed_amount            NUMERIC(12, 2) NOT NULL,
    billed_amount             NUMERIC(12, 2) NOT NULL,
    pa_required               BOOLEAN NOT NULL,
    is_duplicate              BOOLEAN NOT NULL,
    status                    TEXT NOT NULL,  -- paid | denied | rejected
    denial_carc               TEXT,          -- NULL unless denied
    decision_date             DATE NOT NULL,
    contractual_adjustment    NUMERIC(12, 2),
    adjustment_carc           TEXT,
    patient_responsibility    NUMERIC(12, 2),
    patient_carc              TEXT,
    paid_amount               NUMERIC(12, 2) -- NULL when denied/rejected
);

CREATE TABLE IF NOT EXISTS staging.stg_appeals (
    appeal_id             TEXT PRIMARY KEY,
    claim_id              TEXT NOT NULL,
    event_id              TEXT NOT NULL,
    denial_carc           TEXT NOT NULL,
    cause_category        TEXT NOT NULL,
    filed_date            DATE NOT NULL,     
    appeal_decision_date  DATE NOT NULL,
    outcome               TEXT NOT NULL      -- overturned | upheld
);
