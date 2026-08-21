-- dim line of business table

DROP TABLE IF EXISTS warehouse.dim_line_of_business;

CREATE TABLE warehouse.dim_line_of_business AS
SELECT * FROM staging.stg_lines_of_business;

ALTER TABLE warehouse.dim_line_of_business
    ADD PRIMARY KEY (lob_id);

-- dim members table

DROP TABLE IF EXISTS warehouse.dim_member;

CREATE TABLE warehouse.dim_member AS
SELECT * FROM staging.stg_members;

ALTER TABLE warehouse.dim_member
    ADD PRIMARY KEY (member_id);

-- dim provider table

DROP TABLE IF EXISTS warehouse.dim_provider;

CREATE TABLE warehouse.dim_provider AS
SELECT * FROM staging.stg_providers;

ALTER TABLE warehouse.dim_provider
    ADD PRIMARY KEY (provider_id);

-- dim service line

DROP TABLE IF EXISTS warehouse.dim_service_line;

CREATE TABLE warehouse.dim_service_line AS
SELECT * FROM staging.stg_service_lines;

ALTER TABLE warehouse.dim_service_line
    ADD PRIMARY KEY (service_line_id);

-- dim carc (denial / adjustment reason codes)

DROP TABLE IF EXISTS warehouse.dim_carc;

CREATE TABLE warehouse.dim_carc AS
SELECT * FROM staging.stg_carc_codes;

ALTER TABLE warehouse.dim_carc
    ADD PRIMARY KEY (carc_code);

-- dim cpt (optional)

DROP TABLE IF EXISTS warehouse.dim_cpt;

CREATE TABLE warehouse.dim_cpt AS
SELECT * FROM staging.stg_cpt_codes;

ALTER TABLE warehouse.dim_cpt
    ADD PRIMARY KEY (cpt_code);

-- dim icd10 (optional)

DROP TABLE IF EXISTS warehouse.dim_icd10;

CREATE TABLE warehouse.dim_icd10 AS
SELECT * FROM staging.stg_icd10_codes;

ALTER TABLE warehouse.dim_icd10
    ADD PRIMARY KEY (icd10_code);
