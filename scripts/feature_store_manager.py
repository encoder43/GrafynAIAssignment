"""
Feature Store Manager
Manages feature store operations using the new simplified schema structure
"""

import pandas as pd
from typing import List, Optional, Dict
from datetime import datetime
from snowflake_connection import SnowflakeConnection
import os


class FeatureStoreManager:
    """Manages Feature Store operations"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Feature Store Manager
        
        Args:
            config_path: Path to Snowflake config file
        """
        self.sf = SnowflakeConnection(config_path)
        self.sf.connect()
        self.db_name = self.sf.config.get('database', 'FEAT_DB')
        self.schema_name = self.sf.config.get('schema', 'FEAT_SCHEMA')
    
    def get_latest_features(self, entity_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Retrieve latest features for entities (customers)
        Returns features in wide format (pivoted from key-value store)
        
        Args:
            entity_ids: List of entity IDs (customer IDs). If None, returns all entities
            
        Returns:
            DataFrame with features in wide format (one row per entity)
        """
        if entity_ids:
            entity_list = "', '".join(entity_ids)
            query = f"""
            SELECT * 
            FROM {self.db_name}.{self.schema_name}.latest_features
            WHERE entity_id IN ('{entity_list}')
            """
        else:
            query = f"""
            SELECT * 
            FROM {self.db_name}.{self.schema_name}.latest_features
            WHERE entity_id IS NOT NULL
            """
        
        df = self.sf.execute_query(query)
        
        # Pivot from key-value format to wide format
        if len(df) > 0:
            df_wide = df.pivot_table(
                index='ENTITY_ID',
                columns='FEATURE_NAME',
                values='FEATURE_VALUE',
                aggfunc='first'
            ).reset_index()
            df_wide.columns.name = None
            df_wide = df_wide.rename(columns={'ENTITY_ID': 'entity_id'})
            return df_wide
        else:
            return pd.DataFrame()
    
    def get_features_for_training(self, 
                                   filters: Optional[Dict] = None,
                                   feature_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Retrieve features formatted for ML model training
        
        Args:
            filters: Dictionary of filter conditions (not used in key-value store, but kept for compatibility)
            feature_columns: List of specific feature columns to retrieve
            
        Returns:
            DataFrame with features ready for training
        """
        # Get all features
        df = self.get_latest_features()
        
        if len(df) == 0:
            return pd.DataFrame()
        
        # Select specific columns if requested
        if feature_columns:
            available_cols = [col for col in feature_columns if col in df.columns]
            if available_cols:
                df = df[['entity_id'] + available_cols]
        
        return df
    
    def get_point_in_time_features(self, 
                                    entity_id: str, 
                                    timestamp: datetime) -> pd.DataFrame:
        """
        Retrieve features at a specific point in time
        
        Args:
            entity_id: Entity ID (customer ID)
            timestamp: Point in time for feature retrieval
            
        Returns:
            DataFrame with historical features
        """
        query = f"""
        SELECT 
            entity_id,
            feature_name,
            feature_value,
            feature_ts
        FROM {self.db_name}.{self.schema_name}.feature_store
        WHERE entity_id = '{entity_id}'
            AND feature_ts <= '{timestamp.strftime('%Y-%m-%d %H:%M:%S')}'
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY entity_id, feature_name 
            ORDER BY feature_ts DESC
        ) = 1
        """
        
        df = self.sf.execute_query(query)
        
        # Pivot to wide format
        if len(df) > 0:
            df_wide = df.pivot_table(
                index='ENTITY_ID',
                columns='FEATURE_NAME',
                values='FEATURE_VALUE',
                aggfunc='first'
            ).reset_index()
            df_wide.columns.name = None
            df_wide = df_wide.rename(columns={'ENTITY_ID': 'entity_id'})
            return df_wide
        else:
            return pd.DataFrame()
    
    def refresh_features(self) -> int:
        """
        Refresh features in the feature store by recomputing from customer_agg_30d view
        
        Returns:
            Number of rows inserted
        """
        query = f"""
        INSERT INTO {self.db_name}.{self.schema_name}.feature_store 
            (feature_id, entity_id, feature_name, feature_value, created_at, feature_ts, source)
        SELECT
            CONCAT(customer_id, '_avg_tx_30d') as feature_id,
            customer_id AS entity_id,
            'avg_tx_amount_30d' AS feature_name,
            avg_tx_amount_30d AS feature_value,
            CURRENT_TIMESTAMP() AS created_at,
            CURRENT_TIMESTAMP() AS feature_ts,
            'sql_agg_30d' AS source
        FROM {self.db_name}.{self.schema_name}.customer_agg_30d
        WHERE customer_id NOT IN (
            SELECT entity_id 
            FROM {self.db_name}.{self.schema_name}.feature_store 
            WHERE feature_ts >= DATEADD('hour', -1, CURRENT_TIMESTAMP())
                AND feature_name = 'avg_tx_amount_30d'
        )
        """
        
        try:
            rows_inserted = self.sf.execute_update(query)
            print(f"Refreshed {rows_inserted} feature records")
            return rows_inserted
        except Exception as e:
            print(f"Error refreshing features: {e}")
            return 0
    
    def get_feature_statistics(self) -> pd.DataFrame:
        """
        Get statistics about features in the feature store
        
        Returns:
            DataFrame with feature statistics
        """
        query = f"""
        SELECT 
            COUNT(DISTINCT entity_id) AS total_entities,
            COUNT(*) AS total_features,
            COUNT(DISTINCT feature_name) AS unique_feature_names,
            AVG(feature_value) AS avg_feature_value,
            MIN(feature_value) AS min_feature_value,
            MAX(feature_value) AS max_feature_value,
            STDDEV(feature_value) AS std_feature_value
        FROM {self.db_name}.{self.schema_name}.latest_features
        WHERE feature_value IS NOT NULL
        """
        
        return self.sf.execute_query(query)
    
    def get_all_features_for_entity(self, entity_id: str) -> pd.DataFrame:
        """
        Get all features for a specific entity in key-value format
        
        Args:
            entity_id: Entity ID (customer ID)
            
        Returns:
            DataFrame with feature_name and feature_value columns
        """
        query = f"""
        SELECT 
            entity_id,
            feature_name,
            feature_value,
            feature_ts
        FROM {self.db_name}.{self.schema_name}.latest_features
        WHERE entity_id = '{entity_id}'
        ORDER BY feature_name
        """
        
        return self.sf.execute_query(query)
    
    def close(self):
        """Close connection"""
        self.sf.close()


def main():
    """Example usage"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'snowflake_config.json')
    
    try:
        fs_manager = FeatureStoreManager(config_path)
        
        # Get feature statistics
        print("Feature Store Statistics:")
        stats = fs_manager.get_feature_statistics()
        print(stats)
        print()
        
        # Get features for specific entities
        print("Features for sample entities:")
        features = fs_manager.get_latest_features(['cust01', 'cust02', 'cust03'])
        print(features)
        print()
        
        # Get all features for a specific entity
        print("All features for cust01:")
        entity_features = fs_manager.get_all_features_for_entity('cust01')
        print(entity_features)
        print()
        
        # Get features for training
        print("Features for training:")
        training_features = fs_manager.get_features_for_training()
        print(f"Retrieved {len(training_features)} records")
        print(training_features.head())
        
        fs_manager.close()
        
    except FileNotFoundError:
        print("Config file not found. Please create config/snowflake_config.json")
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure sql/snowflake_feature_engineering.sql ran successfully")
        print(f"2. Verify the view exists: SHOW VIEWS IN SCHEMA {fs_manager.db_name}.{fs_manager.schema_name};")
        print(f"3. Check if table has data: SELECT COUNT(*) FROM {fs_manager.db_name}.{fs_manager.schema_name}.feature_store;")


if __name__ == "__main__":
    main()
