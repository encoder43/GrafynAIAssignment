"""
Refresh Feature Data
Adds more sample transactions and refreshes features without dropping the database
"""

import os
from snowflake_connection import SnowflakeConnection

def refresh_data():
    """Add more transactions and refresh features"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'snowflake_config.json')
    sf = SnowflakeConnection(config_path)
    
    if not sf.connect():
        print("Failed to connect to Snowflake")
        return
    
    print("=" * 70)
    print("REFRESHING FEATURE DATA")
    print("=" * 70)
    
    try:
        # Switch to FEAT_DB.FEAT_SCHEMA
        sf.execute_update("USE DATABASE FEAT_DB")
        sf.execute_update("USE SCHEMA FEAT_SCHEMA")
        
        # Add more transactions
        print("\nAdding more sample transactions...")
        insert_query = """
        INSERT INTO FEAT_DB.FEAT_SCHEMA.customer_transactions 
        SELECT 
            'tx0007'::STRING, 'cust02'::STRING, '2025-10-15 16:00:00'::TIMESTAMP_NTZ, 150.00::FLOAT, 'web'::STRING, PARSE_JSON('{"promo":"Y","items":[{"sku":"F","qty":2}]}')::VARIANT
        UNION ALL SELECT 'tx0008'::STRING, 'cust03'::STRING, '2025-10-08 12:00:00'::TIMESTAMP_NTZ, 85.00::FLOAT, 'app'::STRING, PARSE_JSON('{"promo":"X","items":[{"sku":"G","qty":1}]}')::VARIANT
        UNION ALL SELECT 'tx0009'::STRING, 'cust04'::STRING, '2025-10-05 14:30:00'::TIMESTAMP_NTZ, 200.00::FLOAT, 'pos'::STRING, PARSE_JSON('{"promo":"Z","items":[{"sku":"H","qty":3}]}')::VARIANT
        UNION ALL SELECT 'tx0010'::STRING, 'cust04'::STRING, '2025-10-18 10:15:00'::TIMESTAMP_NTZ, 95.00::FLOAT, 'web'::STRING, PARSE_JSON('{"promo":null,"items":[{"sku":"I","qty":2}]}')::VARIANT
        UNION ALL SELECT 'tx0011'::STRING, 'cust05'::STRING, '2025-10-03 09:45:00'::TIMESTAMP_NTZ, 180.00::FLOAT, 'app'::STRING, PARSE_JSON('{"promo":"Y","items":[{"sku":"J","qty":1}]}')::VARIANT
        UNION ALL SELECT 'tx0012'::STRING, 'cust05'::STRING, '2025-10-20 15:20:00'::TIMESTAMP_NTZ, 60.00::FLOAT, 'web'::STRING, PARSE_JSON('{"promo":"X","items":[{"sku":"K","qty":4}]}')::VARIANT
        """
        
        rows = sf.execute_update(insert_query)
        print(f"✓ Added {rows} new transactions")
        
        # Refresh cleaned table
        print("\nRefreshing cleaned transactions table...")
        sf.execute_update("""
        CREATE OR REPLACE TABLE FEAT_DB.FEAT_SCHEMA.tx_cleaned AS
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
        FROM FEAT_DB.FEAT_SCHEMA.customer_transactions
        WHERE transaction_ts IS NOT NULL
        """)
        print("✓ Refreshed tx_cleaned table")
        
        # Refresh aggregation view
        print("\nRefreshing customer aggregation view...")
        sf.execute_update("""
        CREATE OR REPLACE VIEW FEAT_DB.FEAT_SCHEMA.customer_agg_30d AS
        SELECT
          customer_id,
          AVG(amount_filled) AS avg_tx_amount_30d,
          COUNT(*) AS tx_count_30d,
          SUM(high_value_flag) AS high_value_tx_count_30d
        FROM FEAT_DB.FEAT_SCHEMA.tx_cleaned
        WHERE transaction_ts >= DATEADD(day, -30, CURRENT_TIMESTAMP())
        GROUP BY customer_id
        """)
        print("✓ Refreshed customer_agg_30d view")
        
        # Refresh feature store
        print("\nRefreshing feature store...")
        sf.execute_update("""
        INSERT INTO FEAT_DB.FEAT_SCHEMA.feature_store 
            (feature_id, entity_id, feature_name, feature_value, created_at, feature_ts, source)
        SELECT
            CONCAT(customer_id, '_avg_tx_30d') as feature_id,
            customer_id AS entity_id,
            'avg_tx_amount_30d' AS feature_name,
            avg_tx_amount_30d AS feature_value,
            CURRENT_TIMESTAMP() AS created_at,
            CURRENT_TIMESTAMP() AS feature_ts,
            'sql_agg_30d' AS source
        FROM FEAT_DB.FEAT_SCHEMA.customer_agg_30d
        WHERE customer_id NOT IN (
            SELECT entity_id 
            FROM FEAT_DB.FEAT_SCHEMA.feature_store 
            WHERE feature_ts >= DATEADD('hour', -1, CURRENT_TIMESTAMP())
                AND feature_name = 'avg_tx_amount_30d'
        )
        """)
        print("✓ Refreshed feature store")
        
        # Check how many customers now have features
        print("\nChecking feature store status...")
        count_df = sf.execute_query("SELECT COUNT(DISTINCT entity_id) AS customer_count FROM FEAT_DB.FEAT_SCHEMA.latest_features")
        customer_count = count_df['CUSTOMER_COUNT'].iloc[0] if len(count_df) > 0 else 0
        print(f"✓ Feature store now has features for {customer_count} customers")
        
        print("\n" + "=" * 70)
        print("DATA REFRESH COMPLETE")
        print("=" * 70)
        print(f"\nYou now have {customer_count} customers with features.")
        print("You can now run: python scripts/ml_model_training.py")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sf.close()

if __name__ == "__main__":
    refresh_data()

