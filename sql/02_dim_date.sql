-- dim date table

DROP TABLE IF EXISTS warehouse.dim_date;

CREATE TABLE warehouse.dim_date AS
SELECT
    d::date AS date_day,
    EXTRACT(YEAR FROM d)::int AS year,
    EXTRACT(MONTH FROM d)::int AS month,
    TO_CHAR(d, 'YYYY-MM') AS year_month,
    EXTRACT(QUARTER FROM d)::int AS quarter,
    TO_CHAR(d, 'Month') AS month_name,
    (EXTRACT(DAY FROM d) = 1) AS is_month_start
FROM generate_series(
    DATE '2024-01-01',
    DATE '2026-12-31',
    INTERVAL '1 day'
) AS d;

ALTER TABLE warehouse.dim_date
    ADD PRIMARY KEY (date_day);


SELECT COUNT(*) FROM warehouse.dim_date;  -- expect 1096
SELECT MIN(date_day), MAX(date_day) FROM warehouse.dim_date;