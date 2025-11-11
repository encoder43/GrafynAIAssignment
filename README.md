# Feature Engineering Using Snowflake and Feature Stores

## Project Overview

This project demonstrates feature engineering workflows using Snowflake for data storage and processing, and Feature Stores for managing ML features. The implementation covers the complete ML pipeline from data extraction to feature serving.

## Project Structure

```
.
├── README.md                          # Project overview and setup instructions
├── docs/                              # Documentation files
│   ├── 01_feature_engineering_intro.md
│   ├── 02_snowflake_overview.md
│   ├── 03_feature_store_concepts.md
│   └── 04_implementation_guide.md
├── sql/                               # Snowflake SQL scripts
│   └── snowflake_feature_engineering.sql  # Complete setup script
├── scripts/                           # Python scripts for Feature Store integration
│   ├── setup_feature_store.py         # 🚀 Automated setup script
│   ├── snowflake_connection.py        # Snowflake connection utility
│   ├── feature_store_manager.py       # Feature Store operations
│   └── ml_model_training.py           # ML model training
├── config/                            # Configuration files
│   └── snowflake_config.json         # Your Snowflake credentials (create from example)
└── presentation/                      # Presentation materials
    └── Feature_Engineering_Presentation.md
```

## Prerequisites

1. **Snowflake Account**: Sign up for a free trial at [snowflake.com](https://www.snowflake.com)
2. **Python 3.8+**: For Feature Store integration scripts
3. **Required Python Packages**:
   - snowflake-connector-python
   - snowflake-sqlalchemy
   - pandas
   - scikit-learn

## Setup Instructions

### 1. Snowflake Account Setup

1. Sign up for Snowflake free trial
2. Note down your account URL, username, password, and warehouse details
3. Create a new database and schema for this project

### 2. Configuration

1. Create `config/snowflake_config.json` with your Snowflake credentials:
   ```json
   {
     "account": "your_account",
     "user": "your_username",
     "password": "your_password",
     "warehouse": "COMPUTE_WH",
     "database": "FEAT_DB",
     "schema": "FEAT_SCHEMA"
   }
   ```

### 3. Automated Database Setup (Recommended) 🚀

**Option A: Automated Setup (Easiest)**
```bash
# Install dependencies first
pip install -r requirements.txt

# Run automated setup script
python scripts/setup_feature_store.py
```

The automated script will:
- ✅ Connect to Snowflake
- ✅ Create database and schema (FEAT_DB.FEAT_SCHEMA)
- ✅ Create all tables and views
- ✅ Insert sample data
- ✅ Set up feature store
- ✅ Verify everything was created correctly

**Option B: Manual Setup**
1. Log into Snowflake Web UI
2. Open a SQL Worksheet
3. Copy and paste the contents of `sql/snowflake_feature_engineering.sql`
4. Execute the script

### 4. Python Environment Setup

```bash
# Install required packages
pip install -r requirements.txt
```

## Usage

### Quick Start

1. **Setup Feature Store** (one-time):
   ```bash
   python scripts/setup_feature_store.py
   ```

2. **Verify Setup**:
   ```bash
   python scripts/setup_feature_store.py --verify-only
   ```

3. **Use Feature Store**:
   ```bash
   # Connect and view features
   python scripts/feature_store_manager.py
   
   # Train ML models
   python scripts/ml_model_training.py
   ```

### Advanced Options

```bash
# Drop existing database and recreate (WARNING: Deletes all data!)
python scripts/setup_feature_store.py --drop-existing

# Use custom config file
python scripts/setup_feature_store.py --config /path/to/config.json
```

### Running Individual Scripts

```bash
# Test Snowflake connection
python scripts/snowflake_connection.py

# Manage Feature Store operations
python scripts/feature_store_manager.py

# Train ML models using features
python scripts/ml_model_training.py
```

### Expected Output

When running `ml_model_training.py`, you should see:
- Regression model training with RMSE and R² metrics
- Classification model training with accuracy metrics
- Feature importance rankings
- Successful prediction for sample entity (e.g., cust01)

**Note**: Model performance metrics may vary with small datasets. The pipeline is designed to work with larger datasets in production.

## Key Features

- **Data Extraction**: SQL queries to extract raw transaction data from Snowflake
- **Feature Engineering**: Time-based aggregations (30-day windows), transaction counts, high-value flags
- **Feature Store**: Key-value based feature storage with versioning and point-in-time retrieval
- **ML Integration**: 
  - Regression model training (predicting avg_tx_amount_30d)
  - Classification model training (high_value_customer prediction)
  - Individual entity prediction with proper feature scaling
- **Automated Setup**: One-command setup script for complete database initialization

## Documentation

Detailed documentation is available in the `docs/` folder:
- Feature Engineering Introduction
- Snowflake Overview and Integration
- Feature Store Concepts and Comparison
- Implementation Guide

## Deliverables

- ✅ Complete project code and documentation
- ✅ SQL scripts for Snowflake operations
- ✅ Feature Store integration
- ✅ Presentation materials
- ✅ Video walkthrough (to be recorded separately)

## Video Walkthrough

A 15-minute video walkthrough will be recorded covering:
- Project design and architecture
- Snowflake setup and data extraction
- Feature engineering techniques
- Feature Store implementation
- ML model integration

## Presentation

The presentation document is available in `presentation/Feature_Engineering_Presentation.md` with code snippets and explanations for each step.

## License

This project is created for educational purposes as part of the Grafyn AI assignment.

## Contact

For questions: hr@vistora.co.in or hr@grafyn.a

