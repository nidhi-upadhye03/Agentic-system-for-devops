#!/usr/bin/env python3
"""
Inject a test incident directly into the database to trigger the full pipeline.
This bypasses the monitoring agent to test: Database → Analyzer → Auto-Response → Approval
"""
import time
import psycopg2
import json

# Database connection
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='devops_db',
    user='devops',
    password='devops123'
)

incident_id = f"manual-test-{int(time.time())}"

incident_data = {
    'incident_id': incident_id,
    'event_type': 'threshold_breach',
    'severity': 'high',
    'metric_name': 'test_app_cpu_percent',
    'metric_value': 95.5,
    'threshold': 80.0,
    'message': f'MANUAL TEST - High CPU detected: 95.5% (threshold: 80.0%)',
    'labels': json.dumps({'service': 'test-app', 'environment': 'local'}),
    'metadata': json.dumps({'test': True, 'triggered_by': 'manual_script'}),
    'source': 'monitoring-agent',
    'status': 'detected'
}

print("="*70)
print("INJECTING TEST INCIDENT INTO DATABASE")
print("="*70)
print(f"\nIncident ID: {incident_id}")
print(f"Type: {incident_data['event_type']}")
print(f"Severity: {incident_data['severity']}")  
print(f"Metric: {incident_data['metric_name']} = {incident_data['metric_value']}")

try:
    cur = conn.cursor()
    
    # Insert incident
    insert_sql = """
    INSERT INTO incidents (incident_id, event_type, severity, metric_name, metric_value, 
                          threshold, message, labels, metadata, source, status)
    VALUES (%(incident_id)s, %(event_type)s, %(severity)s, %(metric_name)s, %(metric_value)s,
            %(threshold)s, %(message)s, %(labels)s::jsonb, %(metadata)s::jsonb, %(source)s, %(status)s)
    RETURNING id, created_at;
    """
    
    cur.execute(insert_sql, incident_data)
    result = cur.fetchone()
    conn.commit()
    
    print(f"\n✓ Incident inserted successfully!")
    print(f"  Database ID: {result[0]}")
    print(f"  Created at: {result[1]}")
    
    print(f"\n{'='*70}")
    print("NEXT STEPS:")
    print("="*70)
    print("\nNOTE: Database incidents don't auto-trigger the pipeline.")
    print("The monitoring agent publishes to RabbitMQ, not the database.")
    print("\nTo trigger the full pipeline, we need to publish to RabbitMQ.")
    print("\nCheck if there are ANY recent incidents being analyzed:")
    print("  docker logs devops-analyzer-agent --since 1m")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    conn.rollback()
