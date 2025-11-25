"""
Fine-Tuned Home Type Classifier

Fine-tuned RandomForest classifier for home type classification.

Baseline Model: scikit-learn RandomForestClassifier
- Best for tabular data classification (2025 best practice)
- Already proven in device-intelligence-service
- Lightweight, fast, interpretable

Model Specs:
- Algorithm: RandomForestClassifier (scikit-learn)
- Trees: 100 (lightweight for NUC)
- Max depth: 15
- Min samples split: 5
- Features: 15-20 (tabular)
- Classes: 5-10 home types
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

from .feature_extractor import HomeTypeFeatureExtractor

logger = logging.getLogger(__name__)


class FineTunedHomeTypeClassifier:
    """
    Fine-tuned RandomForest classifier for home type classification.
    
    Baseline Model: scikit-learn RandomForestClassifier
    - Best for tabular data classification (2025 best practice)
    - Already proven in device-intelligence-service
    - Lightweight, fast, interpretable
    
    Model Specs:
    - Algorithm: RandomForestClassifier (scikit-learn)
    - Trees: 100 (lightweight for NUC)
    - Max depth: 15
    - Min samples split: 5
    - Features: 15-20 (tabular)
    - Classes: 5-10 home types
    """
    
    def __init__(self, model_path: str | Path | None = None):
        """
        Initialize classifier.
        
        Args:
            model_path: Optional path to load pre-trained model
        """
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1  # Use all CPU cores
        )
        self.scaler = StandardScaler()
        self.feature_extractor = HomeTypeFeatureExtractor()
        self.is_trained = False
        self.model_version = '1.0'
        self.training_date = None
        self.feature_names = []
        self.class_names = []
        
        if model_path:
            self.load(model_path)
        
        logger.info("FineTunedHomeTypeClassifier initialized")
    
    async def train_from_synthetic_data(
        self,
        synthetic_homes: list[dict[str, Any]],
        test_size: float = 0.2,
        random_state: int = 42
    ) -> dict[str, Any]:
        """
        Train model on synthetic homes (LOCAL TRAINING, BEFORE RELEASE).
        
        Process:
        1. Load synthetic homes
        2. Extract home profiles
        3. Extract features (tabular)
        4. Generate labels
        5. Augment data (3-5 variations)
        6. Train model (scikit-learn RandomForest)
        7. Evaluate (cross-validation)
        8. Save model to models/home_type_classifier.pkl
        
        Note: This runs ONCE before release, model is included in Docker image.
        
        Args:
            synthetic_homes: List of synthetic home dictionaries
            test_size: Test set size (default: 0.2)
            random_state: Random seed (default: 42)
        
        Returns:
            Training results dictionary
        """
        logger.info(f"Training model on {len(synthetic_homes)} synthetic homes...")
        
        from .data_augmenter import TrainingDataAugmenter
        from .home_type_profiler import HomeTypeProfiler
        from .label_generator import HomeTypeLabelGenerator
        
        profiler = HomeTypeProfiler()
        label_generator = HomeTypeLabelGenerator()
        augmenter = TrainingDataAugmenter(augmentation_factor=4)
        
        # Extract profiles and labels
        profiles = []
        labels = []
        
        for home in synthetic_homes:
            try:
                # Profile home
                profile = await profiler.profile_home(
                    home_id=home.get('home_id', f"home_{len(profiles)}"),
                    devices=home.get('devices', []),
                    events=home.get('events', []),
                    areas=home.get('areas', [])
                )
                
                # Generate label
                label = label_generator.label_home_type(
                    home_metadata=home,
                    profile=profile
                )
                
                profiles.append(profile)
                labels.append(label)
                
                # Create augmented variations
                variations = augmenter.create_variations(profile, count=3)
                for variation in variations:
                    profiles.append(variation)
                    labels.append(label)
                
            except Exception as e:
                logger.error(f"Failed to process home: {e}")
                continue
        
        logger.info(f"Created {len(profiles)} training samples ({len(labels)} labels)")
        
        # Extract features
        X = []
        y = []
        
        for profile, label in zip(profiles, labels):
            try:
                features = self.feature_extractor.extract(profile)
                X.append(features)
                y.append(label)
            except Exception as e:
                logger.error(f"Failed to extract features: {e}")
                continue
        
        if not X:
            raise ValueError("No valid training samples generated")
        
        X = np.array(X)
        y = np.array(y)
        
        # Store feature names and class names
        self.feature_names = self.feature_extractor.get_feature_names()
        self.class_names = sorted(list(set(y)))
        
        logger.info(f"Feature vector shape: {X.shape}")
        logger.info(f"Classes: {self.class_names}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        logger.info("Training RandomForest classifier...")
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        self.training_date = datetime.now(timezone.utc).isoformat()
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X_train_scaled, y_train, cv=5, scoring='accuracy'
        )
        
        # Classification report
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred, labels=self.class_names)
        
        results = {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'cv_accuracy_mean': float(cv_scores.mean()),
            'cv_accuracy_std': float(cv_scores.std()),
            'classification_report': report,
            'confusion_matrix': cm.tolist(),
            'feature_names': self.feature_names,
            'class_names': self.class_names,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'model_version': self.model_version,
            'training_date': self.training_date
        }
        
        logger.info(f"✅ Model training complete:")
        logger.info(f"   Accuracy: {accuracy:.3f}")
        logger.info(f"   Precision: {precision:.3f}")
        logger.info(f"   Recall: {recall:.3f}")
        logger.info(f"   F1 Score: {f1:.3f}")
        logger.info(f"   CV Accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        
        return results
    
    def predict(self, profile: dict[str, Any]) -> dict[str, Any]:
        """
        Predict home type from profile.
        
        Args:
            profile: Home profile dictionary
        
        Returns:
            Prediction dictionary with home_type, confidence, etc.
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train_from_synthetic_data() first.")
        
        # Extract features
        features = self.feature_extractor.extract(profile)
        features_scaled = self.scaler.transform([features])
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]
        
        # Get confidence (probability of predicted class)
        class_index = self.class_names.index(prediction)
        confidence = float(probabilities[class_index])
        
        return {
            'home_type': prediction,
            'confidence': confidence,
            'method': 'ml_model',
            'probabilities': {
                class_name: float(prob)
                for class_name, prob in zip(self.class_names, probabilities)
            },
            'model_version': self.model_version
        }
    
    def get_feature_importance(self) -> dict[str, float]:
        """
        Get feature importance scores.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            return {}
        
        importances = self.model.feature_importances_
        return {
            name: float(importance)
            for name, importance in zip(self.feature_names, importances)
        }
    
    def save(self, path: str | Path):
        """
        Save trained model and scaler.
        
        Args:
            path: Path to save model file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_extractor': self.feature_extractor,
            'is_trained': self.is_trained,
            'model_version': self.model_version,
            'training_date': self.training_date,
            'feature_names': self.feature_names,
            'class_names': self.class_names
        }
        
        joblib.dump(model_data, path)
        logger.info(f"✅ Model saved to {path}")
        
        # Save metadata separately
        metadata_path = path.parent / f"{path.stem}_metadata.json"
        metadata = {
            'model_version': self.model_version,
            'training_date': self.training_date,
            'feature_names': self.feature_names,
            'class_names': self.class_names,
            'is_trained': self.is_trained
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Metadata saved to {metadata_path}")
    
    def load(self, path: str | Path):
        """
        Load pre-trained model.
        
        Args:
            path: Path to model file
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        
        model_data = joblib.load(path)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_extractor = model_data.get('feature_extractor', HomeTypeFeatureExtractor())
        self.is_trained = model_data.get('is_trained', False)
        self.model_version = model_data.get('model_version', '1.0')
        self.training_date = model_data.get('training_date')
        self.feature_names = model_data.get('feature_names', [])
        self.class_names = model_data.get('class_names', [])
        
        logger.info(f"✅ Model loaded from {path}")
        logger.info(f"   Version: {self.model_version}")
        logger.info(f"   Trained: {self.training_date}")
        logger.info(f"   Classes: {self.class_names}")

