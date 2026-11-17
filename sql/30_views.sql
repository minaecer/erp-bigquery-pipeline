-- Reporting view for Looker Studio / Power BI. Cancelled orders are excluded from sales.
CREATE OR REPLACE VIEW `${PROJECT}.${DWH}.vw_daily_sales` AS
SELECT
  f.order_date,
  d.year,
  d.month,
  d.month_name,
  f.region,
  c.segment,
  p.category,
  COUNT(DISTINCT f.order_id) AS orders,
  SUM(f.quantity)            AS units,
  SUM(f.net_amount_try)      AS net_sales_try
FROM `${PROJECT}.${DWH}.fact_sales` AS f
JOIN `${PROJECT}.${DWH}.dim_date` AS d ON d.date_key = f.order_date
LEFT JOIN `${PROJECT}.${DWH}.dim_customer` AS c ON c.customer_id = f.customer_id
LEFT JOIN `${PROJECT}.${DWH}.dim_product` AS p ON p.product_id = f.product_id
WHERE f.order_status != 'Cancelled'
GROUP BY 1, 2, 3, 4, 5, 6, 7;
