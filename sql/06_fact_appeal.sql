-- fact_appeal: one row per filed appeal
-- Enriches with member/provider/service_line from the denied claim
DROP TABLE IF EXISTS warehouse.fact_appeal;

CREATE TABLE warehouse.fact_appeal AS
SELECT
    a.appeal_id,
    a.claim_id,
    a.event_id,
    a.denial_carc,
    a.cause_category,
    a.filed_date,
    a.appeal_decision_date,
    a.outcome,
    c.member_id,
    c.provider_id,
    c.service_line_id,
    c.billed_amount,
    (a.filed_date - c.decision_date) AS days_to_file,
    (a.appeal_decision_date - a.filed_date) AS days_to_decide
FROM staging.stg_appeals AS a
JOIN warehouse.fact_claim AS c
    ON a.claim_id = c.claim_id;

ALTER TABLE warehouse.fact_appeal
    ADD PRIMARY KEY (appeal_id);

ALTER TABLE warehouse.fact_appeal
    ADD CONSTRAINT fk_fact_appeal_claim
        FOREIGN KEY (claim_id) REFERENCES warehouse.fact_claim (claim_id);

ALTER TABLE warehouse.fact_appeal
    ADD CONSTRAINT fk_fact_appeal_carc
        FOREIGN KEY (denial_carc) REFERENCES warehouse.dim_carc (carc_code);

ALTER TABLE warehouse.fact_appeal
    ADD CONSTRAINT fk_fact_appeal_member
        FOREIGN KEY (member_id) REFERENCES warehouse.dim_member (member_id);

ALTER TABLE warehouse.fact_appeal
    ADD CONSTRAINT fk_fact_appeal_provider
        FOREIGN KEY (provider_id) REFERENCES warehouse.dim_provider (provider_id);

ALTER TABLE warehouse.fact_appeal
    ADD CONSTRAINT fk_fact_appeal_service_line
        FOREIGN KEY (service_line_id) REFERENCES warehouse.dim_service_line (service_line_id);

-- primary date role for appeal trends (v1)
ALTER TABLE warehouse.fact_appeal
    ADD CONSTRAINT fk_fact_appeal_decision_date
        FOREIGN KEY (appeal_decision_date) REFERENCES warehouse.dim_date (date_day);

SELECT COUNT(*) FROM warehouse.fact_appeal;
SELECT outcome, COUNT(*) FROM warehouse.fact_appeal GROUP BY outcome;