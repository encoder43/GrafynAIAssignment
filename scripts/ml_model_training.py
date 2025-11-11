"""
ML Model Training using Features from Feature Store
Demonstrates how to retrieve features and train a model
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score, classification_report
from feature_store_manager import FeatureStoreManager
import os
import warnings
warnings.filterwarnings('ignore')



class MLModelTrainer:
    """Trains ML models using features from Feature Store"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ML Model Trainer
        
        Args:
            config_path: Path to Snowflake config file
        """
        self.fs_manager = FeatureStoreManager(config_path)
        self.label_encoders = {}
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for ML model
        
        Args:
            df: Raw feature DataFrame
            
        Returns:
            Processed DataFrame ready for modeling
        """
        df = df.copy()
        
        # Handle missing values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
        
        return df
    
    def train_regression_model(self, 
                              target_column: str = 'avg_tx_amount_30d',
                              test_size: float = 0.2,
                              random_state: int = 42) -> Dict:
        """
        Train a regression model to predict a continuous target
        
        Args:
            target_column: Name of target column (must exist in data)
            test_size: Proportion of data for testing
            random_state: Random seed
            
        Returns:
            Dictionary with model and metrics
        """
        # Get features from Feature Store
        print("Retrieving features from Feature Store...")
        df = self.fs_manager.get_features_for_training()
        print(f"Retrieved {len(df)} records")
        
        if len(df) == 0:
            raise ValueError("No features found in Feature Store. Run sql/snowflake_feature_engineering.sql first.")
        
        # Prepare features
        df = self.prepare_features(df)
        
        # If target doesn't exist, create a synthetic one for demonstration
        if target_column not in df.columns:
            print(f"Target column '{target_column}' not found. Creating synthetic target...")
            # Create synthetic target based on available features
            if 'avg_tx_amount_30d' in df.columns:
                df[target_column] = df['avg_tx_amount_30d'] + np.random.normal(0, 10, len(df))
            elif 'tx_count_30d' in df.columns:
                df[target_column] = df['tx_count_30d'] * 50 + np.random.normal(0, 20, len(df))
            else:
                # Use first numeric column as base
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    base_col = numeric_cols[0]
                    df[target_column] = df[base_col] * 10 + np.random.normal(0, 50, len(df))
                else:
                    raise ValueError(f"Cannot create synthetic target. No numeric features available.")
        
        # Select feature columns (exclude entity_id and target)
        exclude_cols = ['entity_id', target_column]
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # If we only have one feature and it's the target, create additional features
        if len(feature_cols) == 0:
            print("Warning: No features available after excluding target. Creating synthetic features...")
            # Create synthetic features based on entity_id or other available data
            df['entity_id_numeric'] = pd.Categorical(df['entity_id']).codes
            # Use a simple hash function (avoiding conflict with built-in hash)
            def simple_hash(s):
                return abs(hash(str(s))) % 1000
            df['entity_id_hash'] = df['entity_id'].apply(simple_hash)
            feature_cols = ['entity_id_numeric', 'entity_id_hash']
        
        X = df[feature_cols].select_dtypes(include=[np.number])
        y = df[target_column]
        
        # Remove rows with missing target
        mask = ~y.isna()
        X = X[mask]
        y = y[mask]
        
        if len(X) == 0:
            raise ValueError("No valid data for training after filtering")
        
        # Check if we have any numeric features
        if X.shape[1] == 0:
            raise ValueError("No numeric features available for training. Need at least one feature column.")
        
        # Split data
        if len(X) < 2:
            raise ValueError("Not enough data for train/test split. Need at least 2 records.")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        # Create a new scaler for this model
        scaler = StandardScaler()
        
        # Scale features (only if we have features)
        if X_train.shape[1] > 0:
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
        else:
            raise ValueError("No features to scale. Cannot train model.")
        
        # Train model
        print(f"\nTraining Random Forest Regressor to predict '{target_column}'...")
        model = RandomForestRegressor(n_estimators=100, random_state=random_state, n_jobs=-1)
        model.fit(X_train_scaled, y_train)
        
        # Predictions
        y_train_pred = model.predict(X_train_scaled)
        y_test_pred = model.predict(X_test_scaled)
        
        # Metrics
        train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
        test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
        train_r2 = r2_score(y_train, y_train_pred)
        test_r2 = r2_score(y_test, y_test_pred)
        
        print(f"\nModel Performance:")
        print(f"Train RMSE: {train_rmse:.2f}")
        print(f"Test RMSE: {test_rmse:.2f}")
        print(f"Train R²: {train_r2:.4f}")
        print(f"Test R²: {test_r2:.4f}")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"\nTop 10 Most Important Features:")
        print(feature_importance.head(10))
        
        return {
            'model': model,
            'scaler': scaler,
            'feature_columns': X.columns.tolist(),
            'train_rmse': train_rmse,
            'test_rmse': test_rmse,
            'train_r2': train_r2,
            'test_r2': test_r2,
            'feature_importance': feature_importance,
            'X_test': X_test,
            'y_test': y_test,
            'y_test_pred': y_test_pred
        }
    
    def train_classification_model(self,
                                  target_column: str = 'high_value_customer',
                                  test_size: float = 0.2,
                                  random_state: int = 42) -> Dict:
        """
        Train a classification model
        
        Args:
            target_column: Name of target column (will be created if doesn't exist)
            test_size: Proportion of data for testing
            random_state: Random seed
            
        Returns:
            Dictionary with model and metrics
        """
        # Get features from Feature Store
        print("Retrieving features from Feature Store...")
        df = self.fs_manager.get_features_for_training()
        print(f"Retrieved {len(df)} records")
        
        if len(df) == 0:
            raise ValueError("No features found in Feature Store. Run sql/snowflake_feature_engineering.sql first.")
        
        # Prepare features
        df = self.prepare_features(df)
        
        # Create target if it doesn't exist
        if target_column not in df.columns:
            print(f"Target column '{target_column}' not found. Creating binary classification target...")
            # Create synthetic binary classification target based on avg_tx_amount_30d
            if 'avg_tx_amount_30d' in df.columns:
                median_value = df['avg_tx_amount_30d'].median()
                df[target_column] = (df['avg_tx_amount_30d'] > median_value).astype(int)
                df[target_column] = df[target_column].map({0: 'Low Value', 1: 'High Value'})
            else:
                # Use first numeric column
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    base_col = numeric_cols[0]
                    median_value = df[base_col].median()
                    df[target_column] = (df[base_col] > median_value).astype(int)
                    df[target_column] = df[target_column].map({0: 'Low Value', 1: 'High Value'})
                else:
                    raise ValueError("Cannot create classification target. No numeric features available.")
        
        # Select feature columns
        exclude_cols = ['entity_id', target_column]
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # If we only have one feature and it's the target, create additional features
        if len(feature_cols) == 0:
            print("Warning: No features available after excluding target. Creating synthetic features...")
            # Create synthetic features based on entity_id or other available data
            df['entity_id_numeric'] = pd.Categorical(df['entity_id']).codes
            # Use a simple hash function (avoiding conflict with built-in hash)
            def simple_hash(s):
                return abs(hash(str(s))) % 1000
            df['entity_id_hash'] = df['entity_id'].apply(simple_hash)
            feature_cols = ['entity_id_numeric', 'entity_id_hash']
        
        X = df[feature_cols].select_dtypes(include=[np.number])
        y = df[target_column]
        
        # Remove rows with missing target
        mask = ~y.isna()
        X = X[mask]
        y = y[mask]
        
        if len(X) == 0:
            raise ValueError("No valid data for training after filtering")
        
        # Check if we have any numeric features
        if X.shape[1] == 0:
            raise ValueError("No numeric features available for training. Need at least one feature column.")
        
        # Encode target if needed
        if y.dtype == 'object':
            if target_column not in self.label_encoders:
                self.label_encoders[target_column] = LabelEncoder()
                y_encoded = self.label_encoders[target_column].fit_transform(y)
            else:
                y_encoded = self.label_encoders[target_column].transform(y)
        else:
            y_encoded = y
        
        if len(X) < 2:
            raise ValueError("Not enough data for train/test split. Need at least 2 records.")
        
        # Split data
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_encoded, test_size=test_size, random_state=random_state, stratify=y_encoded
            )
        except ValueError:
            # If stratification fails (e.g., only one class), use regular split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_encoded, test_size=test_size, random_state=random_state
            )
        
        # Create a new scaler for this model
        scaler = StandardScaler()
        
        # Scale features (only if we have features)
        if X_train.shape[1] > 0:
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
        else:
            raise ValueError("No features to scale. Cannot train model.")
        
        # Train model
        print(f"\nTraining Random Forest Classifier to predict '{target_column}'...")
        model = RandomForestClassifier(n_estimators=100, random_state=random_state, n_jobs=-1)
        model.fit(X_train_scaled, y_train)
        
        # Predictions
        y_train_pred = model.predict(X_train_scaled)
        y_test_pred = model.predict(X_test_scaled)
        
        # Metrics
        train_accuracy = accuracy_score(y_train, y_train_pred)
        test_accuracy = accuracy_score(y_test, y_test_pred)
        
        print(f"\nModel Performance:")
        print(f"Train Accuracy: {train_accuracy:.4f}")
        print(f"Test Accuracy: {test_accuracy:.4f}")
        
        print(f"\nClassification Report:")
        # Get unique classes in test set
        unique_test_classes = np.unique(y_test)
        unique_pred_classes = np.unique(y_test_pred)
        all_classes = np.unique(np.concatenate([unique_test_classes, unique_pred_classes]))
        
        if target_column in self.label_encoders:
            all_target_names = self.label_encoders[target_column].classes_
            # Only include target names for classes that exist in test/pred
            target_names = [all_target_names[i] for i in all_classes if i < len(all_target_names)]
        else:
            target_names = [f'Class {i}' for i in all_classes]
        
        # Only print classification report if we have multiple classes
        if len(all_classes) > 1:
            print(classification_report(y_test, y_test_pred, target_names=target_names, labels=all_classes))
        else:
            print(f"Only one class present in test set: {target_names[0] if target_names else all_classes[0]}")
            print("Classification report requires at least 2 classes.")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"\nTop 10 Most Important Features:")
        print(feature_importance.head(10))
        
        return {
            'model': model,
            'scaler': scaler,
            'feature_columns': X.columns.tolist(),
            'train_accuracy': train_accuracy,
            'test_accuracy': test_accuracy,
            'feature_importance': feature_importance,
            'X_test': X_test,
            'y_test': y_test,
            'y_test_pred': y_test_pred
        }
    
    def predict_for_entity(self, entity_id: str, model: object, 
                            feature_columns: List[str], scaler: Optional[StandardScaler] = None) -> Dict:
        """
        Make prediction for a single entity
        
        Args:
            entity_id: Entity ID (customer ID)
            model: Trained model
            feature_columns: List of feature column names used during training
            scaler: Scaler used during training (required for proper feature scaling)
            
        Returns:
            Dictionary with prediction
        """
        if scaler is None:
            raise ValueError("Scaler is required for prediction. Pass the scaler from training results.")
        # Get features for entity
        features_df = self.fs_manager.get_latest_features([entity_id])
        
        if len(features_df) == 0:
            raise ValueError(f"Entity {entity_id} not found in Feature Store")
        
        # Prepare features
        features_df = self.prepare_features(features_df)
        
        # Create a DataFrame with the exact feature columns used during training
        # Fill missing columns with 0 (mean imputation for missing features)
        # Ensure columns are in the exact order as feature_columns
        feature_values = []
        for col in feature_columns:
            if col in features_df.columns:
                val = features_df[col].iloc[0]
                # Convert to numeric, use 0.0 if NaN or non-numeric
                try:
                    val = float(val) if not pd.isna(val) else 0.0
                except (ValueError, TypeError):
                    val = 0.0
                feature_values.append(val)
            else:
                # Feature not available, use 0 as default
                feature_values.append(0.0)
        
        # Create DataFrame with exact column names and order
        X = pd.DataFrame([feature_values], columns=feature_columns)
        
        # Ensure all columns are numeric
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0.0)
        
        # Verify we have all required features
        if set(X.columns) != set(feature_columns):
            missing = set(feature_columns) - set(X.columns)
            raise ValueError(f"Missing required features: {missing}. Available: {features_df.columns.tolist()}")
        
        # Ensure columns are in the correct order
        X = X[feature_columns]
        
        # Scale features using the same scaler from training
        X_scaled = scaler.transform(X)
        
        # Predict
        prediction = model.predict(X_scaled)[0]
        
        return {
            'entity_id': entity_id,
            'prediction': prediction,
            'features_used': X.iloc[0].to_dict(),
            'all_available_features': features_df.iloc[0].to_dict()
        }
    
    def close(self):
        """Close connections"""
        self.fs_manager.close()


def main():
    """Example usage"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'snowflake_config.json')
    
    try:
        trainer = MLModelTrainer(config_path)
        
        # Train regression model
        print("=" * 60)
        print("TRAINING REGRESSION MODEL")
        print("=" * 60)
        regression_results = trainer.train_regression_model(target_column='avg_tx_amount_30d')
        
        # Train classification model
        print("\n" + "=" * 60)
        print("TRAINING CLASSIFICATION MODEL")
        print("=" * 60)
        classification_results = trainer.train_classification_model(
            target_column='high_value_customer'
        )
        
        # Example prediction for an entity
        print("\n" + "=" * 60)
        print("MAKING PREDICTION FOR ENTITY")
        print("=" * 60)
        try:
            prediction = trainer.predict_for_entity(
                'cust01',
                regression_results['model'],
                regression_results['feature_columns'],
                regression_results['scaler']
            )
            print(f"Prediction for entity cust01: {prediction['prediction']:.2f}")
            print(f"Features used: {prediction['features_used']}")
        except Exception as e:
            print(f"Could not make prediction: {e}")
            import traceback
            traceback.print_exc()
        
        trainer.close()
        
    except FileNotFoundError:
        print("Config file not found. Please create config/snowflake_config.json")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
