"""
Snowflake Connection Utility
Handles connection to Snowflake and basic operations
"""

import snowflake.connector
import json
import os
from typing import Dict, Optional
import pandas as pd


class SnowflakeConnection:
    """Manages Snowflake database connections"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Snowflake connection
        
        Args:
            config_path: Path to JSON config file. If None, uses environment variables
        """
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            # Use environment variables or default config
            self.config = {
                'account': os.getenv('SNOWFLAKE_ACCOUNT', ''),
                'user': os.getenv('SNOWFLAKE_USER', ''),
                'password': os.getenv('SNOWFLAKE_PASSWORD', ''),
                'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                'database': os.getenv('SNOWFLAKE_DATABASE', 'FEAT_DB'),
                'schema': os.getenv('SNOWFLAKE_SCHEMA', 'FEAT_SCHEMA')
            }
        
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish connection to Snowflake"""
        try:
            self.conn = snowflake.connector.connect(
                user=self.config['user'],
                password=self.config['password'],
                account=self.config['account'],
                warehouse=self.config['warehouse'],
                database=self.config['database'],
                schema=self.config['schema']
            )
            self.cursor = self.conn.cursor()
            print(f"Successfully connected to Snowflake")
            print(f"Database: {self.config['database']}")
            print(f"Schema: {self.config['schema']}")
            return True
        except Exception as e:
            print(f"Error connecting to Snowflake: {e}")
            return False
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame
        
        Args:
            query: SQL query string
            
        Returns:
            pandas DataFrame with query results
        """
        if not self.conn:
            raise Exception("Not connected to Snowflake. Call connect() first.")
        
        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            df = pd.DataFrame(results, columns=columns)
            return df
        except Exception as e:
            print(f"Error executing query: {e}")
            raise
    
    def execute_update(self, query: str) -> int:
        """
        Execute UPDATE/INSERT/DELETE query
        
        Args:
            query: SQL query string
            
        Returns:
            Number of rows affected
        """
        if not self.conn:
            raise Exception("Not connected to Snowflake. Call connect() first.")
        
        try:
            self.cursor.execute(query)
            return self.cursor.rowcount
        except Exception as e:
            print(f"Error executing update: {e}")
            raise
    
    def close(self):
        """Close connection to Snowflake"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("Connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def main():
    """Example usage"""
    # Example: Connect and run a simple query
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'snowflake_config.json')
    
    try:
        with SnowflakeConnection(config_path) as sf:
            # Test query
            query = "SELECT CURRENT_VERSION() AS snowflake_version"
            df = sf.execute_query(query)
            print("\nSnowflake Version:")
            print(df)
            
            # Check if tables exist
            query = "SHOW TABLES IN SCHEMA FEAT_DB.FEAT_SCHEMA"
            df = sf.execute_query(query)
            print("\nTables in FEAT_SCHEMA:")
            print(df)
            
    except FileNotFoundError:
        print("Config file not found. Please create config/snowflake_config.json")
        print("Or set environment variables: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, etc.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
