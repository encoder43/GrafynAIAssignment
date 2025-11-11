# Feature Engineering Using Snowflake and Feature Stores
## Assignment Presentation

---

## Slide 1: Title Slide

**Feature Engineering Using Snowflake and Feature Stores**

- Assignment for Grafyn AI
- Complete ML Pipeline Implementation
- Date: [Your Date]

---

## Slide 2: Agenda

1. Introduction to Feature Engineering
2. Snowflake for Data Storage & Processing
3. Feature Store Concepts
4. Implementation Overview
5. Practical Demonstration
6. Results and Next Steps

---

## Slide 3: What is Feature Engineering?

**Definition:**
- Process of transforming raw data into features that better represent the problem
- Critical step in ML pipeline that significantly impacts model performance

**Key Benefits:**
- Improves model accuracy
- Incorporates domain knowledge
- Reduces dimensionality
- Enhances interpretability

**Example:**
- Raw: `sale_date = '2024-01-15'`
- Engineered: `day_of_week = 1`, `is_weekend = 0`, `month = 1`

---

## Slide 4: Feature Engineering Techniques

### 1. Normalization & Standardization
- Min-Max Scaling: `(x - min) / (max - min)`
- Z-score: `(x - mean) / std`

### 2. Encoding
- One-Hot Encoding for categorical variables
- Label Encoding for ordinal data
- Target Encoding for high-cardinality categories

### 3. Time-Based Aggregations
- Extract temporal features (day, month, hour)
- Rolling windows (7-day, 30-day averages)
- Time differences (days since last purchase)

### 4. Aggregations
- Statistical: mean, median, std, min, max
- Group aggregations by categories
- Customer-level summaries

---

## Slide 5: Snowflake Overview

**What is Snowflake?**
- Cloud-native data platform
- Separates storage and compute
- Supports structured and semi-structured data

**Key Features:**
- Automatic scaling
- Time Travel for versioning
- Zero-copy cloning
- SQL interface

**Why Snowflake for ML?**
- Handles large datasets efficiently
- Familiar SQL syntax
- Easy integration with Python
- Cost-effective compute model

---

## Slide 6: Snowflake Data Extraction

**Example: Extract Sales Data**

```sql
SELECT 
    s.sale_id,
    s.customer_id,
    s.sale_date,
    s.sale_amount,
    c.customer_segment,
    p.product_name
FROM sales s
INNER JOIN customers c ON s.customer_id = c.customer_id
INNER JOIN products p ON s.product_id = p.product_id
WHERE s.sale_date >= '2024-01-01'
ORDER BY s.sale_date DESC;
```

**Key Operations:**
- Joins across multiple tables
- Filtering and aggregation
- Time-based queries
- Window functions for rolling calculations

---

## Slide 7: Feature Engineering in Snowflake

**Temporal Features Example:**

```sql
SELECT 
    sale_date,
    EXTRACT(DAYOFWEEK FROM sale_date) AS day_of_week,
    EXTRACT(MONTH FROM sale_date) AS month,
    CASE 
        WHEN EXTRACT(DAYOFWEEK FROM sale_date) IN (1, 7) 
        THEN 1 ELSE 0 
    END AS is_weekend
FROM sales;
```

**Aggregation Features:**

```sql
SELECT 
    customer_id,
    COUNT(*) AS total_purchases,
    SUM(sale_amount) AS total_spent,
    AVG(sale_amount) AS avg_purchase_amount,
    DATEDIFF('day', MAX(sale_date), CURRENT_DATE()) 
        AS days_since_last_purchase
FROM sales
GROUP BY customer_id;
```

---

## Slide 8: Rolling Window Features

**7-Day and 30-Day Rolling Windows:**

```sql
SELECT 
    customer_id,
    sale_date,
    sale_amount,
    -- 7-day rolling average
    AVG(sale_amount) OVER (
        PARTITION BY customer_id 
        ORDER BY sale_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS avg_7day_purchase,
    -- 30-day rolling sum
    SUM(sale_amount) OVER (
        PARTITION BY customer_id 
        ORDER BY sale_date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS sum_30day_purchase
FROM sales;
```

**Benefits:**
- Captures recent trends
- Smooths out noise
- Provides context for predictions

---

## Slide 9: What is a Feature Store?

**Definition:**
- Centralized repository for storing, managing, and serving ML features
- Bridge between data engineering and machine learning

**Key Problems It Solves:**
- Feature inconsistency between training and production
- Code duplication across projects
- Data leakage prevention
- Slow feature serving
- Lack of versioning

**Benefits:**
- Consistency across environments
- Feature reusability
- Version control
- Low-latency serving
- Governance and monitoring

---

## Slide 10: Feature Store Comparison

| Feature | AWS SageMaker | Snowflake | Databricks | Feast |
|---------|--------------|-----------|------------|-------|
| Managed | Yes | Yes | Yes | No |
| Online Store | Yes | Limited | Yes | Yes |
| SQL Interface | Limited | Excellent | Good | Limited |
| Cost | High | Medium | Medium | Low |
| Best For | AWS users | Snowflake users | Databricks users | Flexible needs |

**Our Choice: Snowflake Feature Store**
- Already using Snowflake for data storage
- SQL-based feature definitions
- Cost-effective
- Leverages existing infrastructure

---

## Slide 11: Feature Store Architecture

```
Raw Data (Snowflake Tables)
    ↓
Feature Engineering (SQL Views)
    ↓
Feature Store (Snowflake Tables)
    ├── Offline Store (Historical Features)
    └── Online Store (Latest Features)
    ↓
ML Models (Training & Inference)
```

**Key Components:**
1. Feature Registry: Metadata and definitions
2. Storage Layer: Tables for features
3. Serving Layer: Views for retrieval
4. Versioning: Time Travel for history

---

## Slide 12: Feature Store Implementation

**Step 1: Create Feature Store Table**

```sql
CREATE TABLE FEATURE_STORE.customer_features (
    customer_id VARCHAR(50) PRIMARY KEY,
    feature_timestamp TIMESTAMP,
    total_purchases INT,
    total_spent DECIMAL(10, 2),
    avg_purchase_amount DECIMAL(10, 2),
    days_since_last_purchase INT,
    -- ... more features ...
    feature_version INT
);
```

**Step 2: Populate Features**

```sql
INSERT INTO FEATURE_STORE.customer_features
SELECT 
    customer_id,
    CURRENT_TIMESTAMP() AS feature_timestamp,
    COUNT(*) AS total_purchases,
    SUM(sale_amount) AS total_spent,
    -- ... feature calculations ...
FROM sales
GROUP BY customer_id;
```

---

## Slide 13: Feature Retrieval for ML

**Latest Features View:**

```sql
CREATE VIEW latest_customer_features AS
SELECT * 
FROM customer_features
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_id 
    ORDER BY feature_timestamp DESC
) = 1;
```

**Retrieve for Training:**

```sql
SELECT 
    customer_id,
    age,
    total_purchases,
    total_spent,
    days_since_last_purchase,
    is_electronics_buyer,
    recent_purchases
FROM latest_customer_features
WHERE customer_id IS NOT NULL
    AND total_purchases > 0;
```

---

## Slide 14: Point-in-Time Feature Retrieval

**Historical Features:**

```sql
SELECT 
    customer_id,
    total_purchases,
    total_spent,
    feature_timestamp
FROM customer_features
WHERE customer_id = 'C001'
    AND feature_timestamp <= '2024-05-01 00:00:00'
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_id 
    ORDER BY feature_timestamp DESC
) = 1;
```

**Use Cases:**
- Training models on historical data
- Preventing data leakage
- Reproducing past predictions
- Analyzing feature evolution

---

## Slide 15: Python Integration

**Connect to Snowflake:**

```python
from snowflake_connection import SnowflakeConnection

sf = SnowflakeConnection('config/snowflake_config.json')
sf.connect()

# Execute query
df = sf.execute_query("SELECT * FROM latest_customer_features")
```

**Feature Store Manager:**

```python
from feature_store_manager import FeatureStoreManager

fs = FeatureStoreManager()
features = fs.get_features_for_training()
```

---

## Slide 16: ML Model Training

**Training Pipeline:**

```python
from ml_model_training import MLModelTrainer

trainer = MLModelTrainer()

# Train regression model
results = trainer.train_regression_model(
    target_column='total_spent'
)

# Train classification model
results = trainer.train_classification_model(
    target_column='customer_segment'
)
```

**Features Used:**
- Customer demographics (age, gender, segment)
- Purchase behavior (total purchases, total spent)
- Temporal features (days since last purchase)
- Category preferences (electronics, clothing, etc.)
- Rolling window features (7-day, 30-day averages)

---

## Slide 17: Model Results

**Regression Model (Predicting Total Spent):**
- Train RMSE: [Value]
- Test RMSE: [Value]
- Train R²: [Value]
- Test R²: [Value]

**Top Important Features:**
1. total_purchases
2. avg_purchase_amount
3. days_since_last_purchase
4. recent_spent
5. electronics_spent

**Classification Model (Customer Segment):**
- Train Accuracy: [Value]
- Test Accuracy: [Value]

---

## Slide 18: Feature Engineering Pipeline

**Complete Workflow:**

1. **Extract**: SQL queries to fetch raw data from Snowflake
   - Customer data
   - Sales transactions
   - Product information

2. **Transform**: Feature engineering SQL scripts
   - Temporal features
   - Aggregations
   - Rolling windows
   - Encoding

3. **Load**: Populate Feature Store
   - Store computed features
   - Maintain version history
   - Create latest features view

4. **Serve**: Retrieve for ML
   - Training data extraction
   - Real-time inference
   - Point-in-time queries

---

## Slide 19: Key Features Created

**Demographic Features:**
- Age, gender, city, customer segment
- Customer lifetime days

**Purchase Behavior:**
- Total purchases, total spent
- Average purchase amount
- Min, max, median purchases
- Standard deviation

**Temporal Features:**
- Days since last purchase
- First and last purchase dates
- Customer lifetime days

**Category Features:**
- Purchases per category (Electronics, Clothing, Food, Books)
- Spending per category
- Binary flags for category preferences

**Rolling Window Features:**
- 7-day average purchase
- 30-day sum and count
- Cumulative totals

---

## Slide 20: Best Practices Implemented

1. **Feature Documentation**
   - Clear naming conventions
   - Documented in SQL comments

2. **Version Control**
   - Feature versioning in Feature Store
   - Time Travel for historical access

3. **Data Quality**
   - NULL handling
   - Data validation checks
   - Missing value imputation

4. **Performance**
   - Indexes on key columns
   - Materialized views for common queries
   - Efficient window functions

5. **Reproducibility**
   - Point-in-time feature retrieval
   - Consistent transformations
   - Version tracking

---

## Slide 21: Challenges and Solutions

**Challenge 1: Feature Consistency**
- Solution: Centralized Feature Store with versioning

**Challenge 2: Real-time Feature Updates**
- Solution: Scheduled tasks to refresh features

**Challenge 3: Feature Serving Latency**
- Solution: Pre-computed features in Feature Store

**Challenge 4: Data Leakage**
- Solution: Point-in-time queries ensure no future data

**Challenge 5: Feature Reusability**
- Solution: Shared Feature Store across models

---

## Slide 22: Project Structure

```
project/
├── docs/                    # Documentation
│   ├── 01_feature_engineering_intro.md
│   ├── 02_snowflake_overview.md
│   ├── 03_feature_store_concepts.md
│   └── 04_implementation_guide.md
├── sql/                     # SQL scripts
│   ├── 01_setup_database.sql
│   ├── 02_sample_data.sql
│   ├── 03_extract_raw_data.sql
│   ├── 04_feature_engineering.sql
│   ├── 05_feature_store_setup.sql
│   └── 06_retrieve_features.sql
├── scripts/                 # Python scripts
│   ├── snowflake_connection.py
│   ├── feature_store_manager.py
│   └── ml_model_training.py
└── config/                  # Configuration
    └── snowflake_config.json.example
```

---

## Slide 23: Code Snippets - Feature Engineering

**Customer Aggregations:**

```sql
CREATE VIEW customer_aggregations AS
SELECT 
    customer_id,
    COUNT(*) AS total_purchases,
    SUM(sale_amount) AS total_spent,
    AVG(sale_amount) AS avg_purchase_amount,
    DATEDIFF('day', MAX(sale_date), CURRENT_DATE()) 
        AS days_since_last_purchase
FROM sales
GROUP BY customer_id;
```

**Category Encoding:**

```sql
SELECT 
    customer_id,
    SUM(CASE WHEN category = 'Electronics' THEN 1 ELSE 0 END) 
        AS electronics_purchases,
    CASE WHEN SUM(CASE WHEN category = 'Electronics' THEN 1 ELSE 0 END) > 0 
        THEN 1 ELSE 0 END AS is_electronics_buyer
FROM sales
GROUP BY customer_id;
```

---

## Slide 24: Code Snippets - Feature Store

**Feature Store Population:**

```sql
INSERT INTO FEATURE_STORE.customer_features
SELECT 
    c.customer_id,
    CURRENT_TIMESTAMP() AS feature_timestamp,
    COALESCE(agg.total_purchases, 0) AS total_purchases,
    COALESCE(agg.total_spent, 0) AS total_spent,
    -- ... more features ...
    1 AS feature_version
FROM customers c
LEFT JOIN customer_aggregations agg 
    ON c.customer_id = agg.customer_id;
```

**Latest Features View:**

```sql
CREATE VIEW latest_customer_features AS
SELECT * 
FROM customer_features
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_id 
    ORDER BY feature_timestamp DESC
) = 1;
```

---

## Slide 25: Code Snippets - Python Integration

**Feature Retrieval:**

```python
from feature_store_manager import FeatureStoreManager

fs = FeatureStoreManager()

# Get features for training
features = fs.get_features_for_training(
    filters={'customer_segment': 'Premium'}
)

# Get features for specific customers
customer_features = fs.get_latest_features(['C001', 'C002'])
```

**Model Training:**

```python
from ml_model_training import MLModelTrainer

trainer = MLModelTrainer()

# Train model
results = trainer.train_regression_model(
    target_column='total_spent'
)

# Make prediction
prediction = trainer.predict_for_customer(
    'C001',
    results['model'],
    results['feature_columns']
)
```

---

## Slide 26: Results Summary

**Features Created:**
- 30+ engineered features
- Multiple feature categories
- Time-based and aggregated features

**Feature Store:**
- Centralized feature storage
- Version control implemented
- Point-in-time retrieval working

**ML Models:**
- Regression model trained
- Classification model trained
- Feature importance analyzed

**Performance:**
- Efficient SQL queries
- Fast feature retrieval
- Scalable architecture

---

## Slide 27: Future Enhancements

1. **Real-time Feature Updates**
   - Implement Snowflake Tasks for automated refresh
   - Stream processing for live updates

2. **Feature Monitoring**
   - Track feature distributions
   - Detect feature drift
   - Alert on anomalies

3. **Advanced Features**
   - Embedding features
   - Interaction features
   - Polynomial features

4. **MLOps Integration**
   - Model versioning
   - Automated retraining
   - A/B testing framework

---

## Slide 28: Key Takeaways

1. **Feature Engineering is Critical**
   - Significantly impacts model performance
   - Requires domain knowledge
   - Iterative process

2. **Snowflake is Powerful for ML**
   - Efficient data processing
   - SQL-based feature engineering
   - Easy integration

3. **Feature Stores Solve Real Problems**
   - Consistency between training and production
   - Feature reusability
   - Version control

4. **Complete Pipeline Works**
   - Extract → Transform → Load → Serve
   - End-to-end implementation
   - Production-ready architecture

---

## Slide 29: Conclusion

**What We Built:**
- Complete feature engineering pipeline
- Snowflake-based data processing
- Feature Store implementation
- ML model integration

**Key Achievements:**
- 30+ engineered features
- Centralized feature management
- Reproducible ML pipeline
- Scalable architecture

**Ready for Production:**
- Well-documented code
- Best practices implemented
- Version control in place
- Monitoring capabilities

---

## Slide 30: Questions & Thank You

**Questions?**

**Contact:**
- GitHub Repository: [Your Repository Link]
- Video Walkthrough: [Your Video Link]

**Thank You!**

---

## Appendix: SQL Script Execution Order

1. `01_setup_database.sql` - Create database and tables
2. `02_sample_data.sql` - Insert sample data
3. `03_extract_raw_data.sql` - Extract raw data (optional, for verification)
4. `04_feature_engineering.sql` - Create feature engineering views
5. `05_feature_store_setup.sql` - Create and populate Feature Store
6. `06_retrieve_features.sql` - Retrieve features for ML (examples)

---

## Appendix: Python Scripts Usage

**Connection Test:**
```bash
python scripts/snowflake_connection.py
```

**Feature Store Operations:**
```bash
python scripts/feature_store_manager.py
```

**Model Training:**
```bash
python scripts/ml_model_training.py
```

---

## Appendix: Configuration

**Setup Steps:**
1. Copy `config/snowflake_config.json.example` to `config/snowflake_config.json`
2. Fill in your Snowflake credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Execute SQL scripts in Snowflake
5. Run Python scripts for ML integration

