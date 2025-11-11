# Using Snowflake for Data Storage & Processing

## Introduction to Snowflake

Snowflake is a cloud-based data platform that provides a fully managed data warehouse solution. It separates compute and storage, allowing for independent scaling and cost optimization. Snowflake supports structured and semi-structured data, making it ideal for modern data engineering and ML workflows.

## Key Features of Snowflake

1. **Cloud-Native Architecture**: Built for the cloud with automatic scaling
2. **Separation of Storage and Compute**: Independent scaling of resources
3. **Multi-Cluster Architecture**: Support for concurrent workloads
4. **Time Travel**: Access historical data versions
5. **Zero-Copy Cloning**: Instant database cloning without data duplication
6. **Semi-Structured Data Support**: Native JSON, XML, Parquet support
7. **Secure Data Sharing**: Share data without copying

## Snowflake Architecture

### Storage Layer
- Stores data in compressed, columnar format
- Automatically manages data organization and optimization
- Supports multiple cloud providers (AWS, Azure, GCP)

### Compute Layer
- Virtual warehouses for processing queries
- Auto-scaling and auto-suspend capabilities
- Multiple warehouses for different workloads

### Cloud Services Layer
- Authentication and authorization
- Query optimization and metadata management
- Infrastructure management

## Data Storage in Snowflake

### Structured Data
Snowflake excels at storing structured relational data:
- Tables with defined schemas
- ACID transactions
- Primary and foreign key constraints
- Indexes and clustering keys

### Semi-Structured Data
Native support for:
- **JSON**: Store and query JSON documents
- **XML**: XML data processing
- **Parquet**: Columnar format for analytics
- **Avro**: Schema evolution support

### Example: Storing Semi-Structured Data

```sql
-- Create table with variant column for JSON
CREATE TABLE customer_data (
    customer_id VARCHAR,
    profile VARIANT,
    created_at TIMESTAMP
);

-- Insert JSON data
INSERT INTO customer_data VALUES (
    'C001',
    PARSE_JSON('{"name": "John", "age": 30, "city": "NYC"}'),
    CURRENT_TIMESTAMP()
);

-- Query JSON data
SELECT 
    customer_id,
    profile:name::STRING AS name,
    profile:age::INT AS age,
    profile:city::STRING AS city
FROM customer_data;
```

## SQL Queries for Data Extraction and Preprocessing

### 1. Basic Data Extraction

```sql
-- Extract all columns from a table
SELECT * FROM sales_data;

-- Extract specific columns with filtering
SELECT 
    customer_id,
    product_id,
    sale_amount,
    sale_date
FROM sales_data
WHERE sale_date >= '2024-01-01'
    AND sale_amount > 100;
```

### 2. Data Aggregation

```sql
-- Daily sales aggregation
SELECT 
    DATE_TRUNC('day', sale_date) AS sale_day,
    COUNT(*) AS transaction_count,
    SUM(sale_amount) AS total_sales,
    AVG(sale_amount) AS avg_sale_amount,
    MAX(sale_amount) AS max_sale,
    MIN(sale_amount) AS min_sale
FROM sales_data
GROUP BY DATE_TRUNC('day', sale_date)
ORDER BY sale_day DESC;
```

### 3. Window Functions for Time-Series Features

Window functions are super useful for creating features. They let you calculate things like "average of last 7 days" or "total so far" without grouping.

**Rolling Average (7-day window)**

```sql
AVG(sale_amount) OVER (
    PARTITION BY customer_id 
    ORDER BY sale_date 
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
) AS avg_7day_sales
```

**What this does**: For each row, it looks at the current row plus the 6 rows before it (7 total), and calculates the average.

**Real example from our project**: We use a 30-day window instead:
```sql
AVG(amount_filled) AS avg_tx_amount_30d
FROM tx_cleaned
WHERE transaction_ts >= DATEADD(day, -30, CURRENT_TIMESTAMP())
```

This gives us the average transaction amount in the last 30 days. For cust01, that's (120.50 + 40.00 + 75.00) / 3 = $78.50.

**Cumulative Sum**

```sql
SUM(sale_amount) OVER (
    PARTITION BY customer_id 
    ORDER BY sale_date 
    ROWS UNBOUNDED PRECEDING
) AS cumulative_sales
```

This adds up all sales from the beginning until the current row. "UNBOUNDED PRECEDING" means "all rows before this one".

### 4. Feature Engineering Queries

```sql
-- Extract temporal features
SELECT 
    customer_id,
    sale_date,
    EXTRACT(YEAR FROM sale_date) AS sale_year,
    EXTRACT(MONTH FROM sale_date) AS sale_month,
    EXTRACT(DAY FROM sale_date) AS sale_day,
    EXTRACT(DAYOFWEEK FROM sale_date) AS day_of_week,
    EXTRACT(QUARTER FROM sale_date) AS quarter,
    CASE 
        WHEN EXTRACT(DAYOFWEEK FROM sale_date) IN (1, 7) THEN 'Weekend'
        ELSE 'Weekday'
    END AS day_type
FROM sales_data;

-- Calculate time differences
SELECT 
    customer_id,
    sale_date,
    LAG(sale_date) OVER (
        PARTITION BY customer_id 
        ORDER BY sale_date
    ) AS previous_sale_date,
    DATEDIFF('day', 
        LAG(sale_date) OVER (
            PARTITION BY customer_id 
            ORDER BY sale_date
        ), 
        sale_date
    ) AS days_since_last_purchase
FROM sales_data;
```

### 5. Data Preprocessing

**Handling Missing Values**

In our project, we handle missing amounts like this:
```sql
CASE WHEN amount IS NULL THEN 0.0 ELSE amount END as amount_filled
```

This is simple - if amount is missing, use 0.0. In production, you might use the median instead:
```sql
COALESCE(amount, MEDIAN(amount) OVER ()) AS amount_filled
```

**Normalization (Min-Max)**

The formula is:
```
normalized = (value - min) / (max - min)
```

In SQL:
```sql
(sale_amount - MIN(sale_amount) OVER ()) / 
(MAX(sale_amount) OVER () - MIN(sale_amount) OVER ()) AS normalized_amount
```

**Real example**: If amounts are $15, $85, $200, $300:
- Min = $15, Max = $300
- $85 normalized = (85 - 15) / (300 - 15) = 0.246

**Standardization (Z-score)**

This is what we actually use in our ML models:
```sql
(sale_amount - AVG(sale_amount) OVER ()) / 
STDDEV(sale_amount) OVER () AS standardized_amount
```

The formula: `(x - mean) / std`

**Real example**: Same amounts $15, $85, $200, $300:
- Mean = 150
- Std ≈ 108.5
- $85 standardized = (85 - 150) / 108.5 = -0.60 (below average)

### 6. Categorical Encoding

```sql
-- One-hot encoding simulation
SELECT 
    customer_id,
    CASE WHEN category = 'Electronics' THEN 1 ELSE 0 END AS is_electronics,
    CASE WHEN category = 'Clothing' THEN 1 ELSE 0 END AS is_clothing,
    CASE WHEN category = 'Food' THEN 1 ELSE 0 END AS is_food
FROM product_data;

-- Label encoding
SELECT 
    category,
    DENSE_RANK() OVER (ORDER BY category) - 1 AS category_encoded
FROM product_data;
```

## Snowflake Integration with ML Pipelines

### 1. Data Extraction for Training

In our project, we extract features from the Feature Store, but here's how you'd do it directly from transactions:

```sql
-- Extract features for model training
CREATE OR REPLACE VIEW customer_agg_30d AS
SELECT 
    customer_id,
    AVG(amount_filled) AS avg_tx_amount_30d,
    COUNT(*) AS tx_count_30d,
    SUM(high_value_flag) AS high_value_tx_count_30d
FROM tx_cleaned
WHERE transaction_ts >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY customer_id;
```

**What this does**:
- Groups by customer_id
- Calculates average amount (using AVG)
- Counts transactions (using COUNT)
- Sums high-value flags (using SUM)

**Real numbers**: For cust01 with transactions $120.50, $40.00, $75.00:
- avg_tx_amount_30d = (120.50 + 40.00 + 75.00) / 3 = $78.50
- tx_count_30d = 3
- high_value_tx_count_30d = 1 (only $120.50 is ≥ $100)

### 2. Using Snowflake with Python

```python
from snowflake_connection import SnowflakeConnection

# Connect to Snowflake using config file
sf = SnowflakeConnection('config/snowflake_config.json')
sf.connect()

# Execute query and get pandas DataFrame
query = """
SELECT * FROM FEAT_DB.FEAT_SCHEMA.latest_features
WHERE entity_id IS NOT NULL
"""
df = sf.execute_query(query)

# Close connection
sf.close()
```

**Configuration File (`config/snowflake_config.json`):**
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

### 3. Snowflake Tasks for Automated Feature Engineering

```sql
-- Create a task to refresh features daily
CREATE OR REPLACE TASK refresh_features
    WAREHOUSE = COMPUTE_WH
    SCHEDULE = 'USING CRON 0 2 * * * UTC'
AS
    INSERT INTO feature_store.features
    SELECT * FROM training_features;
```

### 4. Stored Procedures for Feature Computation

```sql
-- Create stored procedure for feature engineering
CREATE OR REPLACE PROCEDURE compute_customer_features()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    -- Feature engineering logic
    CREATE OR REPLACE TABLE feature_store.customer_features AS
    SELECT 
        customer_id,
        -- Aggregated features
        COUNT(*) AS purchase_count,
        SUM(amount) AS total_spent,
        -- Temporal features
        DATEDIFF('day', MIN(purchase_date), MAX(purchase_date)) AS customer_lifetime_days
    FROM sales
    GROUP BY customer_id;
    
    RETURN 'Features computed successfully';
END;
$$;
```

## Best Practices for Snowflake ML Integration

1. **Use Views for Feature Definitions**: Create views for reusable feature logic
2. **Materialize Expensive Features**: Store computed features in tables for performance
3. **Partition Large Tables**: Use clustering keys for better query performance
4. **Leverage Time Travel**: Access historical data versions for feature versioning
5. **Use Tasks for Automation**: Schedule feature refresh jobs
6. **Optimize Warehouse Size**: Right-size warehouses for workload
7. **Monitor Query Performance**: Use query profiling to optimize slow queries

## Advantages for ML Workflows

1. **Scalability**: Handle large datasets without performance degradation
2. **SQL Interface**: Familiar SQL syntax for data transformations
3. **Integration**: Easy integration with Python, R, and other ML tools
4. **Cost Efficiency**: Pay only for compute time used
5. **Data Governance**: Built-in security and access controls
6. **Versioning**: Time Travel for feature versioning
7. **Real-time**: Support for streaming data with Snowpipe

