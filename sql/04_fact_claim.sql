-- fact_claim: one row per adjudicated claim
DROP TABLE IF EXISTS warehouse.fact_claim;

CREATE TABLE warehouse.fact_claim AS
SELECT
    claim_id,
    event_id,
    member_id,
    provider_id,
    service_line_id,
    cpt_code,
    icd10_code,
    service_date,
    received_date,
    allowed_amount,
    billed_amount,
    pa_required,
    is_duplicate,
    status,
    NULLIF(denial_carc, '') AS denial_carc,  -- blank CSV → NULL (FK-safe)
    decision_date,
    contractual_adjustment,
    NULLIF(adjustment_carc, '') AS adjustment_carc,
    patient_responsibility,
    NULLIF(patient_carc, '') AS patient_carc,
    paid_amount,
    (decision_date - received_date) AS turnaround_days
FROM staging.stg_adjudicated_claims;

-- Primary key
ALTER TABLE warehouse.fact_claim
    ADD PRIMARY KEY (claim_id);

-- Foreign keys to dimensions
ALTER TABLE warehouse.fact_claim
    ADD CONSTRAINT fk_fact_claim_member
        FOREIGN KEY (member_id) REFERENCES warehouse.dim_member (member_id);

ALTER TABLE warehouse.fact_claim
    ADD CONSTRAINT fk_fact_claim_provider
        FOREIGN KEY (provider_id) REFERENCES warehouse.dim_provider (provider_id);

ALTER TABLE warehouse.fact_claim
    ADD CONSTRAINT fk_fact_claim_service_line
        FOREIGN KEY (service_line_id) REFERENCES warehouse.dim_service_line (service_line_id);

ALTER TABLE warehouse.fact_claim
    ADD CONSTRAINT fk_fact_claim_denial_carc
        FOREIGN KEY (denial_carc) REFERENCES warehouse.dim_carc (carc_code);

ALTER TABLE warehouse.fact_claim
    ADD CONSTRAINT fk_fact_claim_cpt
        FOREIGN KEY (cpt_code) REFERENCES warehouse.dim_cpt (cpt_code);

ALTER TABLE warehouse.fact_claim
    ADD CONSTRAINT fk_fact_claim_icd10
        FOREIGN KEY (icd10_code) REFERENCES warehouse.dim_icd10 (icd10_code);

-- Primary date role for trends (v1)
ALTER TABLE warehouse.fact_claim
    ADD CONSTRAINT fk_fact_claim_decision_date
        FOREIGN KEY (decision_date) REFERENCES warehouse.dim_date (date_day);

-- Quick checks
SELECT COUNT(*) FROM warehouse.fact_claim;
SELECT status, COUNT(*) FROM warehouse.fact_claim GROUP BY status;