MERGE `${PROJECT}.${DWH}.dim_customer` AS t
USING (
  SELECT * EXCEPT (rn)
  FROM (
    SELECT c.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY _load_date DESC) AS rn
    FROM `${PROJECT}.${STG}.customers` AS c
    WHERE _load_date = @ds
  )
  WHERE rn = 1
) AS s
ON t.customer_id = s.customer_id
WHEN MATCHED THEN UPDATE SET
  customer_name = s.customer_name,
  segment       = s.segment,
  city          = s.city,
  region        = s.region,
  updated_at    = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (customer_id, customer_name, segment, city, region, updated_at)
  VALUES (s.customer_id, s.customer_name, s.segment, s.city, s.region, CURRENT_TIMESTAMP());
