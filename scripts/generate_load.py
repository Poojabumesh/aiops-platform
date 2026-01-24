import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor
import sys

ALB_DNS = sys.argv[1] if len(sys.argv) > 1 else "YOUR-ALB-DNS-HERE"
BASE_URL = f"http://{ALB_DNS}"

print("ALB_DNS =", ALB_DNS)
print("BASE_URL =", BASE_URL)


def make_request(endpoint):
    """Make a request and return status code and latency"""
    try:
        start = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        latency = time.time() - start
        return {
            "endpoint": endpoint,
            "status": response.status_code,
            "latency": latency,
            "timestamp": time.time(),
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "status": "error",
            "latency": None,
            "error": str(e),
            "timestamp": time.time(),
        }


def generate_normal_load(duration_seconds=600, requests_per_second=5):
    """Generate normal baseline traffic"""
    print(
        f"Generating NORMAL load: {requests_per_second} req/s for {duration_seconds}s"
    )
    print(f"Target: {BASE_URL}")

    endpoints = ["/api/predict"] * 7 + ["/api/analyze"] * 2 + ["/health"] * 1
    start_time = time.time()
    request_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        while time.time() - start_time < duration_seconds:
            endpoint = random.choice(endpoints)
            future = executor.submit(make_request, endpoint)
            result = future.result()

            request_count += 1
            if result["status"] != 200:
                error_count += 1

            if request_count % 50 == 0:
                elapsed = time.time() - start_time
                print(
                    f"Requests: {request_count}, Errors: {error_count}, Elapsed: {elapsed:.0f}s"
                )

            time.sleep(1.0 / requests_per_second)

    print("Load generation complete")
    print(f"Total requests: {request_count}")
    print(f"Total errors: {error_count}")
    print(f"Error rate: {(error_count/request_count)*100:.2f}%")


def generate_anomaly_load(duration_seconds=120, requests_per_second=20):
    """Generate anomalous traffic for testing ML detection"""
    print(
        f"Generating ANOMALY load: {requests_per_second} req/s for {duration_seconds}s"
    )
    print(f"Target: {BASE_URL}")

    # Mostly /api/analyze which is CPU intensive
    endpoints = ["/api/analyze"] * 8 + ["/api/predict"] * 2
    start_time = time.time()
    request_count = 0

    with ThreadPoolExecutor(max_workers=30) as executor:
        while time.time() - start_time < duration_seconds:
            endpoint = random.choice(endpoints)
            executor.submit(make_request, endpoint)
            request_count += 1

            if request_count % 100 == 0:
                elapsed = time.time() - start_time
                print(f"Anomaly requests: {request_count}, Elapsed: {elapsed:.0f}s")

            time.sleep(1.0 / requests_per_second)

    print("Anomaly load complete")
    print(f"Total requests: {request_count}")


if __name__ == "__main__":
    if "YOUR-ALB-DNS-HERE" in ALB_DNS:
        print("ERROR: Set ALB_DNS as command line argument")
        print("Usage: python generate_load.py <ALB-DNS>")
        sys.exit(1)

    print("=== Baseline Data Collection ===")
    print("This will generate 60 minutes of normal traffic")
    print("Phase 4 will use this as baseline for anomaly detection\n")

    # Generate 60 minutes of normal traffic for baseline
    generate_normal_load(duration_seconds=3600, requests_per_second=5)
