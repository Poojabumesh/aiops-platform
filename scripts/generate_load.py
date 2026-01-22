import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor

# Replace with your ALB DNS
ALB_DNS = "aiops-platform-alb-2051198743.us-east-1.elb.amazonaws.com"
BASE_URL = f"http://{ALB_DNS}"


def make_request(endpoint):
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        return response.status_code, response.elapsed.total_seconds()
    except Exception as e:
        return None, None


def generate_load(duration_seconds=300, requests_per_second=10):
    """Generate load for specified duration"""
    print(f"Generating load: {requests_per_second} req/s for {duration_seconds}s")

    endpoints = ["/api/predict", "/api/predict", "/health"]
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        while time.time() - start_time < duration_seconds:
            endpoint = random.choice(endpoints)
            executor.submit(make_request, endpoint)
            time.sleep(1.0 / requests_per_second)

    print("Load generation complete!")


if __name__ == "__main__":
    generate_load(duration_seconds=180, requests_per_second=5)
