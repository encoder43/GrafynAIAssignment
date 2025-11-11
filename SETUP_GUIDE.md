# Setup Guide: Feature Engineering with Snowflake and Feature Stores

## Prerequisites

1. **Snowflake Account**
   - Sign up for free trial at [snowflake.com](https://www.snowflake.com)
   - Note your account URL, username, and password
   - Create a warehouse (or use default COMPUTE_WH)

2. **Python Environment**
   - Python 3.8 or higher
   - pip package manager

## Step-by-Step Setup

### Step 1: Clone/Download Project

```bash
# If using git
git clone <repository-url>
cd GrafynAIAssignment

# Or download and extract the project folder
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- snowflake-connector-python
- snowflake-sqlalchemy
- pandas
- numpy
- scikit-learn

### Step 3: Configure Snowflake Connection

1. Copy the example config file:
   ```bash
   cp config/snowflake_config.json.example config/snowflake_config.json
   ```

2. Edit `config/snowflake_config.json` with your Snowflake credentials:
   ```json
   {
     "account": "your_account_identifier",
     "user": "your_username",
     "password": "your_password",
     "warehouse": "COMPUTE_WH",
     "database": "FEAT_DB",
     "schema": "FEAT_SCHEMA"
   }
   ```

   **Note:** Your account identifier format is usually: `xxxxx.yyy-zzz` (e.g., `abc12345.us-east-1`)

### Step 4: Set Up Snowflake Database

**Option A: Automated Setup (Recommended)**

```bash
python scripts/setup_feature_store.py
```

This will automatically:
- Create database (FEAT_DB) and schema (FEAT_SCHEMA)
- Create all tables and views
- Insert sample transaction data
- Set up feature store
- Verify everything was created correctly

**Option B: Manual Setup**

1. Log into Snowflake Web UI (https://app.snowflake.com)

2. Open a new worksheet

3. Execute the complete SQL script:
   - Open `sql/snowflake_feature_engineering.sql`
   - Copy and paste into Snowflake worksheet
   - Execute (Ctrl+Enter or click Run)

4. Verify Setup:
   ```sql
   -- Check transactions
   SELECT COUNT(*) FROM FEAT_DB.FEAT_SCHEMA.customer_transactions;
   
   -- Check feature store
   SELECT COUNT(*) FROM FEAT_DB.FEAT_SCHEMA.feature_store;
   
   -- Check latest features view
   SELECT * FROM FEAT_DB.FEAT_SCHEMA.latest_features LIMIT 5;
   ```

### Step 7: Test Python Connection

```bash
python scripts/snowflake_connection.py
```

Expected output:
```
Successfully connected to Snowflake
Database: FEAT_DB
Schema: FEAT_SCHEMA
```

### Step 8: Test Feature Store Manager

```bash
python scripts/feature_store_manager.py
```

This should:
- Connect to Snowflake
- Retrieve feature statistics
- Display sample features

### Step 9: Train ML Models

```bash
python scripts/ml_model_training.py
```

This will:
- Retrieve features from Feature Store
- Train a regression model (predicting avg_tx_amount_30d)
- Train a classification model (predicting high_value_customer)
- Display model performance metrics
- Make a prediction for a sample entity (cust01)

Expected output includes:
- Model performance metrics (RMSE, R², Accuracy)
- Feature importance rankings
- Successful prediction result

## Troubleshooting

### Connection Issues

**Error: "Invalid account identifier"**
- Check your account format: should be `xxxxx.yyy-zzz`
- Ensure no extra spaces or characters

**Error: "Authentication failed"**
- Verify username and password
- Check if account is locked (reset password if needed)

**Error: "Database does not exist"**
- Make sure you executed `sql/snowflake_feature_engineering.sql` or ran `setup_feature_store.py`
- Check database name in config matches (should be FEAT_DB)

### SQL Execution Issues

**Error: "Table already exists"**
- This is normal if re-running scripts
- Use `DROP TABLE IF EXISTS` or `CREATE OR REPLACE TABLE`

**Error: "Schema does not exist"**
- Ensure you're using the correct database context
- Run `USE DATABASE FEAT_DB; USE SCHEMA FEAT_SCHEMA;` first

### Python Import Issues

**Error: "Module not found"**
- Ensure you're in the project root directory
- Run `pip install -r requirements.txt` again
- Check Python version: `python --version` (should be 3.8+)

**Error: "Cannot import feature_store_manager"**
- Make sure you're running from project root
- Or use: `python -m scripts.feature_store_manager`

## Verification Checklist

- [ ] Snowflake account created and accessible
- [ ] Python dependencies installed
- [ ] Config file created with correct credentials
- [ ] Database (FEAT_DB) and schema (FEAT_SCHEMA) created in Snowflake
- [ ] Sample transaction data inserted (12 transactions for 5 customers)
- [ ] Feature aggregation view (customer_agg_30d) created
- [ ] Feature Store table created and populated with features
- [ ] Latest features view created
- [ ] Python connection test successful
- [ ] Feature Store manager test successful
- [ ] ML model training runs without errors

## Next Steps

1. **Explore the Documentation**
   - Read `docs/01_feature_engineering_intro.md`
   - Review `docs/02_snowflake_overview.md`
   - Study `docs/03_feature_store_concepts.md`
   - Follow `docs/04_implementation_guide.md`

2. **Experiment with SQL**
   - Modify feature engineering queries
   - Create new features
   - Test different aggregations

3. **Customize ML Models**
   - Try different algorithms
   - Experiment with feature selection
   - Tune hyperparameters

4. **Prepare for Submission**
   - Record video walkthrough (max 15 mins)
   - Create presentation from template
   - Push to GitHub repository
   - Submit via Google Form

## Video Walkthrough Tips

1. **Structure (15 minutes max):**
   - Introduction (1 min)
   - Snowflake setup (2 mins)
   - Feature engineering demonstration (4 mins)
   - Feature Store implementation (3 mins)
   - ML model training (3 mins)
   - Results and conclusion (2 mins)

2. **What to Show:**
   - Snowflake Web UI with database
   - SQL query execution
   - Feature Store tables
   - Python scripts running
   - Model training results

3. **Best Practices:**
   - Speak clearly and explain each step
   - Show code snippets on screen
   - Demonstrate actual results
   - Keep it concise and focused

## Support

For questions or issues:
- Email: hr@vistora.co.in or hr@grafyn.a
- Check documentation in `docs/` folder
- Review SQL scripts for examples

