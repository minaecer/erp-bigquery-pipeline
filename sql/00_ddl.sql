-- Warehouse tables (idempotent). ${PROJECT}/${STG}/${DWH} are substituted by the pipeline.

CREATE TABLE IF NOT EXISTS `${PROJECT}.${DWH}.dim_customer` (
  customer_id   STRING NOT NULL,
  customer_name STRING,
  segment       STRING,
  city          STRING,
  region        STRING,
  updated_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${PROJECT}.${DWH}.dim_product` (
  product_id     STRING NOT NULL,
  product_name   STRING,
  category       STRING,
  list_price_eur NUMERIC,
  updated_at     TIMESTAMP
);

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
CREATE TABLE IF NOT EXISTS `${PROJECT}.${DWH}.fact_sales` (
  order_id       STRING NOT NULL,
  line_no        INT64  NOT NULL,
  order_date     DATE   NOT NULL,
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
