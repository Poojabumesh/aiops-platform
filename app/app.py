from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram, Gauge
import time
import random
import logging
import os

app = Flask(__name__)

# Initialize Prometheus metrics
metrics = PrometheusMetrics(app)

# Custom metrics
request_latency = Histogram(
    'app_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint', 'method']
)

error_counter = Counter(
    'app_errors_total',
    'Total number of errors',
    ['endpoint', 'error_type']
)

prediction_counter = Counter(
    'app_predictions_total',
    'Total number of predictions',
    ['prediction_type']
)

active_requests = Gauge(
    'app_active_requests',
    'Number of active requests'
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "aiops-platform"}), 200

@app.route('/api/predict')
@request_latency.labels(endpoint='predict', method='GET').time()
def predict():
    active_requests.inc()
    try:
        # Simulate processing time
        latency = random.uniform(0.1, 0.5)
        time.sleep(latency)
        
        # Randomly inject errors (5% failure rate)
        if random.random() < 0.05:
            error_counter.labels(endpoint='predict', error_type='random_failure').inc()
            logger.error("Prediction failed - random error injection")
            active_requests.dec()
            return jsonify({"error": "Internal processing error"}), 500
        
        # Generate prediction
        prediction_type = random.choice(["normal", "anomaly"])
        prediction_counter.labels(prediction_type=prediction_type).inc()
        
        result = {
            "prediction": prediction_type,
            "confidence": random.uniform(0.7, 0.99),
            "latency_ms": latency * 1000,
            "timestamp": time.time()
        }
        
        logger.info(f"Prediction successful: {result}")
        active_requests.dec()
        return jsonify(result), 200
        
    except Exception as e:
        error_counter.labels(endpoint='predict', error_type='exception').inc()
        logger.exception("Unexpected error in predict endpoint")
        active_requests.dec()
        return jsonify({"error": "Unexpected error"}), 500

@app.route('/api/analyze')
@request_latency.labels(endpoint='analyze', method='GET').time()
def analyze():
    active_requests.inc()
    try:
        # Simulate CPU work
        start = time.time()
        _ = sum(i**2 for i in range(100000))
        duration = time.time() - start
        
        logger.info(f"Analysis completed in {duration:.3f}s")
        active_requests.dec()
        return jsonify({
            "status": "completed",
            "duration_ms": duration * 1000,
            "timestamp": time.time()
        }), 200
        
    except Exception as e:
        error_counter.labels(endpoint='analyze', error_type='exception').inc()
        logger.exception("Error in analyze endpoint")
        active_requests.dec()
        return jsonify({"error": "Analysis failed"}), 500

# Prometheus metrics endpoint is automatically created by PrometheusMetrics
# Available at /metrics

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
