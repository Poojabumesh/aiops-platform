import json
import boto3
from datetime import datetime, timedelta
import re

cloudwatch_logs = boto3.client("logs")
ecs = boto3.client("ecs")
sns = boto3.client("sns")
logs = boto3.client("logs")
lambda_client = boto3.client("lambda")


def analyze_logs(log_group, minutes=10):
    """Analyze CloudWatch logs for error patterns"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=minutes)

    # Convert to milliseconds timestamp
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)

    errors = []
    patterns = {
        "memory": r"(OutOfMemory|MemoryError|killed|exit code 137)",
        "timeout": r"(timeout|timed out|TimeoutError)",
        "connection": r"(connection refused|ConnectionError|cannot connect)",
        "rate_limit": r"(rate limit|429|too many requests)",
        "exception": r"(Exception|Error|Traceback)",
    }

    try:
        # Query logs
        response = cloudwatch_logs.filter_log_events(
            logGroupName=log_group, startTime=start_ms, endTime=end_ms, limit=100
        )

        for event in response.get("events", []):
            message = event["message"]

            for error_type, pattern in patterns.items():
                if re.search(pattern, message, re.IGNORECASE):
                    errors.append(
                        {
                            "type": error_type,
                            "timestamp": event["timestamp"],
                            "message": message[:200],  # Truncate
                        }
                    )

        return errors
    except Exception as e:
        print(f"Error analyzing logs: {str(e)}")
        return []


def classify_root_cause(anomaly_metrics, log_errors):
    """Classify the root cause based on metrics and logs"""
    root_causes = []

    # Check CPU issues
    if "CPU" in str(anomaly_metrics.get("anomalies", [])):
        cpu_errors = [e for e in log_errors if e["type"] in ["timeout", "exception"]]
        if cpu_errors:
            root_causes.append(
                {
                    "type": "HIGH_CPU",
                    "severity": "HIGH",
                    "description": "High CPU utilization detected with application errors",
                    "evidence": cpu_errors[:3],
                    "remediation": "scale_up",
                }
            )
        else:
            root_causes.append(
                {
                    "type": "HIGH_CPU",
                    "severity": "MEDIUM",
                    "description": "High CPU utilization without application errors (likely normal load)",
                    "evidence": [],
                    "remediation": "monitor",
                }
            )

    # Check Memory issues
    if "Memory" in str(anomaly_metrics.get("anomalies", [])):
        memory_errors = [e for e in log_errors if e["type"] == "memory"]
        if memory_errors:
            root_causes.append(
                {
                    "type": "MEMORY_LEAK",
                    "severity": "CRITICAL",
                    "description": "Memory leak detected - tasks being killed",
                    "evidence": memory_errors[:3],
                    "remediation": "restart_tasks",
                }
            )

    if "Error Rate" in str(anomaly_metrics.get("anomalies", [])):
        exception_errors = [
            e for e in log_errors if e["type"] in ["exception", "connection"]
        ]
        if len(exception_errors) > 10:  # High number of errors
            root_causes.append(
                {
                    "type": "APPLICATION_ERROR",
                    "severity": "CRITICAL",
                    "description": f"High error rate ({len(exception_errors)} errors) - likely bad deployment",
                    "evidence": exception_errors[:3],
                    "remediation": "rollback",  # ← Trigger rollback
                }
            )
        elif exception_errors:
            root_causes.append(
                {
                    "type": "APPLICATION_ERROR",
                    "severity": "HIGH",
                    "description": "Elevated error rate with exceptions",
                    "evidence": exception_errors[:3],
                    "remediation": "investigate_and_alert",
                }
            )

    # Check Response Time
    if "Response Time" in str(anomaly_metrics.get("anomalies", [])):
        timeout_errors = [e for e in log_errors if e["type"] == "timeout"]
        if timeout_errors:
            root_causes.append(
                {
                    "type": "SLOW_RESPONSE",
                    "severity": "MEDIUM",
                    "description": "Slow response times with timeout errors",
                    "evidence": timeout_errors[:3],
                    "remediation": "scale_up",
                }
            )

    return (
        root_causes
        if root_causes
        else [
            {
                "type": "UNKNOWN",
                "severity": "LOW",
                "description": "Anomaly detected but no clear root cause in logs",
                "evidence": [],
                "remediation": "monitor",
            }
        ]
    )


def trigger_rollback(cluster, service, reason):
    """Trigger automated rollback"""
    try:
        rollback_function = os.environ.get(
            "ROLLBACK_FUNCTION_NAME", "aiops-platform-rollback"
        )

        lambda_client.invoke(
            FunctionName=rollback_function,
            InvocationType="Event",
            Payload=json.dumps(
                {"cluster": cluster, "service": service, "reason": reason}
            ),
        )
        print(f"Triggered rollback Lambda")
        return True
    except Exception as e:
        print(f"Failed to trigger rollback: {str(e)}")
        return False


def execute_remediation(root_cause, cluster, service):
    """Execute automated remediation based on root cause"""
    remediation_action = root_cause["remediation"]

    results = []

    if remediation_action == "restart_tasks":
        print(f"Executing remediation: Restart tasks")

        # List running tasks
        task_arns = ecs.list_tasks(
            cluster=cluster, serviceName=service, desiredStatus="RUNNING"
        )["taskArns"]

        # Stop tasks (ECS will auto-restart them)
        for task_arn in task_arns[:1]:  # Only restart one at a time for safety
            ecs.stop_task(
                cluster=cluster,
                task=task_arn,
                reason="Automated remediation: Memory leak detected",
            )
            results.append(f"Stopped task: {task_arn.split('/')[-1]}")

        return {"action": "restart_tasks", "status": "completed", "details": results}

    elif remediation_action == "scale_up":
        print(f"Executing remediation: Scale up")

        # Get current desired count
        service_info = ecs.describe_services(cluster=cluster, services=[service])[
            "services"
        ][0]

        current_count = service_info["desiredCount"]
        new_count = min(current_count + 1, 4)  # Max 4 tasks

        if new_count > current_count:
            ecs.update_service(cluster=cluster, service=service, desiredCount=new_count)
            results.append(f"Scaled from {current_count} to {new_count} tasks")
        else:
            results.append(f"Already at max tasks ({current_count})")

        return {"action": "scale_up", "status": "completed", "details": results}

    elif remediation_action == "monitor":
        return {
            "action": "monitor",
            "status": "no_action",
            "details": ["Continuing to monitor - no immediate action needed"],
        }

    elif remediation_action == "rollback":
        print(f"Executing remediation: Rollback deployment")

        success = trigger_rollback(
            cluster=cluster, service=service, reason=root_cause["description"]
        )

        if success:
            results.append("Triggered automated rollback")
        else:
            results.append("Rollback trigger failed")

        return {
            "action": "rollback",
            "status": "triggered" if success else "failed",
            "details": results,
        }

    else:  # investigate_and_alert
        return {
            "action": "alert",
            "status": "pending_manual",
            "details": ["Manual investigation required"],
        }


def send_rca_report(root_causes, remediation_results, anomaly_data):
    """Send detailed RCA report via SNS"""
    topic_arn = os.environ["SNS_TOPIC_ARN"]

    # Format root causes
    rca_details = []
    for rc in root_causes:
        evidence_str = "\n".join(
            [f"    - {e['message'][:100]}" for e in rc["evidence"][:2]]
        )
        rca_details.append(f"""
  [{rc['severity']}] {rc['type']}
  Description: {rc['description']}
  Evidence:
{evidence_str if evidence_str else '    None'}
  Recommended Action: {rc['remediation']}
""")

    # Format remediation results
    remediation_str = "\n".join(
        [f"  - {detail}" for detail in remediation_results.get("details", [])]
    )

    message = f"""
🔍 ROOT CAUSE ANALYSIS REPORT

Timestamp: {datetime.utcnow().isoformat()}

ANOMALY DETECTED:
{anomaly_data.get('anomalies', [])}

ROOT CAUSE ANALYSIS:
{''.join(rca_details)}

AUTOMATED REMEDIATION TAKEN:
  Action: {remediation_results.get('action', 'none')}
  Status: {remediation_results.get('status', 'unknown')}
  Details:
{remediation_str}

METRICS AT TIME OF INCIDENT:
  CPU: {anomaly_data['metrics']['cpu_utilization']:.2f}%
  Memory: {anomaly_data['metrics']['memory_utilization']:.2f}%
  Response Time: {anomaly_data['metrics']['response_time']:.4f}s
  Error Rate: {anomaly_data['metrics']['error_rate']:.2f}%

Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=aiops-platform-enhanced-dashboard
"""

    sns.publish(
        TopicArn=topic_arn,
        Subject=f'🔍 Root Cause Analysis - {root_causes[0]["type"]}',
        Message=message,
    )


def lambda_handler(event, context):
    """Main handler - triggered by anomaly detection"""
    print("Starting root cause analysis...")

    try:
        # Get anomaly data from event (passed from anomaly detector)
        if "body" in event:
            anomaly_data = json.loads(event["body"])
        else:
            anomaly_data = event

        print(f"Anomaly data: {anomaly_data}")

        # Analyze logs
        log_errors = analyze_logs("/ecs/aiops-platform", minutes=10)
        print(f"Found {len(log_errors)} log errors")

        # Classify root cause
        root_causes = classify_root_cause(anomaly_data, log_errors)
        print(f"Identified {len(root_causes)} root causes")

        # Execute remediation for the highest severity issue
        primary_cause = sorted(
            root_causes,
            key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[
                x["severity"]
            ],
        )[0]

        remediation_results = execute_remediation(
            primary_cause,
            cluster="aiops-platform-cluster",
            service="aiops-platform-service",
        )

        print(f"Remediation results: {remediation_results}")

        # Send detailed RCA report
        send_rca_report(root_causes, remediation_results, anomaly_data)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "root_causes": root_causes,
                    "remediation": remediation_results,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                default=str,
            ),
        }

    except Exception as e:
        print(f"Error in RCA: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
