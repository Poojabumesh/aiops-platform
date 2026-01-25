import json
import boto3
import os
import joblib
from datetime import datetime, timedelta
import numpy as np

lambda_client = boto3.client("lambda")

# Load model at cold start
MODEL_PATH = "/tmp/anomaly_detector.pkl"
s3 = boto3.client("s3")
cloudwatch = boto3.client("cloudwatch")
sns = boto3.client("sns")


def load_model_from_s3():
    """Download model from S3 if not in /tmp"""
    if not os.path.exists(MODEL_PATH):
        bucket = os.environ["MODEL_BUCKET"]
        key = "models/anomaly_detector.pkl"
        s3.download_file(bucket, key, MODEL_PATH)

    return joblib.load(MODEL_PATH)


def fetch_latest_metrics():
    """Fetch latest metrics from CloudWatch"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=10)

    def get_metric(metric_name, namespace, dimensions=[]):
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=["Average"],
        )
        datapoints = response["Datapoints"]
        if datapoints:
            return sorted(datapoints, key=lambda x: x["Timestamp"])[-1]["Average"]
        return 0

    cpu = get_metric(
        "CPUUtilization",
        "AWS/ECS",
        [
            {"Name": "ServiceName", "Value": "aiops-platform-service"},
            {"Name": "ClusterName", "Value": "aiops-platform-cluster"},
        ],
    )

    memory = get_metric(
        "MemoryUtilization",
        "AWS/ECS",
        [
            {"Name": "ServiceName", "Value": "aiops-platform-service"},
            {"Name": "ClusterName", "Value": "aiops-platform-cluster"},
        ],
    )

    response_time = get_metric("TargetResponseTime", "AWS/ApplicationELB")
    request_count = get_metric("RequestCount", "AWS/ApplicationELB")
    error_count = get_metric("HTTPCode_Target_5XX_Count", "AWS/ApplicationELB")

    error_rate = (error_count / request_count * 100) if request_count > 0 else 0

    return {
        "cpu_utilization": cpu,
        "memory_utilization": memory,
        "response_time": response_time,
        "request_count": request_count,
        "error_rate": error_rate,
    }


def send_alert(result):
    """Send SNS alert if anomaly detected"""
    topic_arn = os.environ["SNS_TOPIC_ARN"]

    message = f"""
              ANOMALY DETECTED in AIOps Platform

              Timestamp: {result['timestamp']}
              Anomaly Score: {result['anomaly_score']:.4f}

              Current Metrics:
               - CPU Utilization: {result['metrics']['cpu_utilization']:.2f}%
               - Memory Utilization: {result['metrics']['memory_utilization']:.2f}%
               - Response Time: {result['metrics']['response_time']:.4f}s
               - Request Count: {result['metrics']['request_count']:.0f}
               - Error Rate: {result['metrics']['error_rate']:.2f}%

             Action Required: Investigate infrastructure immediately.
             """

    sns.publish(
        TopicArn=topic_arn, Subject="Anomaly Detected - AIOps Platform", Message=message
    )


def trigger_rca(result):
    """Trigger root cause analysis Lambda"""
    try:
        rca_function = os.environ.get("RCA_FUNCTION_NAME", "aiops-platform-rca")

        lambda_client.invoke(
            FunctionName=rca_function,
            InvocationType="Event",  # Async
            Payload=json.dumps(result),
        )
        print(f"Triggered RCA Lambda: {rca_function}")
    except Exception as e:
        print(f"Failed to trigger RCA: {str(e)}")


def lambda_handler(event, context):
    """Main Lambda handler"""
    print("Starting anomaly detection...")

    try:
        # Load model
        model_data = load_model_from_s3()

        # Fetch latest metrics
        metrics = fetch_latest_metrics()
        print(f"Current metrics: {metrics}")

        # Prepare features
        feature_names = model_data["feature_names"]
        features = np.array([metrics[name] for name in feature_names]).reshape(1, -1)

        # Scale and predict
        X_scaled = model_data["scaler"].transform(features)
        prediction = model_data["model"].predict(X_scaled)[0]
        score = model_data["model"].score_samples(X_scaled)[0]

        is_anomaly = prediction == -1

        result = {
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": float(score),
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
        }

        # Log to CloudWatch
        print(f"Detection result: {result}")

        # Send alert if anomaly
        if is_anomaly:
            print("ANOMALY DETECTED! Sending alert...")
            send_alert(result)
            trigger_rca(result)
        else:
            print("No anomaly detected")

        return {"statusCode": 200, "body": json.dumps(result, default=str)}

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
