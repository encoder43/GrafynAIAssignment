"""
Automated Feature Store Setup
This script automatically executes the SQL setup script to create the feature store
"""

import os
import sys
import pandas as pd
from snowflake_connection import SnowflakeConnection
from typing import Optional


class FeatureStoreSetup:
    """Automates the feature store setup process"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Feature Store Setup
        
        Args:
            config_path: Path to Snowflake config file
        """
        self.sf = SnowflakeConnection(config_path)
        self.sql_file_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'sql', 
            'snowflake_feature_engineering.sql'
        )
    
    def read_sql_file(self) -> str:
        """Read the SQL file content"""
        if not os.path.exists(self.sql_file_path):
            raise FileNotFoundError(
                f"SQL file not found: {self.sql_file_path}\n"
                f"Please ensure sql/snowflake_feature_engineering.sql exists"
            )
        
        with open(self.sql_file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def split_sql_statements(self, sql_content: str) -> list:
        """
        Split SQL content into individual statements
        Handles comments and multiple statements more reliably
        """
        statements = []
        current_statement = []
        in_block_comment = False
        
        # Remove block comments first
        lines = []
        for line in sql_content.split('\n'):
            # Handle block comments
            if '/*' in line:
                if '*/' in line:
                    # Comment on same line, remove it
                    start = line.find('/*')
                    end = line.find('*/') + 2
                    line = line[:start] + line[end:]
                else:
                    # Start of block comment
                    in_block_comment = True
                    line = line[:line.find('/*')]
            
            if in_block_comment:
                if '*/' in line:
                    # End of block comment
                    in_block_comment = False
                    line = line[line.find('*/') + 2:]
                else:
                    # Still in comment, skip line
                    continue
            
            lines.append(line)
        
        # Now process lines for statements
        for line in lines:
            # Remove inline comments (--)
            if '--' in line:
                comment_pos = line.find('--')
                # Check if it's not inside a string
                before_comment = line[:comment_pos]
                if before_comment.count("'") % 2 == 0:  # Even number of quotes = not in string
                    line = before_comment
            
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Add line to current statement
            current_statement.append(stripped)
            
            # Check if line ends with semicolon (end of statement)
            if stripped.endswith(';'):
                # Join the statement
                statement = ' '.join(current_statement)
                # Remove trailing semicolon for cleaner execution
                statement = statement.rstrip(';').strip()
                if statement:
                    statements.append(statement)
                current_statement = []
        
        # Add any remaining statement (in case no semicolon at end)
        if current_statement:
            statement = ' '.join(current_statement).strip()
            if statement and not statement.endswith(';'):
                statements.append(statement)
        
        return statements
    
    def execute_setup(self, drop_existing: bool = False) -> dict:
        """
        Execute the SQL setup script
        
        Args:
            drop_existing: If True, drops existing database/schema before creating
            
        Returns:
            Dictionary with execution results
        """
        print("=" * 70)
        print("FEATURE STORE AUTOMATED SETUP")
        print("=" * 70)
        print()
        
        # Connect to Snowflake
        print("Step 1: Connecting to Snowflake...")
        if not self.sf.connect():
            raise Exception("Failed to connect to Snowflake. Check your credentials.")
        print("✓ Connected successfully\n")
        
        # Read SQL file
        print("Step 2: Reading SQL setup script...")
        try:
            sql_content = self.read_sql_file()
            print(f"✓ SQL file loaded: {self.sql_file_path}\n")
        except Exception as e:
            self.sf.close()
            raise
        
        # Split into statements
        print("Step 3: Parsing SQL statements...")
        statements = self.split_sql_statements(sql_content)
        print(f"✓ Found {len(statements)} SQL statements to execute\n")
        
        # Optionally drop existing objects
        if drop_existing:
            print("Step 4: Dropping existing objects (if any)...")
            try:
                drop_statements = [
                    "DROP VIEW IF EXISTS FEAT_DB.FEAT_SCHEMA.latest_features",
                    "DROP TABLE IF EXISTS FEAT_DB.FEAT_SCHEMA.feature_store",
                    "DROP VIEW IF EXISTS FEAT_DB.FEAT_SCHEMA.customer_agg_30d",
                    "DROP TABLE IF EXISTS FEAT_DB.FEAT_SCHEMA.tx_cleaned",
                    "DROP TABLE IF EXISTS FEAT_DB.FEAT_SCHEMA.customer_transactions",
                    "DROP SCHEMA IF EXISTS FEAT_DB.FEAT_SCHEMA",
                    "DROP DATABASE IF EXISTS FEAT_DB"
                ]
                for stmt in drop_statements:
                    try:
                        self.sf.execute_update(stmt)
                    except Exception as e:
                        # Ignore errors if objects don't exist
                        pass
                print("✓ Cleanup completed\n")
            except Exception as e:
                print(f"⚠ Warning during cleanup: {e}\n")
        
        # Execute statements
        print("Step 5: Executing SQL statements...")
        print("-" * 70)
        
        results = {
            'total_statements': len(statements),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, statement in enumerate(statements, 1):
            # Skip SELECT statements that are just for display
            if statement.strip().upper().startswith('SELECT') and 'LIMIT' in statement.upper():
                print(f"[{i}/{len(statements)}] Skipping display query: {statement[:50]}...")
                try:
                    # Still execute to show results
                    df = self.sf.execute_query(statement)
                    if len(df) > 0:
                        print(f"    Results: {len(df)} rows")
                        print(df.to_string(index=False))
                except Exception as e:
                    print(f"    (Query failed, but continuing...)")
                continue
            
            # Show what we're executing
            statement_preview = statement[:60].replace('\n', ' ')
            if len(statement) > 60:
                statement_preview += "..."
            
            print(f"[{i}/{len(statements)}] Executing: {statement_preview}")
            
            try:
                # Determine if it's a query (SELECT) or update (CREATE, INSERT, etc.)
                stmt_upper = statement.strip().upper()
                
                if stmt_upper.startswith('SELECT') or stmt_upper.startswith('SHOW'):
                    # It's a query, use execute_query
                    df = self.sf.execute_query(statement)
                    if len(df) > 0:
                        print(f"    ✓ Success - {len(df)} rows returned")
                        # Show preview for small results
                        if len(df) <= 10:
                            print(df.to_string(index=False))
                    else:
                        print(f"    ✓ Success - No rows returned")
                else:
                    # It's an update statement
                    rows_affected = self.sf.execute_update(statement)
                    print(f"    ✓ Success - {rows_affected} rows affected")
                
                results['successful'] += 1
                
            except Exception as e:
                error_msg = str(e)
                print(f"    ✗ Failed: {error_msg}")
                results['failed'] += 1
                results['errors'].append({
                    'statement_number': i,
                    'statement': statement_preview,
                    'error': error_msg
                })
                # Continue with next statement
                continue
            
            print()
        
        # Summary
        print("=" * 70)
        print("SETUP SUMMARY")
        print("=" * 70)
        print(f"Total statements: {results['total_statements']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        
        if results['failed'] > 0:
            print("\nErrors encountered:")
            for error in results['errors']:
                print(f"  Statement {error['statement_number']}: {error['error']}")
            print("\n⚠ Some statements failed. Please review the errors above.")
        else:
            print("\n✓ All statements executed successfully!")
            print("\nFeature Store is ready to use!")
            print("\nNext steps:")
            print("  1. Run: python scripts/feature_store_manager.py")
            print("  2. Run: python scripts/ml_model_training.py")
        
        # Don't close connection yet - verification might need it
        # Connection will be closed in verify_setup or main()
        
        return results
    
    def verify_setup(self) -> dict:
        """
        Verify that the feature store was set up correctly
        
        Returns:
            Dictionary with verification results
        """
        print("\n" + "=" * 70)
        print("VERIFYING SETUP")
        print("=" * 70)
        
        # Reconnect if connection is closed
        if not self.sf.conn or not self.sf.cursor:
            print("Reconnecting to Snowflake for verification...")
            self.sf.connect()
        
        verification = {
            'database_exists': False,
            'schema_exists': False,
            'tables': {},
            'views': {},
            'data_counts': {}
        }
        
        try:
            # Check database
            try:
                df = self.sf.execute_query("SHOW DATABASES")
                # Filter in Python since LIKE doesn't work in SHOW commands
                db_df = df[df['name'] == 'FEAT_DB'] if 'name' in df.columns else pd.DataFrame()
                verification['database_exists'] = len(db_df) > 0
                print(f"✓ Database FEAT_DB exists: {verification['database_exists']}")
            except Exception as e:
                print(f"✗ Error checking database: {e}")
            
            # Check schema
            try:
                df = self.sf.execute_query("SHOW SCHEMAS IN DATABASE FEAT_DB")
                # Filter in Python since LIKE doesn't work in SHOW commands
                schema_df = df[df['name'] == 'FEAT_SCHEMA'] if 'name' in df.columns else pd.DataFrame()
                verification['schema_exists'] = len(schema_df) > 0
                print(f"✓ Schema FEAT_SCHEMA exists: {verification['schema_exists']}")
            except Exception as e:
                print(f"✗ Error checking schema: {e}")
            
            # Check tables
            tables_to_check = ['customer_transactions', 'tx_cleaned', 'feature_store']
            try:
                df = self.sf.execute_query("SHOW TABLES IN SCHEMA FEAT_DB.FEAT_SCHEMA")
                existing_tables = df['name'].str.upper().tolist() if 'name' in df.columns else []
                
                for table in tables_to_check:
                    exists = table.upper() in existing_tables
                    verification['tables'][table] = exists
                    
                    if exists:
                        # Get row count
                        count_df = self.sf.execute_query(f"SELECT COUNT(*) AS cnt FROM FEAT_DB.FEAT_SCHEMA.{table}")
                        count = count_df['CNT'].iloc[0] if len(count_df) > 0 else 0
                        verification['data_counts'][table] = count
                        print(f"✓ Table {table} exists with {count} rows")
                    else:
                        print(f"✗ Table {table} does not exist")
            except Exception as e:
                print(f"✗ Error checking tables: {e}")
            
            # Check views
            views_to_check = ['customer_agg_30d', 'latest_features']
            try:
                df = self.sf.execute_query("SHOW VIEWS IN SCHEMA FEAT_DB.FEAT_SCHEMA")
                existing_views = df['name'].str.upper().tolist() if 'name' in df.columns else []
                
                for view in views_to_check:
                    exists = view.upper() in existing_views
                    verification['views'][view] = exists
                    
                    if exists:
                        # Get row count
                        count_df = self.sf.execute_query(f"SELECT COUNT(*) AS cnt FROM FEAT_DB.FEAT_SCHEMA.{view}")
                        count = count_df['CNT'].iloc[0] if len(count_df) > 0 else 0
                        verification['data_counts'][view] = count
                        print(f"✓ View {view} exists with {count} rows")
                    else:
                        print(f"✗ View {view} does not exist")
            except Exception as e:
                print(f"✗ Error checking views: {e}")
            
        except Exception as e:
            print(f"✗ Verification error: {e}")
        finally:
            # Close connection after verification
            if self.sf.conn:
                self.sf.close()
        
        return verification


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated Feature Store Setup')
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to Snowflake config file (default: config/snowflake_config.json)'
    )
    parser.add_argument(
        '--drop-existing',
        action='store_true',
        help='Drop existing database/schema before creating (WARNING: This will delete all data!)'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify existing setup, do not execute SQL'
    )
    
    args = parser.parse_args()
    
    # Default config path
    if args.config is None:
        args.config = os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            'snowflake_config.json'
        )
    
    try:
        setup = FeatureStoreSetup(args.config)
        
        if args.verify_only:
            try:
                setup.verify_setup()
            except Exception as e:
                print(f"\n✗ Verification error: {e}")
                setup.sf.close()
        else:
            if args.drop_existing:
                response = input(
                    "\n⚠ WARNING: This will DROP existing FEAT_DB database and all its data!\n"
                    "Are you sure you want to continue? (yes/no): "
                )
                if response.lower() != 'yes':
                    print("Setup cancelled.")
                    return
            
            results = setup.execute_setup(drop_existing=args.drop_existing)
            
            # Always verify after setup (if successful)
            if results['failed'] == 0:
                setup.verify_setup()
            else:
                # Close connection if verification won't run
                setup.sf.close()
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease create config/snowflake_config.json with your Snowflake credentials.")
        print("Example config structure:")
        print("""
{
    "account": "your_account",
    "user": "your_username",
    "password": "your_password",
    "warehouse": "COMPUTE_WH",
    "database": "FEAT_DB",
    "schema": "FEAT_SCHEMA"
}
        """)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

