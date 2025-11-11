# Introduction to Feature Engineering

## What is Feature Engineering?

Think of feature engineering like preparing ingredients before cooking. You could throw raw vegetables into a pot, but chopping them properly makes a huge difference in the final dish. Similarly, feature engineering takes your raw data and transforms it into something that machine learning models can actually use effectively.

For example, instead of just giving a model the raw transaction dates, you might create features like "day of week" or "days since last purchase". These transformed features often help models make much better predictions.

## Why Does Feature Engineering Matter?

Here's the thing - most machine learning algorithms are pretty dumb. They can't automatically figure out that "days since last purchase" is more useful than just "last purchase date". You need to give them the right features.

**Real example from our project**: We have customer transactions with amounts like $120.50, $40.00, $300.00. Instead of just using these raw amounts, we created:
- Average transaction amount over 30 days
- Count of high-value transactions (≥ $100)
- Total transaction count

These engineered features help our model understand customer behavior patterns much better than raw transaction amounts would.

## Types of Feature Engineering Techniques

### 1. Normalization and Standardization

When you have features with very different scales, some algorithms get confused. Imagine trying to compare someone's age (maybe 30) with their annual income (maybe $50,000). The numbers are so different that the algorithm might ignore age completely.

**Normalization (Min-Max Scaling)**

This squishes everything into a 0 to 1 range. Here's the formula:

```
normalized_value = (x - min) / (max - min)
```

**Real example**: Let's say we have transaction amounts: $15, $85, $200, $300
- Min = $15, Max = $300
- $85 normalized = (85 - 15) / (300 - 15) = 70 / 285 = 0.246
- $200 normalized = (200 - 15) / (300 - 15) = 185 / 285 = 0.649

Now all values are between 0 and 1, making them easier to compare.

**Standardization (Z-score)**

This centers the data around zero with a standard deviation of 1. The formula is:

```
standardized_value = (x - mean) / std
```

**Real example**: Same transaction amounts: $15, $85, $200, $300
- Mean = (15 + 85 + 200 + 300) / 4 = 150
- Standard deviation ≈ 108.5 (calculated from variance)
- $85 standardized = (85 - 150) / 108.5 = -0.60
- $200 standardized = (200 - 150) / 108.5 = 0.46

Negative values mean below average, positive means above average. This is what we use in our ML models - it helps algorithms like Random Forest work better.

### 2. Encoding Techniques

Machine learning models need numbers, not text. So when you have categories like "web", "app", "pos" (point of sale), you need to convert them.

**One-Hot Encoding**

Each category becomes its own column with 1s and 0s. If you have 3 categories, you get 3 columns.

**Real example from our data**: Transaction channels are "web", "app", "pos"
- "web" → [1, 0, 0]
- "app" → [0, 1, 0]  
- "pos" → [0, 0, 1]

The problem? If you have 50 different channels, you get 50 columns. That's a lot of columns.

**Label Encoding**

Just assign numbers: web=0, app=1, pos=2. Simple, but be careful - the model might think pos (2) is "more" than app (1), which doesn't make sense for categories.

**Target Encoding**

This is clever - you use the average target value for each category. Say you're predicting transaction amount:
- Average for "web" transactions = $95
- Average for "app" transactions = $50
- Average for "pos" transactions = $180

Then you encode: web=95, app=50, pos=180. This captures useful information while keeping just one column.

### 3. Time-Based Aggregations

Time is gold for understanding behavior. People shop differently on weekends, during holidays, or after payday.

**Temporal Features**

Extract useful time information from dates:
- Day of week (1=Sunday, 7=Saturday) - helps catch weekend shopping patterns
- Month (1-12) - seasonal patterns
- Hour of day - morning vs evening shoppers

**Real example from our project**: We extract `DAYOFWEEK(transaction_ts)` to see if customers shop more on weekends.

**Rolling Statistics**

This is where it gets interesting. Instead of looking at all historical data, you look at a "window" of recent data.

**30-Day Average (what we use in our project)**

The formula is:
```
avg_tx_amount_30d = (sum of all amounts in last 30 days) / (count of transactions in last 30 days)
```

**Real example**: Customer cust01 has these transactions in the last 30 days:
- Oct 10: $120.50
- Oct 12: $40.00
- Sep 11: $75.00

Average = (120.50 + 40.00 + 75.00) / 3 = $235.50 / 3 = **$78.50**

This tells us their recent spending pattern, which is more useful than their lifetime average.

**Rolling Sum**

Sometimes you want totals, not averages:
```
sum_30day = sum of all amounts in last 30 days
```

For cust01: $120.50 + $40.00 + $75.00 = **$235.50** total in last 30 days.

### 4. Aggregation Features

Aggregations summarize multiple data points into single numbers. This is what we do most in our project.

**Mean (Average)**

The classic average. Formula:
```
mean = sum of all values / count of values
```

**Real example**: Customer cust02's transactions: $300, $25, $150
- Mean = (300 + 25 + 150) / 3 = $158.33

**Count**

Simple but powerful - how many times did something happen?

**Real example**: In our project, `tx_count_30d` counts transactions in last 30 days:
- cust01: 3 transactions
- cust02: 3 transactions
- cust03: 2 transactions

**Sum**

Total of all values:
```
sum = value1 + value2 + ... + valueN
```

**Real example**: `high_value_tx_count_30d` counts how many transactions were ≥ $100:
- cust01: 1 high-value transaction ($120.50)
- cust02: 2 high-value transactions ($300, $150)
- cust03: 0 high-value transactions

This binary flag (≥ $100 = 1, < $100 = 0) is created with:
```
high_value_flag = CASE WHEN amount >= 100 THEN 1 ELSE 0 END
```

Then we sum these flags to get the count.

### 5. Interaction Features

**Polynomial Features**
- Create combinations of features
- Example: x1 * x2, x1², x2²

**Cross Features**
- Combine categorical features
- Example: Country × Product Category

### 6. Binning and Discretization

**Equal-Width Binning**
- Divide continuous variables into equal-width intervals
- Example: Age groups [0-20, 21-40, 41-60, 61+]

**Equal-Frequency Binning**
- Divide into bins with equal number of observations
- Useful for skewed distributions

### 7. Missing Value Handling

**Imputation**
- Mean/median/mode imputation
- Forward fill, backward fill
- Model-based imputation

**Indicator Variables**
- Create binary flags for missing values
- Helps model learn from missingness patterns

### 8. Feature Selection

**Statistical Methods**
- Correlation analysis
- Chi-square test
- Mutual information

**Model-Based**
- Feature importance from tree models
- L1 regularization (Lasso)
- Recursive feature elimination

## How We Actually Do It (Our Workflow)

Let me walk you through what we did in this project:

**Step 1: Look at the raw data**
We started with a `customer_transactions` table with columns like transaction_id, customer_id, transaction_ts, amount, channel, and metadata (JSON).

**Step 2: Clean it up**
We created `tx_cleaned` table where we:
- Handled missing amounts (set to 0.0)
- Extracted promo codes from JSON: `metadata:promo::STRING`
- Created a high-value flag: `CASE WHEN amount >= 100 THEN 1 ELSE 0 END`

**Step 3: Create aggregations**
We built `customer_agg_30d` view that calculates:
- `avg_tx_amount_30d = AVG(amount_filled)` - average spending
- `tx_count_30d = COUNT(*)` - how many transactions
- `high_value_tx_count_30d = SUM(high_value_flag)` - count of big purchases

**Step 4: Store in Feature Store**
We put these features in a key-value table so we can:
- Track changes over time
- Query features for any point in time
- Add new features without changing the schema

**Step 5: Use for ML**
When training models, we retrieve these features, scale them (using StandardScaler), and feed them to Random Forest models.

## Best Practices

1. **Avoid Data Leakage**: Don't use future information to predict past
2. **Maintain Consistency**: Apply same transformations to train and test
3. **Document Transformations**: Keep track of all feature engineering steps
4. **Version Control**: Version features for reproducibility
5. **Monitor Drift**: Track feature distributions for model degradation
6. **Domain Knowledge**: Incorporate business logic and expertise
7. **Iterative Process**: Continuously refine features based on model performance

## Challenges in Feature Engineering

1. **Time-Consuming**: Requires domain expertise and experimentation
2. **Data Quality**: Poor quality data leads to poor features
3. **Scalability**: Feature engineering at scale can be complex
4. **Maintenance**: Features need to be updated as data changes
5. **Reproducibility**: Ensuring consistent transformations across environments

## Feature Stores: The Solution

Feature Stores address many challenges by:
- Centralizing feature definitions
- Ensuring consistency across training and serving
- Versioning features for reproducibility
- Enabling feature reuse across models
- Providing low-latency feature serving

