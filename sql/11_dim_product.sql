MERGE `${PROJECT}.${DWH}.dim_product` AS t
USING (
  SELECT * EXCEPT (rn)
  FROM (
    SELECT p.*, ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY _load_date DESC) AS rn
    FROM `${PROJECT}.${STG}.products` AS p
    WHERE _load_date = @ds
  )
  WHERE rn = 1
) AS s
ON t.product_id = s.product_id
WHEN MATCHED THEN UPDATE SET
  product_name   = s.product_name,
  category       = s.category,
  list_price_eur = CAST(s.list_price_eur AS NUMERIC),
  updated_at     = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (product_id, product_name, category, list_price_eur, updated_at)
  VALUES (s.product_id, s.product_name, s.category, CAST(s.list_price_eur AS NUMERIC), CURRENT_TIMESTAMP());
