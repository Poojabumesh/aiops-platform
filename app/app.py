from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics
import logging
import time 
import random


app = Flask(__name__)
metrics = PrometheusMetrics(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/api/predict")
def predict():
    latency = random.uniform(0.1, 0.5)
    time.sleep(latency)
    
    # 5% error rate
    if random.random() < 0.05:
        logger.error("Prediction failed")
        return jsonify({"error": "Internal error"}), 500
    
    return jsonify({
        "prediction": random.choice(["normal", "anomaly"]),
        "confidence": random.uniform(0.7, 0.99)
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
