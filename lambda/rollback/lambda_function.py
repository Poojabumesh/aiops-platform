import json
import boto3
from datetime import datetime

ecs = boto3.client('ecs')
sns = boto3.client('sns')

def get_task_definition_history(family):
    """Get task definition revision history"""
    response = ecs.list_task_definitions(
        familyPrefix=family,
        sort='DESC',
        maxResults=10
    )
    return response['taskDefinitionArns']

def rollback_deployment(cluster, service, reason):
    """Rollback to previous task definition"""
    
    # Get current service
    service_info = ecs.describe_services(
        cluster=cluster,
        services=[service]
    )['services'][0]
    
    current_task_def = service_info['taskDefinition']
    family = current_task_def.split('/')[1].split(':')[0]
    
    print(f"Current task definition: {current_task_def}")
    
    # Get previous version
    task_defs = get_task_definition_history(family)
    
    if len(task_defs) < 2:
        return {
            'status': 'failed',
            'message': 'No previous version to rollback to'
        }
    
    # Find previous version (skip current)
    current_revision = int(current_task_def.split(':')[-1])
    previous_task_def = None
    
    for task_def in task_defs:
        revision = int(task_def.split(':')[-1])
        if revision < current_revision:
            previous_task_def = task_def
            break
    
    if not previous_task_def:
        return {
            'status': 'failed',
            'message': 'Could not find previous task definition'
        }
    
    print(f"Rolling back to: {previous_task_def}")
    
    # Update service
    ecs.update_service(
        cluster=cluster,
        service=service,
        taskDefinition=previous_task_def,
        forceNewDeployment=False
    )
    
    return {
        'status': 'success',
        'from': current_task_def.split('/')[-1],
        'to': previous_task_def.split('/')[-1],
        'reason': reason
    }

def lambda_handler(event, context):
    """Rollback handler"""
    print("Starting rollback process...")
    
    try:
        # Get event data
        if 'body' in event:
            data = json.loads(event['body'])
        else:
            data = event
        
        cluster = data.get('cluster', 'aiops-platform-cluster')
        service = data.get('service', 'aiops-platform-service')
        reason = data.get('reason', 'Automated rollback due to anomaly')
        
        # Execute rollback
        result = rollback_deployment(cluster, service, reason)
        
        # Send notification
        if result['status'] == 'success':
            topic_arn = os.environ['SNS_TOPIC_ARN']
            
            message = f"""
AUTOMATED ROLLBACK EXECUTED

Timestamp: {datetime.utcnow().isoformat()}

Status: SUCCESS
Cluster: {cluster}
Service: {service}

Rollback Details:
  From: {result['from']}
  To: {result['to']}
  Reason: {result['reason']}

The service has been rolled back to the previous stable version.
Monitor the dashboard to ensure the issue is resolved.

Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=aiops-platform-enhanced-dashboard
"""
            
            sns.publish(
                TopicArn=topic_arn,
                Subject='Automated Rollback Executed',
                Message=message
            )
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
        
    except Exception as e:
        print(f"Rollback error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
