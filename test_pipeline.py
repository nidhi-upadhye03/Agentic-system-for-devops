#!/usr/bin/env python3
"""
Quick test script to verify the complete pipeline:
Publish fake analysis event → Auto-response creates approval → Check database
"""
import pika
import json
import time

# RabbitMQ connection
credentials = pika.PlainCredentials('devops', 'devops123')
parameters = pika.ConnectionParameters(
    host='localhost',
    port=5672,
    virtual_host='devops',
    credentials=credentials
)

# Create analysis event (simulating what the analyzer would publish)
analysis_event = {
    "event_type": "analysis_complete",
    "incident_id": f"test-pipeline-{int(time.time())}",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "severity": "high",
    "data": {
        "root_cause": "High CPU usage detected (95%)",
        "explanation": "CPU utilization exceeded threshold",
        "confidence": 75.0,
        "recommendations": [{
            "action_type": "scale_deployment",
            "target": "test-app",
            "parameters": {"replicas": 3},
            "reason": "Scale up to handle increased load",
            "criticality": "high",
            "estimated_impact": "Should resolve in 2-3 minutes",
            "approval_required": True,
            "confidence": 75.0
        }]
    }
}

print("=" * 60)
print("TESTING COMPLETE PIPELINE")
print("=" * 60)
print(f"\\n1. Publishing analysis event to RabbitMQ...")
print(f"   Incident ID: {analysis_event['incident_id']}")

try:
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    channel.basic_publish(
        exchange='agent_events',
        routing_key='analyzer.analysis.complete',
        body=json.dumps(analysis_event),
        properties=pika.BasicProperties(
            delivery_mode=2,  # persistent
            content_type='application/json'
        )
    )
    
    print("   ✓ Event published successfully!")
    connection.close()
    
    print(f"\\n2. Waiting 5 seconds for auto-response to process...")
    time.sleep(5)
    
    print(f"\\n3. Check auto-response logs:")
    print("   docker logs devops-auto-response-agent --since 10s | findstr 'Processing\\|approval\\|Creating'")
    
    print(f"\\n4. Check approval database:")
    print("   docker exec devops-postgres psql -U devops -d devops_db -c \"SELECT id, title, status FROM approvals ORDER BY created_at DESC LIMIT 1;\"")
    
    print("\\n" + "=" * 60)
    print("Pipeline test initiated! Run the commands above to verify.")
    print("=" * 60)
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    print("\\nMake sure:")
    print("  - Docker containers are running")
    print("  - RabbitMQ is accessible on localhost:5672")
