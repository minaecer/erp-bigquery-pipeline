-- Idempotent daily rebuild of one partition: delete the day, insert the day.
DELETE FROM `${PROJECT}.${DWH}.fact_sales` WHERE order_date = @ds;

INSERT INTO `${PROJECT}.${DWH}.fact_sales`
SELECT
  l.order_id,
  l.line_no,
  o.order_date,
  o.customer_id,
  l.product_id,
  o.region,
  o.currency,
  o.status AS order_status,
  l.quantity,
  CAST(l.unit_price AS NUMERIC)   AS unit_price,
  CAST(l.discount_pct AS NUMERIC) AS discount_pct,
  CAST(ROUND(l.quantity * l.unit_price * (1 - l.discount_pct / 100), 2) AS NUMERIC) AS net_amount,
  CAST(ROUND(l.quantity * l.unit_price * (1 - l.discount_pct / 100)
             * IF(o.currency = 'TRY', 1.0, fx.rate_to_try), 2) AS NUMERIC)           AS net_amount_try,
  CURRENT_TIMESTAMP() AS loaded_at
FROM `${PROJECT}.${STG}.sales_lines` AS l
JOIN `${PROJECT}.${STG}.sales_orders` AS o
  ON o.order_id = l.order_id AND o._load_date = @ds
LEFT JOIN `${PROJECT}.${STG}.fx_rates` AS fx
  ON fx.rate_date = o.order_date AND fx.currency = o.currency AND fx._load_date = @ds
WHERE l._load_date = @ds;
