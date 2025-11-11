# Implementation Guide: Feature Engineering with Snowflake & Feature Store

## Overview

This guide provides step-by-step instructions for implementing a complete feature engineering pipeline using Snowflake for data storage and processing, and a Feature Store for managing ML features.

## Architecture

```
Raw Data (Snowflake) 
    ↓
Extract (SQL Queries)
    ↓
Transform (Feature Engineering)
    ↓
Feature Store (Snowflake Tables)
    ↓
ML Model Training/Inference
```

## Step 1: Extract - Fetching Raw Data from Snowflake

### 1.1 Setup Database and Tables

```sql
-- Create database for feature engineering
CREATE DATABASE IF NOT EXISTS FEAT_DB;
USE DATABASE FEAT_DB;

-- Create schema
CREATE SCHEMA IF NOT EXISTS FEAT_SCHEMA;
USE SCHEMA FEAT_SCHEMA;

-- Create customer transactions table with semi-structured data
CREATE OR REPLACE TABLE customer_transactions (
    transaction_id   STRING,
    customer_id      STRING,
    transaction_ts   TIMESTAMP_NTZ,
    amount           FLOAT,
    channel          STRING,  -- e.g., web, app, pos
    metadata         VARIANT -- semi-structured JSON payload
);
```

### 1.2 Extract Raw Data

```sql
-- Extract transaction data
SELECT 
    transaction_id,
    customer_id,
    transaction_ts,
    amount,
    channel,
    metadata:promo::STRING as promo_code,
    metadata:items AS items
FROM FEAT_DB.FEAT_SCHEMA.customer_transactions
WHERE transaction_ts >= DATEADD(day, -30, CURRENT_TIMESTAMP())
ORDER BY transaction_ts DESC;
```

## Step 2: Transform - Feature Engineering

### 2.1 Data Cleaning and Derived Columns

```sql
-- Clean and derive columns from raw transactions
CREATE OR REPLACE TABLE tx_cleaned AS
SELECT
    transaction_id,
    customer_id,
    transaction_ts,
    amount,
    channel,
    metadata,
    -- Extract from semi-structured data
    COALESCE(metadata:promo::STRING, 'NO_PROMO') AS promo_code,
    DATE_TRUNC('day', transaction_ts)::DATE AS tx_date,
    DAYOFWEEK(transaction_ts) as day_of_week,
    -- Handle missing values
    CASE WHEN amount IS NULL THEN 0.0 ELSE amount END as amount_filled,
    -- Create high-value flag
    CASE WHEN amount >= 100 THEN 1 ELSE 0 END as high_value_flag
FROM FEAT_DB.FEAT_SCHEMA.customer_transactions
WHERE transaction_ts IS NOT NULL;
```

### 2.2 Aggregation Features (30-Day Window)

Here's where we create the actual features. We're looking at the last 30 days of transactions for each customer and calculating three things:

```sql
-- Customer-level aggregations for last 30 days
CREATE OR REPLACE VIEW customer_agg_30d AS
SELECT
    customer_id,
    -- Average transaction amount
    AVG(amount_filled) AS avg_tx_amount_30d,
    -- Transaction count
    COUNT(*) AS tx_count_30d,
    -- High-value transaction count
    SUM(high_value_flag) AS high_value_tx_count_30d
FROM FEAT_DB.FEAT_SCHEMA.tx_cleaned
WHERE transaction_ts >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY customer_id;
```

**Let's break down what each feature means with real numbers:**

**Feature 1: avg_tx_amount_30d**

This is the average transaction amount. The formula is:
```
avg_tx_amount_30d = sum(amount_filled) / count(transactions)
```

**Real example**: Customer cust01 has 3 transactions in last 30 days:
- Oct 10: $120.50
- Oct 12: $40.00  
- Sep 11: $75.00

Average = (120.50 + 40.00 + 75.00) / 3 = **$78.50**

This tells us their typical spending per transaction recently.

**Feature 2: tx_count_30d**

Simple count - how many transactions did they make?

**Real example**:
- cust01: 3 transactions
- cust02: 3 transactions
- cust03: 2 transactions
- cust04: 2 transactions
- cust05: 2 transactions

This shows transaction frequency - are they a frequent buyer or occasional?

**Feature 3: high_value_tx_count_30d**

This counts how many "big" transactions (≥ $100) they made. We first create a flag:
```
high_value_flag = 1 if amount >= 100, else 0
```

Then sum these flags:
```
high_value_tx_count_30d = sum(high_value_flag)
```

**Real example**:
- cust01: 1 high-value transaction ($120.50)
- cust02: 2 high-value transactions ($300, $150)
- cust03: 0 high-value transactions (both under $100)
- cust04: 2 high-value transactions ($200, $95 - wait, $95 doesn't count!)
- Actually cust04: 1 high-value transaction ($200)

This feature helps identify customers who make big purchases, which might indicate higher value customers.

### 2.3 Why These Features Work

These three features capture different aspects of customer behavior:
- **avg_tx_amount_30d**: Spending level (how much per transaction)
- **tx_count_30d**: Engagement (how often they shop)
- **high_value_tx_count_30d**: Purchase pattern (do they make big purchases?)

Together, they give a pretty good picture of a customer's recent behavior. When we train our ML model, it learns patterns like "customers with high tx_count_30d and high avg_tx_amount_30d tend to be high-value customers."

## Step 3: Load into Feature Store

### 3.1 Create Feature Store Table (Key-Value Format)

```sql
-- Create feature store table (key-value format for flexibility)
CREATE OR REPLACE TABLE feature_store (
    feature_id STRING,         -- e.g., cust01_avg_tx_30d
    entity_id  STRING,         -- entity, e.g., customer_id
    feature_name STRING,       -- e.g., avg_tx_amount_30d
    feature_value FLOAT,
    created_at TIMESTAMP_NTZ,
    feature_ts TIMESTAMP_NTZ,  -- timestamp for feature (for point-in-time queries)
    source      STRING         -- source of feature computation
);
```

**Why Key-Value Format?**
- Flexible: Easy to add new features without schema changes
- Scalable: Can store many features per entity
- Versioned: Each feature update creates a new row with timestamp
- Point-in-Time: Can query features as they existed at any point in time

### 3.2 Populate Feature Store

```sql
-- Insert all features from customer_agg_30d
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
```

### 3.3 Create Latest Features View

```sql
-- Create view for latest features per entity (for serving)
CREATE OR REPLACE VIEW latest_features AS
SELECT 
    f.entity_id,
    f.feature_name,
    f.feature_value,
    f.feature_ts
FROM feature_store f
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY f.entity_id, f.feature_name 
    ORDER BY f.feature_ts DESC
) = 1;
```

This view automatically returns the most recent value for each feature per entity.

## Step 4: Access Features for ML

### 4.1 Retrieve Features for Training (Python)

The Python `FeatureStoreManager` automatically retrieves and pivots features:

```python
from feature_store_manager import FeatureStoreManager

fs_manager = FeatureStoreManager(config_path)
# Automatically retrieves and pivots to wide format
features_df = fs_manager.get_features_for_training()
```

**What happens behind the scenes:**
1. Queries `latest_features` view
2. Pivots key-value format to wide format (one row per entity)
3. Returns DataFrame ready for ML training

### 4.2 Point-in-Time Feature Retrieval

```python
from datetime import datetime

# Get features as they existed at a specific time
features_df = fs_manager.get_point_in_time_features(
    entity_id='cust01',
    timestamp=datetime(2025, 10, 15)
)
```

**SQL equivalent:**
```sql
-- Get features at a specific point in time
SELECT 
    entity_id,
    feature_name,
    feature_value,
    feature_ts
FROM feature_store
WHERE entity_id = 'cust01'
    AND feature_ts <= '2025-10-15 00:00:00'
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY entity_id, feature_name 
    ORDER BY feature_ts DESC
) = 1;
```

### 4.3 Batch Feature Retrieval

```python
# Get features for multiple entities
features_df = fs_manager.get_latest_features(['cust01', 'cust02', 'cust03'])
```

**SQL equivalent:**
```sql
-- Get latest features for multiple customers
SELECT * 
FROM latest_features
WHERE entity_id IN ('cust01', 'cust02', 'cust03');
```

## Step 5: ML Model Training

### 5.1 Training Regression Model

We're trying to predict `avg_tx_amount_30d` (average transaction amount) using the other features. Here's what happens:

```python
from ml_model_training import MLModelTrainer

trainer = MLModelTrainer(config_path)
results = trainer.train_regression_model(target_column='avg_tx_amount_30d')
```

**What's happening behind the scenes:**

1. **Get the data**: We retrieve features from the Feature Store. With our small dataset, we get 4 customer records.

2. **Handle missing values**: If any feature is missing, we fill it with the median. The formula is:
   ```
   missing_value = median(all_values_for_that_feature)
   ```

3. **Split the data**: We use 80% for training, 20% for testing. With 4 records:
   - Training: 3 records
   - Testing: 1 record

4. **Scale the features**: This is crucial. We use StandardScaler, which does:
   ```
   scaled_value = (value - mean) / standard_deviation
   ```
   
   **Real example**: If `tx_count_30d` has values [1, 2, 3]:
   - Mean = 2
   - Std = 0.816
   - Scaled values: [(1-2)/0.816, (2-2)/0.816, (3-2)/0.816] = [-1.225, 0, 1.225]

5. **Train the model**: Random Forest creates multiple decision trees and averages their predictions.

6. **Evaluate**: We calculate RMSE (Root Mean Squared Error):
   ```
   RMSE = sqrt(mean((actual - predicted)²))
   ```
   
   And R² (coefficient of determination):
   ```
   R² = 1 - (sum((actual - predicted)²) / sum((actual - mean)²))
   ```

**Important**: Each model gets its own scaler. Why? Because if we train a regression model, then train a classification model, the classification scaler would overwrite the regression scaler. Then when we try to predict with the regression model, it would use the wrong scaling, causing errors. So we store the scaler with each model's results.

### 5.2 Training Classification Model

Now we're trying to classify customers as "high value" or "low value". Here's how it works:

```python
results = trainer.train_classification_model(target_column='high_value_customer')
```

**What happens:**

1. **Create the target**: If `high_value_customer` doesn't exist, we create it. We look at `avg_tx_amount_30d` and say:
   - If above median → "High Value"
   - If below median → "Low Value"
   
   **Real example**: With our 4 customers, if the median avg_tx_amount_30d is $100:
   - cust01 ($78.50) → "Low Value"
   - cust02 ($158.33) → "High Value"
   - cust03 ($50.00) → "Low Value"
   - cust04 ($147.50) → "High Value"

2. **Encode the target**: We convert "High Value"/"Low Value" to numbers:
   - "Low Value" → 0
   - "High Value" → 1
   
   This is called label encoding. The formula is just assigning numbers to categories.

3. **Handle class imbalance**: If all customers are "High Value", we can't train a classifier. In our case, we might have 2 High and 2 Low, which is balanced.

4. **Train the model**: Random Forest Classifier creates trees that split on features to separate High from Low Value customers.

5. **Evaluate**: We calculate accuracy:
   ```
   accuracy = (correct_predictions / total_predictions) × 100%
   ```
   
   With perfect predictions on our small test set, we get 100% accuracy (though this is likely overfitting with such a small dataset).

**Important**: This model gets its own scaler, completely separate from the regression model. This prevents the "feature mismatch" error we fixed earlier.

### 5.3 Making Predictions

Now for the fun part - actually predicting something for a real customer. Let's predict for cust01:

```python
prediction = trainer.predict_for_entity(
    entity_id='cust01',
    model=results['model'],
    feature_columns=results['feature_columns'],
    scaler=results['scaler']  # Important: use the same scaler from training
)
```

**Step-by-step what happens:**

1. **Get features for cust01**: We query the Feature Store and get:
   - high_value_tx_count_30d: 0.0
   - tx_count_30d: 1.0
   - (Note: avg_tx_amount_30d might be missing if it's the target)

2. **Build the feature vector**: We create a DataFrame with the exact features the model expects, in the exact order. If a feature is missing, we fill it with 0.0.

3. **Scale using the SAME scaler**: This is critical. We use the scaler that was fit during training. The formula is:
   ```
   scaled_value = (value - mean_from_training) / std_from_training
   ```
   
   **Why the same scaler?** The model learned patterns on scaled data. If we use different scaling (different mean/std), the model will make wrong predictions.

4. **Predict**: The model outputs a prediction. In our case, it predicted **64.58** for cust01's avg_tx_amount_30d.

**Real output from our run:**
```
Prediction for entity cust01: 64.58
Features used: {'high_value_tx_count_30d': 0.0, 'tx_count_30d': 1.0}
```

This means: based on cust01 having 0 high-value transactions and 1 total transaction in the last 30 days, the model predicts their average transaction amount would be around $64.58.

**Why this matters**: In production, you'd use this to:
- Identify customers likely to make high-value purchases
- Personalize marketing offers
- Predict customer lifetime value
- Detect unusual spending patterns

## Best Practices

1. **Feature Documentation**: Document each feature's definition and business logic
2. **Data Quality Checks**: Validate features before storing
3. **Incremental Updates**: Update only changed features to save compute
4. **Monitoring**: Track feature distributions and detect drift
5. **Testing**: Test feature computation logic thoroughly
6. **Versioning**: Maintain feature versions for reproducibility
7. **Performance**: Index feature tables for fast retrieval

