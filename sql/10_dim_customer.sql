-- Dimension rebuilt from the latest staging snapshot per customer (SCD Type 1).
CREATE OR REPLACE TABLE `${PROJECT}.${DWH}.dim_customer` AS
SELECT
  customer_id,
  customer_name,
  segment,
  city,
  region,
  CURRENT_TIMESTAMP() AS updated_at
FROM (
  SELECT c.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY _load_date DESC) AS rn
  FROM `${PROJECT}.${STG}.customers` AS c
)
WHERE rn = 1;
