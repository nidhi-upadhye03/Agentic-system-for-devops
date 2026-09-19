#!/usr/bin/env python3
"""
Publish a monitoring incident event to trigger the full pipeline:
RabbitMQ → Analyzer → Auto-Response → Approval Dashboard
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

# Create incident event (matching monitoring agent format)
incident_event = {
    "agent": "monitoring",
    "type": "incident_detected",
    "incident_id": f"manual-test-{int(time.time())}",
    "event_type": "threshold_breach",
    "severity": "high",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "message": "Manual test - High CPU usage detected",
    "data": {
        "metric": "test_app_cpu_percent",
        "current_value": 95.5,
        "threshold": 80.0,
        "affected_services": ["test-app"],
        "cluster": "local",
        "namespace": "default"
    },
    "labels": {
        "service": "test-app",
        "environment": "local"
    }
}

print("="*80)
print("MANUAL INCIDENT INJECTION - TESTING COMPLETE PIPELINE")
print("="*80)
print(f"\n📝 Incident Details:")
print(f"   ID: {incident_event['incident_id']}")
print(f"   Type: {incident_event['event_type']}")
print(f"   Severity: {incident_event['severity']}")
print(f"   Metric: {incident_event['data']['metric']} = {incident_event['data']['current_value']}")
print(f"   Threshold: {incident_event['data']['threshold']}")

try:
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Publish to monitoring.incident.* routing key
    routing_key = f"monitoring.incident.{incident_event['event_type']}"
    
    channel.basic_publish(
        exchange='agent_events',
        routing_key=routing_key,
        body=json.dumps(incident_event),
        properties=pika.BasicProperties(
            delivery_mode=2,  # persistent
            content_type='application/json'
        )
    )
    
    print(f"\n✅ Event published to RabbitMQ")
    print(f"   Exchange: agent_events")
    print(f"   Routing Key: {routing_key}")
    connection.close()
    
    print(f"\n⏳ Waiting 8 seconds for pipeline to process...")
    time.sleep(8)
    
    print(f"\n{'='*80}")
    print("RESULTS:")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
