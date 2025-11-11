-- snowflake_feature_engineering.sql
-- Run this in a Snowflake SQL Worksheet. Replace DATABASE/SCHEMA with your names if needed.

-- 0. Optional: choose a working DB/Schema
CREATE DATABASE IF NOT EXISTS FEAT_DB;
USE DATABASE FEAT_DB;
CREATE SCHEMA IF NOT EXISTS FEAT_SCHEMA;
USE SCHEMA FEAT_SCHEMA;

-- 1. Create small customer transactions table (mock data)
CREATE OR REPLACE TABLE customer_transactions (
  transaction_id   STRING,
  customer_id      STRING,
  transaction_ts   TIMESTAMP_NTZ,
  amount           FLOAT,
  channel          STRING,  -- e.g., web, app, pos
  metadata         VARIANT -- semi-structured JSON payload
);

-- 2. Insert sample rows (small dataset for demo)
-- Note: Using SELECT with PARSE_JSON instead of VALUES clause
-- Adding more transactions to ensure multiple customers have features for ML training
INSERT INTO customer_transactions 
SELECT 
    'tx0001'::STRING, 'cust01'::STRING, '2025-10-10 09:00:00'::TIMESTAMP_NTZ, 120.50::FLOAT, 'web'::STRING, PARSE_JSON('{"promo":"X","items":[{"sku":"A","qty":1}]}')::VARIANT
UNION ALL SELECT 'tx0002'::STRING, 'cust01'::STRING, '2025-10-12 11:30:00'::TIMESTAMP_NTZ, 40.00::FLOAT, 'app'::STRING, PARSE_JSON('{"promo":null,"items":[{"sku":"B","qty":2}]}')::VARIANT
UNION ALL SELECT 'tx0003'::STRING, 'cust02'::STRING, '2025-10-01 10:00:00'::TIMESTAMP_NTZ, 300.00::FLOAT, 'pos'::STRING, PARSE_JSON('{"promo":"Y","items":[{"sku":"C","qty":1},{"sku":"D","qty":2}]}')::VARIANT
UNION ALL SELECT 'tx0004'::STRING, 'cust01'::STRING, '2025-09-11 10:00:00'::TIMESTAMP_NTZ, 75.00::FLOAT, 'web'::STRING, PARSE_JSON('{"promo":"X","items":[{"sku":"A","qty":3}]}')::VARIANT
UNION ALL SELECT 'tx0005'::STRING, 'cust03'::STRING, '2025-09-30 08:00:00'::TIMESTAMP_NTZ, 15.00::FLOAT, 'app'::STRING, PARSE_JSON('{"promo":null,"items":[{"sku":"E","qty":1}]}')::VARIANT
UNION ALL SELECT 'tx0006'::STRING, 'cust02'::STRING, '2025-10-09 14:00:00'::TIMESTAMP_NTZ, 25.00::FLOAT, 'web'::STRING, PARSE_JSON('{"promo":"Z","items":[{"sku":"C","qty":1}]}')::VARIANT
UNION ALL SELECT 'tx0007'::STRING, 'cust02'::STRING, '2025-10-15 16:00:00'::TIMESTAMP_NTZ, 150.00::FLOAT, 'web'::STRING, PARSE_JSON('{"promo":"Y","items":[{"sku":"F","qty":2}]}')::VARIANT
UNION ALL SELECT 'tx0008'::STRING, 'cust03'::STRING, '2025-10-08 12:00:00'::TIMESTAMP_NTZ, 85.00::FLOAT, 'app'::STRING, PARSE_JSON('{"promo":"X","items":[{"sku":"G","qty":1}]}')::VARIANT
UNION ALL SELECT 'tx0009'::STRING, 'cust04'::STRING, '2025-10-05 14:30:00'::TIMESTAMP_NTZ, 200.00::FLOAT, 'pos'::STRING, PARSE_JSON('{"promo":"Z","items":[{"sku":"H","qty":3}]}')::VARIANT
UNION ALL SELECT 'tx0010'::STRING, 'cust04'::STRING, '2025-10-18 10:15:00'::TIMESTAMP_NTZ, 95.00::FLOAT, 'web'::STRING, PARSE_JSON('{"promo":null,"items":[{"sku":"I","qty":2}]}')::VARIANT
UNION ALL SELECT 'tx0011'::STRING, 'cust05'::STRING, '2025-10-03 09:45:00'::TIMESTAMP_NTZ, 180.00::FLOAT, 'app'::STRING, PARSE_JSON('{"promo":"Y","items":[{"sku":"J","qty":1}]}')::VARIANT
UNION ALL SELECT 'tx0012'::STRING, 'cust05'::STRING, '2025-10-20 15:20:00'::TIMESTAMP_NTZ, 60.00::FLOAT, 'web'::STRING, PARSE_JSON('{"promo":"X","items":[{"sku":"K","qty":4}]}')::VARIANT;

-- 3. Show how semi-structured VARIANT can be queried: extract promo codes
SELECT transaction_id, customer_id, amount, metadata:promo::STRING as promo_code
FROM customer_transactions
LIMIT 10;

-- 4. Basic cleaning / derived columns
-- Example: remove nulls by filtering, derive day_of_week, month, and flag large_tx
CREATE OR REPLACE TABLE tx_cleaned AS
SELECT
  transaction_id,
  customer_id,
  transaction_ts,
  amount,
  channel,
  metadata,
  COALESCE(metadata:promo::STRING, 'NO_PROMO') AS promo_code,
  DATE_TRUNC('day', transaction_ts)::DATE AS tx_date,
  DAYOFWEEK(transaction_ts) as day_of_week,
  CASE WHEN amount IS NULL THEN 0.0 ELSE amount END as amount_filled,
  CASE WHEN amount >= 100 THEN 1 ELSE 0 END as high_value_flag
FROM customer_transactions
WHERE transaction_ts IS NOT NULL;

-- 5. Example aggregation SQL: compute avg amount last 30 days per customer
-- For demo we use relative dates; in production use proper windows or timestamp filtering.
CREATE OR REPLACE VIEW customer_agg_30d AS
SELECT
  customer_id,
  AVG(amount_filled) AS avg_tx_amount_30d,
  COUNT(*) AS tx_count_30d,
  SUM(high_value_flag) AS high_value_tx_count_30d
FROM tx_cleaned
WHERE transaction_ts >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY customer_id;

SELECT * FROM customer_agg_30d;

-- 6. Create a "feature store" table (simulated) to store feature vectors
CREATE OR REPLACE TABLE feature_store (
  feature_id STRING,         -- e.g., cust01_avg_tx_30d
  entity_id  STRING,         -- entity, e.g., customer_id
  feature_name STRING,       -- e.g., avg_tx_amount_30d
  feature_value FLOAT,
  created_at TIMESTAMP_NTZ,
  feature_ts TIMESTAMP_NTZ,  -- timestamp for feature
  source      STRING
);

-- 7. Example: insert computed features into feature_store
-- Insert all features from customer_agg_30d (avg_tx_amount_30d, tx_count_30d, high_value_tx_count_30d)
INSERT INTO feature_store (feature_id, entity_id, feature_name, feature_value, created_at, feature_ts, source)
SELECT
  CONCAT(customer_id, '_avg_tx_30d') as feature_id,
  customer_id AS entity_id,
  'avg_tx_amount_30d' AS feature_name,
  avg_tx_amount_30d AS feature_value,
  CURRENT_TIMESTAMP() AS created_at,
  CURRENT_TIMESTAMP() AS feature_ts,
  'sql_agg_30d' AS source
FROM customer_agg_30d
UNION ALL
SELECT
  CONCAT(customer_id, '_tx_count_30d') as feature_id,
  customer_id AS entity_id,
  'tx_count_30d' AS feature_name,
  tx_count_30d::FLOAT AS feature_value,
  CURRENT_TIMESTAMP() AS created_at,
  CURRENT_TIMESTAMP() AS feature_ts,
  'sql_agg_30d' AS source
FROM customer_agg_30d
UNION ALL
SELECT
  CONCAT(customer_id, '_high_value_tx_count_30d') as feature_id,
  customer_id AS entity_id,
  'high_value_tx_count_30d' AS feature_name,
  high_value_tx_count_30d::FLOAT AS feature_value,
  CURRENT_TIMESTAMP() AS created_at,
  CURRENT_TIMESTAMP() AS feature_ts,
  'sql_agg_30d' AS source
FROM customer_agg_30d;

-- 8. Create a feature registry view to see latest features per entity
CREATE OR REPLACE VIEW latest_features AS
SELECT f.entity_id,
       f.feature_name,
       f.feature_value,
       f.feature_ts
FROM feature_store f
QUALIFY ROW_NUMBER() OVER (PARTITION BY f.entity_id, f.feature_name ORDER BY f.feature_ts DESC) = 1;

SELECT * FROM latest_features;

-- 9. Cleanup helper (optional)
-- DROP TABLE IF EXISTS customer_transactions, tx_cleaned, feature_store;

