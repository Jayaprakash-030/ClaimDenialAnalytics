-- fact_prior_auth: one row per PA record
DROP TABLE IF EXISTS warehouse.fact_prior_auth;

CREATE TABLE warehouse.fact_prior_auth AS
SELECT
    pa_id,
    event_id,
    member_id,
    provider_id,
    service_line_id,
    cpt_code,
    status,
    match_quality,
    decision_date,   -- NULL when never_requested
    auth_start,
    auth_end
FROM staging.stg_prior_auths;

ALTER TABLE warehouse.fact_prior_auth
    ADD PRIMARY KEY (pa_id);

ALTER TABLE warehouse.fact_prior_auth
    ADD CONSTRAINT fk_fact_pa_member
        FOREIGN KEY (member_id) REFERENCES warehouse.dim_member (member_id);

ALTER TABLE warehouse.fact_prior_auth
    ADD CONSTRAINT fk_fact_pa_provider
        FOREIGN KEY (provider_id) REFERENCES warehouse.dim_provider (provider_id);

ALTER TABLE warehouse.fact_prior_auth
    ADD CONSTRAINT fk_fact_pa_service_line
        FOREIGN KEY (service_line_id) REFERENCES warehouse.dim_service_line (service_line_id);

ALTER TABLE warehouse.fact_prior_auth
    ADD CONSTRAINT fk_fact_pa_cpt
        FOREIGN KEY (cpt_code) REFERENCES warehouse.dim_cpt (cpt_code);

-- nullable FK: never_requested rows have NULL decision_date
ALTER TABLE warehouse.fact_prior_auth
    ADD CONSTRAINT fk_fact_pa_decision_date
        FOREIGN KEY (decision_date) REFERENCES warehouse.dim_date (date_day);

SELECT COUNT(*) FROM warehouse.fact_prior_auth;
SELECT status, COUNT(*) FROM warehouse.fact_prior_auth GROUP BY status;