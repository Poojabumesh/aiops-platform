import json
import boto3
from datetime import datetime, timedelta, timezone
from anomaly_detector import AnomalyDetector


def fetch_cloudwatch_metrics():
    """Fetch baseline metrics from CloudWatch"""
    cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=2)  # Last 2 hours

    def get_metric(metric_name, namespace, dimensions=[]):
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=300,  # 5 minutes
            Statistics=["Average"],
        )
        return response["Datapoints"]

    REGION = "us-east-1"
    ALB_NAME = "aiops-platform-alb"
    TG_NAME = "aiops-platform-tg"

    elbv2 = boto3.client("elbv2", region_name=REGION)

    lb_arn = elbv2.describe_load_balancers(Names=[ALB_NAME])["LoadBalancers"][0][
        "LoadBalancerArn"
    ]
    tg_arn = elbv2.describe_target_groups(Names=[TG_NAME])["TargetGroups"][0][
        "TargetGroupArn"
    ]

    lb_suffix = lb_arn.split("loadbalancer/")[1]
    tg_suffix = "targetgroup/" + tg_arn.split("targetgroup/")[1]

    # Fetch metrics
    cpu_data = get_metric(
        "CPUUtilization",
        "AWS/ECS",
        [
            {"Name": "ServiceName", "Value": "aiops-platform-service"},
            {"Name": "ClusterName", "Value": "aiops-platform-cluster"},
        ],
    )

    memory_data = get_metric(
        "MemoryUtilization",
        "AWS/ECS",
        [
            {"Name": "ServiceName", "Value": "aiops-platform-service"},
            {"Name": "ClusterName", "Value": "aiops-platform-cluster"},
        ],
    )

    lb_dims = [{"Name": "LoadBalancer", "Value": lb_suffix}]
    lb_tg_dims = [
        {"Name": "LoadBalancer", "Value": lb_suffix},
        {"Name": "TargetGroup", "Value": tg_suffix},
    ]

    response_time_data = get_metric(
        "TargetResponseTime", "AWS/ApplicationELB", lb_tg_dims
    )
    request_count_data = get_metric("RequestCount", "AWS/ApplicationELB", lb_dims)
    error_data = get_metric(
        "HTTPCode_Target_5XX_Count", "AWS/ApplicationELB", lb_tg_dims
    )

    print(f"response_time_data: {response_time_data}, len(response_time_data)")
    print(f"request_count_data: {request_count_data}, len(request_count_data)")
    print(f"error_data: {error_data}, len(error_data)")

    # Combine data by timestamp
    training_data = []

    def to_bucket(ts, bucket_seconds=300):
        epoch = int(ts.timestamp())
        return epoch - (epoch % bucket_seconds)

    def index_by_bucket(points, key="Average"):
        d = {}
        for p in points:
            d[to_bucket(p["Timestamp"])] = p.get(key)

        return d

    cpu = index_by_bucket(cpu_data)
    mem = index_by_bucket(memory_data)
    rt = index_by_bucket(response_time_data)
    rc = index_by_bucket(request_count_data)
    err = index_by_bucket(error_data)

    common = sorted(set(cpu) & set(mem) & set(rt) & set(rc))
    training_data = []

    for b in common:
        request_count = rc[b] or 1
        error_count = err.get(b, 0) or 0

        training_data.append(
            {
                "timestamp": datetime.fromtimestamp(b, tz=timezone.utc).isoformat(),
                "cpu_utilization": cpu[b],
                "memory_utilization": mem[b],
                "response_time": rt[b],
                "request_count": request_count,
                "error_rate": (
                    (error_count / request_count) * 100 if request_count else 0
                ),
            }
        )

    return training_data


def main():
    print("=== Training Anomaly Detection Model ===\n")

    # Fetch baseline data
    print("Fetching baseline metrics from CloudWatch...")
    training_data = fetch_cloudwatch_metrics()

    if len(training_data) < 10:
        print(f" Not enough data: {len(training_data)} samples")
        print("Run load generator for at least 1 hour to collect baseline data")
        return

    print(f"Fetched {len(training_data)} baseline samples\n")

    # Save baseline data
    with open("data/baseline_data.json", "w") as f:
        json.dump(training_data, f, indent=2, default=str)
    print("Baseline data saved to data/baseline_data.json\n")

    # Train model
    detector = AnomalyDetector()
    detector.train(training_data)

    # Save model
    detector.save_model("models/anomaly_detector.pkl")

    # Test prediction on latest sample
    print("\n=== Testing Model ===")
    test_sample = training_data[-1]
    result = detector.predict(test_sample)

    print(f"Test prediction: {'ANOMALY' if result['is_anomaly'] else 'NORMAL'}")
    print(f"Anomaly score: {result['anomaly_score']:.4f}")
    print(f"Metrics: {test_sample}")

    print("Model training complete!")


if __name__ == "__main__":
    import os

    os.makedirs("data", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    main()
