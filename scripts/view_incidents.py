import boto3
from datetime import datetime, timedelta
import json

logs = boto3.client('logs', region_name='us-east-1')

def get_recent_incidents(hours=24):
    """Get recent incidents from Lambda logs"""
    
    log_groups = [
        '/aws/lambda/aiops-platform-anomaly-detector',
        '/aws/lambda/aiops-platform-rca',
        '/aws/lambda/aiops-platform-rollback'
    ]
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    incidents = []
    
    for log_group in log_groups:
        try:
            response = logs.filter_log_events(
                logGroupName=log_group,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                filterPattern='ANOMALY'
            )
            
            for event in response.get('events', []):
                if 'ANOMALY DETECTED' in event['message']:
                    incidents.append({
                        'timestamp': datetime.fromtimestamp(event['timestamp']/1000),
                        'source': log_group.split('/')[-1],
                        'message': event['message'][:200]
                    })
        except:
            pass
    
    return sorted(incidents, key=lambda x: x['timestamp'], reverse=True)

def display_incidents():
    """Display incident summary"""
    print("=== RECENT INCIDENTS (Last 24 Hours) ===\n")
    
    incidents = get_recent_incidents(24)
    
    if not incidents:
        print("No incidents detected in the last 24 hours\n")
        return
    
    print(f"Total incidents: {len(incidents)}\n")
    
    for i, incident in enumerate(incidents[:10], 1):
        print(f"{i}. [{incident['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}]")
        print(f"   Source: {incident['source']}")
        print(f"   {incident['message']}\n")

if __name__ == "__main__":
    display_incidents()
