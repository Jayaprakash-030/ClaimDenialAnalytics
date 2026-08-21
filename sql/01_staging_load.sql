-- Load data/raw CSVs into staging.* tables
--   psql -h localhost -p 5432 -U postgres -d claims_denial_analytics -f sql/01_staging_load.sql


\copy staging.stg_lines_of_business FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/lines_of_business.csv' CSV HEADER

\copy staging.stg_service_lines FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/service_lines.csv' CSV HEADER

\copy staging.stg_cpt_codes FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/cpt_codes.csv' CSV HEADER

\copy staging.stg_icd10_codes FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/icd10_codes.csv' CSV HEADER

\copy staging.stg_carc_codes FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/carc_codes.csv' CSV HEADER

\copy staging.stg_members FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/members.csv' CSV HEADER

\copy staging.stg_providers FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/providers.csv' CSV HEADER

\copy staging.stg_service_events FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/service_events.csv' CSV HEADER

\copy staging.stg_prior_auths FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/prior_auths.csv' CSV HEADER

\copy staging.stg_claims FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/claims.csv' CSV HEADER

\copy staging.stg_adjudicated_claims FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/adjudicated_claims.csv' CSV HEADER

\copy staging.stg_appeals FROM '/Users/jp/PortfolioProjects/ClaimDenialAnalytics/data/raw/appeals.csv' CSV HEADER
