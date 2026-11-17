-- Dimension rebuilt from the latest staging snapshot per product (SCD Type 1).
CREATE OR REPLACE TABLE `${PROJECT}.${DWH}.dim_product` AS
SELECT
  product_id,
  product_name,
  category,
  CAST(list_price_eur AS NUMERIC) AS list_price_eur,
  CURRENT_TIMESTAMP() AS updated_at
FROM (
  SELECT p.*, ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY _load_date DESC) AS rn
  FROM `${PROJECT}.${STG}.products` AS p
)
WHERE rn = 1;
