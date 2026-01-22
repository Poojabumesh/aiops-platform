import boto3
from datetime import datetime, timedelta
import json

# Initialize CloudWatch client
cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")


def get_metric_statistics(metric_name, namespace, dimensions, start_time, end_time):
    """Get metric statistics from CloudWatch"""
    response = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start_time,
        EndTime=end_time,
        Period=300,  # 5 minutes
        Statistics=["Average", "Maximum", "Minimum", "Sum"],
    )
    return response["Datapoints"]


def export_baseline_data():
    """Export baseline metrics for ML training"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)  # Last hour

    metrics_data = {}

    # CPU Utilization
    print("Exporting CPU metrics...")
    metrics_data["cpu"] = get_metric_statistics(
        "CPUUtilization",
        "AWS/ECS",
        [
            {"Name": "ServiceName", "Value": "aiops-platform-service"},
            {"Name": "ClusterName", "Value": "aiops-platform-cluster"},
        ],
        start_time,
        end_time,
    )

    # Memory Utilization
    print("Exporting Memory metrics...")
    metrics_data["memory"] = get_metric_statistics(
        "MemoryUtilization",
        "AWS/ECS",
        [
            {"Name": "ServiceName", "Value": "aiops-platform-service"},
            {"Name": "ClusterName", "Value": "aiops-platform-cluster"},
        ],
        start_time,
        end_time,
    )

    # Response Time
    print("Exporting Response Time metrics...")
    metrics_data["response_time"] = get_metric_statistics(
        "TargetResponseTime", "AWS/ApplicationELB", [], start_time, end_time
    )

    # Request Count
    print("Exporting Request Count metrics...")
    metrics_data["request_count"] = get_metric_statistics(
        "RequestCount", "AWS/ApplicationELB", [], start_time, end_time
    )

    # 5xx Errors
    print("Exporting Error metrics...")
    metrics_data["errors_5xx"] = get_metric_statistics(
        "HTTPCode_Target_5XX_Count", "AWS/ApplicationELB", [], start_time, end_time
    )

    # Save to file
    output_file = "data/baseline_metrics.json"
    with open(output_file, "w") as f:
        json.dump(metrics_data, f, indent=2, default=str)

    print(f"Baseline data exported to {output_file}")
    print(f"Data points collected:")
    for metric, data in metrics_data.items():
        print(f"  - {metric}: {len(data)} data points")


if __name__ == "__main__":
    import os

    os.makedirs("data", exist_ok=True)
    export_baseline_data()
