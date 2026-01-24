import requests
import time
from concurrent.futures import ThreadPoolExecutor
import sys

ALB_DNS = sys.argv[1] if len(sys.argv) > 1 else "YOUR-ALB-DNS-HERE"
BASE_URL = f"http://{ALB_DNS}"


def make_request(endpoint):
    """Make a request"""
    try:
        requests.get(f"{BASE_URL}{endpoint}", timeout=10)
    except Exception:
        pass


def generate_cpu_spike():
    """Generate high CPU load to trigger anomaly"""
    print("Generating CPU SPIKE for 10 minutes...")
    print(f"This should trigger anomaly detection!\n")

    # Heavy CPU load - lots of /api/analyze requests
    endpoints = ["/api/analyze"] * 9 + ["/api/predict"] * 1

    start_time = time.time()
    request_count = 0

    with ThreadPoolExecutor(max_workers=20) as executor:
        while time.time() - start_time < 600:  # 10 minutes
            for _ in range(20):  # Burst of requests
                endpoint = endpoints[request_count % len(endpoints)]
                executor.submit(make_request, endpoint)
                request_count += 1

            if request_count % 100 == 0:
                elapsed = time.time() - start_time
                print(f"Anomaly requests: {request_count}, Elapsed: {elapsed:.0f}s")

            time.sleep(0.5)

    print("Anomaly generation complete")
    print(f"Total requests: {request_count}")
    print(f"Wait 5 minutes and check your email for anomaly alert!")


if __name__ == "__main__":
    if "YOUR-ALB-DNS-HERE" in ALB_DNS:
        print("ERROR: Provide ALB DNS as argument")
        print("Usage: python generate_anomaly.py <ALB-DNS>")
        sys.exit(1)

    response = input("This will generate HIGH CPU load. Continue? (yes/no): ")
    if response.lower() == "yes":
        generate_cpu_spike()
    else:
        print("Cancelled")
