import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import json
from datetime import datetime


class AnomalyDetector:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = [
            "cpu_utilization",
            "memory_utilization",
            "response_time",
            "request_count",
            "error_rate",
        ]

    def prepare_features(self, metrics):
        """Convert metrics dict to feature array"""
        features = []
        for name in self.feature_names:
            features.append(metrics.get(name, 0))
        return np.array(features).reshape(1, -1)

    def train(self, training_data):
        """Train Isolation Forest model on baseline data"""
        print(f"Training on {len(training_data)} samples...")

        # Prepare training features
        X = []
        for sample in training_data:
            features = []
            for name in self.feature_names:
                features.append(sample.get(name, 0))
            X.append(features)

        X = np.array(X)

        # Normalize features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train Isolation Forest
        # contamination: expected proportion of outliers (5%)
        self.model = IsolationForest(
            contamination=0.05, random_state=42, n_estimators=100
        )
        self.model.fit(X_scaled)

        print("Model trained successfully")

    def predict(self, metrics):
        """Detect if current metrics are anomalous"""
        if self.model is None:
            raise Exception("Model not trained")

        # Prepare features
        X = self.prepare_features(metrics)

        # Scale features
        X_scaled = self.scaler.transform(X)

        # Predict (-1 = anomaly, 1 = normal)
        prediction = self.model.predict(X_scaled)[0]

        # Get anomaly score (lower = more anomalous)
        score = self.model.score_samples(X_scaled)[0]

        is_anomaly = prediction == -1

        return {
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": float(score),
            "confidence": abs(float(score)),
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
        }

    def save_model(self, filepath):
        """Save model and scaler to file"""
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "feature_names": self.feature_names,
            },
            filepath,
        )
        print(f"Model saved to {filepath}")

    def load_model(self, filepath):
        """Load model and scaler from file"""
        data = joblib.load(filepath)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_names = data["feature_names"]
        print(f"Model loaded from {filepath}")
