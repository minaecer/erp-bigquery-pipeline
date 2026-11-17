-- Idempotent DDL. ${PROJECT}/${STG}/${DWH} are substituted by the pipeline.
-- No DML anywhere in this project, so it also runs in the BigQuery sandbox (no billing).

CREATE TABLE IF NOT EXISTS `${PROJECT}.${DWH}.dim_date` AS
SELECT
  d                                         AS date_key,
  EXTRACT(YEAR FROM d)                      AS year,
  EXTRACT(QUARTER FROM d)                   AS quarter,
  EXTRACT(MONTH FROM d)                     AS month,
  FORMAT_DATE('%B', d)                      AS month_name,
  EXTRACT(ISOWEEK FROM d)                   AS iso_week,
  FORMAT_DATE('%A', d)                      AS day_name,
  EXTRACT(DAYOFWEEK FROM d) IN (1, 7)       AS is_weekend
FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01', '2030-12-31')) AS d;

-- Fact grain: one row per sales order line. Partitioned by day, clustered for typical BI filters.
-- Each day's partition is overwritten by the pipeline (see 20_fact_sales.sql).
CREATE TABLE IF NOT EXISTS `${PROJECT}.${DWH}.fact_sales` (
  order_id       STRING,
  line_no        INT64,
  order_date     DATE,
  customer_id    STRING,
  product_id     STRING,
  region         STRING,
  currency       STRING,
  order_status   STRING,
  quantity       INT64,
  unit_price     NUMERIC,
  discount_pct   NUMERIC,
  net_amount     NUMERIC,   -- in order currency
  net_amount_try NUMERIC,   -- converted with that day's EUR/TRY rate
  loaded_at      TIMESTAMP
)
PARTITION BY order_date
CLUSTER BY region, product_id;
