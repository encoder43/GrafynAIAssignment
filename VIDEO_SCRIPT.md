# Video Walkthrough Script (15 minutes)

## Introduction (1 minute)

**Script:**
"Hello, and welcome to this walkthrough of the Feature Engineering project using Snowflake and Feature Stores. This project demonstrates a complete ML pipeline from data extraction to model training.

I'll be showing you:
- How we set up Snowflake for data storage
- Feature engineering techniques
- Feature Store implementation
- ML model integration

Let's get started!"

---

## Part 1: Project Overview (1 minute)

**Script:**
"First, let me show you the project structure. We have:
- Documentation explaining concepts
- SQL scripts for Snowflake operations
- Python scripts for Feature Store integration
- Configuration files

The architecture follows an ETL pattern:
- Extract data from Snowflake
- Transform through feature engineering
- Load into Feature Store
- Serve features for ML models"

**Action:** Show project folder structure

---

## Part 2: Snowflake Setup (2 minutes)

**Script:**
"Let's start with Snowflake setup. I've created a database called FEATURE_ENGINEERING_DB with three main schemas:
- RAW_DATA for source tables
- FEATURE_STORE for computed features
- ML_MODELS for model artifacts

Here are our source tables:
- Customers table with demographics
- Products table with product information
- Sales table with transaction data"

**Action:**
1. Open Snowflake Web UI
2. Show database structure
3. Execute `sql/01_setup_database.sql`
4. Show tables created

**Script:**
"Now let's insert sample data. We have 10 customers, 10 products, and 30 sales transactions spanning several months."

**Action:** Execute `sql/02_sample_data.sql` and show data

---

## Part 3: Feature Engineering (4 minutes)

**Script:**
"Now for the core part - feature engineering. We'll create various types of features:

First, temporal features - extracting day of week, month, and creating derived features like is_weekend."

**Action:** Show and execute temporal features query from `sql/04_feature_engineering.sql`

**Script:**
"Next, customer aggregation features. We calculate:
- Total purchases and spending
- Average purchase amounts
- Days since last purchase
- Customer lifetime metrics"

**Action:** Show customer aggregations view

**Script:**
"Rolling window features capture recent trends:
- 7-day rolling averages
- 30-day rolling sums
- Cumulative totals"

**Action:** Show rolling window features

**Script:**
"Category features encode customer preferences:
- Purchase counts per category
- Binary flags for category preferences
- Spending per category"

**Action:** Show category features

---

## Part 4: Feature Store Implementation (3 minutes)

**Script:**
"Now let's set up the Feature Store. This is where we store all computed features in a centralized location."

**Action:** Execute `sql/05_feature_store_setup.sql`

**Script:**
"The Feature Store table contains:
- Customer demographics
- Purchase behavior features
- Temporal features
- Category preferences
- Rolling window features
- Feature versioning for tracking changes"

**Action:** Show Feature Store table structure and data

**Script:**
"We also create a view for latest features, which automatically gets the most recent feature set for each customer. This ensures we always use current features for predictions."

**Action:** Show latest_customer_features view

**Script:**
"For training, we can retrieve features with point-in-time correctness. This prevents data leakage by ensuring we only use features available at that time."

**Action:** Show point-in-time query example

---

## Part 5: Python Integration (2 minutes)

**Script:**
"Now let's see how Python integrates with our Feature Store. We have three main scripts:
- snowflake_connection.py for database connectivity
- feature_store_manager.py for feature operations
- ml_model_training.py for model training"

**Action:** Show Python scripts

**Script:**
"Let's test the connection and retrieve features."

**Action:** Run `python scripts/snowflake_connection.py`

**Script:**
"Now let's use the Feature Store manager to get features for training."

**Action:** Run `python scripts/feature_store_manager.py` and show output

---

## Part 6: ML Model Training (3 minutes)

**Script:**
"Finally, let's train ML models using features from our Feature Store. We'll train:
- A regression model to predict total spending
- A classification model to predict customer segment"

**Action:** Run `python scripts/ml_model_training.py`

**Script:**
"As you can see, the model training:
- Retrieves features from the Feature Store
- Prepares and encodes the data
- Splits into train and test sets
- Trains Random Forest models
- Evaluates performance

The regression model shows good performance with R² scores, and we can see which features are most important."

**Action:** Show model results and feature importance

**Script:**
"We can also make predictions for individual customers using their latest features from the Feature Store."

**Action:** Show prediction example

---

## Part 7: Results and Conclusion (1 minute)

**Script:**
"To summarize what we've built:
- Complete feature engineering pipeline in Snowflake
- Centralized Feature Store with versioning
- Python integration for ML workflows
- Trained models using Feature Store features

Key achievements:
- 30+ engineered features
- Consistent feature definitions
- Reproducible ML pipeline
- Production-ready architecture

The Feature Store ensures:
- Features are consistent between training and production
- We can version and track feature changes
- Features are reusable across multiple models
- Point-in-time correctness prevents data leakage

Thank you for watching! The complete code and documentation are available in the GitHub repository."

**Action:** Show repository link and final summary slide

---

## Tips for Recording

1. **Preparation:**
   - Test all scripts beforehand
   - Have Snowflake account ready
   - Prepare sample queries to show

2. **Recording:**
   - Use screen recording software (OBS, Zoom, etc.)
   - Ensure good audio quality
   - Show your face in a corner (as required)
   - Keep code readable (zoom in if needed)

3. **Pacing:**
   - Don't rush through explanations
   - Pause at key concepts
   - Show actual results, not just code

4. **Editing:**
   - Trim unnecessary pauses
   - Add text overlays for key points
   - Ensure total time is under 15 minutes

5. **Upload:**
   - Upload to Google Drive or Microsoft OneDrive
   - Make sure link is shareable
   - Test the link before submission

