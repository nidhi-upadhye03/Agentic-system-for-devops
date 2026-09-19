"""
Prompts for LLM-based incident analysis

Contains structured prompts with JSON schemas for consistent LLM responses.
"""

ANALYSIS_PROMPT_TEMPLATE = """You are a DevOps AI agent analyzing infrastructure incidents.

INCIDENT DATA:
- Service: {service_name}
- Metric: {metric_name}
- Current Value: {current_value}
- Threshold: {threshold}
- Severity: {severity}
- Affected Services: {affected_services}
- Cluster: {cluster}
- Namespace: {namespace}
- Timestamp: {timestamp}

{logs_section}

{similar_incidents_section}

YOUR TASK:
1. Identify the root cause of this incident
2. Assess confidence level (0-100%)
3. Provide ACTIONABLE recommendations using ONLY these action types:
   - RESTART: Restart pods/containers/deployments
   - SCALE: Scale up/down the number of replicas
   - ROLLBACK: Rollback to previous deployment version
   - INVESTIGATE: Requires human investigation (no automated action)

RESPONSE FORMAT (strict JSON):
{{
  "root_cause": "Brief description of the root cause",
  "explanation": "Detailed explanation of why this happened",
  "confidence": 85,
  "contributing_factors": ["factor1", "factor2"],
  "recommendations": [
    {{
      "action_type": "RESTART",
      "target_service": "test-app",
      "target_type": "deployment",
      "parameters": {{}},
      "rationale": "High memory usage indicates memory leak, restart will clear it",
      "criticality": "medium",
      "estimated_impact": "30 seconds downtime"
    }}
  ]
}}

EXAMPLES:

Example 1 - High CPU Usage:
{{
  "root_cause": "CPU spike due to inefficient query causing high load",
  "explanation": "The service is experiencing 95% CPU utilization due to a blocking operation in the request handler",
  "confidence": 80,
  "contributing_factors": ["Inefficient database query", "High request volume"],
  "recommendations": [
    {{
      "action_type": "RESTART",
      "target_service": "api-service",
      "target_type": "deployment",
      "parameters": {{}},
      "rationale": "Restart will kill stuck processes and restore normal operation",
      "criticality": "high",
      "estimated_impact": "Brief service interruption during restart"
    }},
    {{
      "action_type": "SCALE",
      "target_service": "api-service",
      "target_type": "deployment",
      "parameters": {{"replicas": 5}},
      "rationale": "Distribute load across more instances while investigating",
      "criticality": "medium",
      "estimated_impact": "Increased resource usage"
    }}
  ]
}}

Example 2 - Memory Leak:
{{
  "root_cause": "Memory leak causing OOM errors",
  "explanation": "The service memory usage has grown from 50MB to 800MB over 2 hours, indicating a memory leak",
  "confidence": 85,
  "contributing_factors": ["Unclosed connections", "Object accumulation"],
  "recommendations": [
    {{
      "action_type": "RESTART",
      "target_service": "worker-service",
      "target_type": "deployment",
      "parameters": {{}},
      "rationale": "Clear leaked memory and restore service to baseline",
      "criticality": "medium",
      "estimated_impact": "30 seconds restart time"
    }}
  ]
}}

Example 3 - Deployment Issue:
{{
  "root_cause": "New deployment introduced breaking changes",
  "explanation": "Error rate increased from 0.1% to 15% immediately after deployment v2.3.0",
  "confidence": 95,
  "contributing_factors": ["Untested code path", "Missing configuration"],
  "recommendations": [
    {{
      "action_type": "ROLLBACK",
      "target_service": "payment-service",
      "target_type": "deployment",
      "parameters": {{"to_version": "v2.2.0"}},
      "rationale": "Rollback to last known good version to restore service",
      "criticality": "critical",
      "estimated_impact": "Immediate error rate reduction"
    }}
  ]
}}

IMPORTANT RULES:
1. Only use action_type values: RESTART, SCALE, ROLLBACK, INVESTIGATE
2. Always include target_service (the exact service name from affected services)
3. Always include target_type (usually "deployment")
4. For SCALE actions, include "replicas" in parameters
5. For ROLLBACK actions, optionally include "to_version" in parameters
6. Criticality must be one of: low, medium, high, critical
7. If no safe automated action exists, use action_type: INVESTIGATE
8. Return valid JSON only, no markdown code blocks
9. If uncertain, set lower confidence and use INVESTIGATE action
10. Always provide at least ONE recommendation

Now analyze the incident above and provide your response in the exact JSON format specified.
"""


def build_analysis_prompt(
    service_name: str,
    metric_name: str,
    current_value: str,
    threshold: str,
    severity: str,
    affected_services: list,
    cluster: str,
    namespace: str,
    timestamp: str,
    logs: list = None,
    similar_incidents: list = None
) -> str:
    """
    Build analysis prompt from incident data

    Args:
        service_name: Name of the affected service
        metric_name: Metric that triggered the incident
        current_value: Current metric value
        threshold: Alert threshold
        severity: Incident severity
        affected_services: List of affected services
        cluster: Cluster name
        namespace: Namespace
        timestamp: Incident timestamp
        logs: Optional list of log lines
        similar_incidents: Optional list of similar past incidents

    Returns:
        Formatted prompt string
    """
    # Build logs section
    logs_section = ""
    if logs and len(logs) > 0:
        logs_section = "RECENT LOGS:\n"
        logs_section += "\n".join(logs[:20])  # Limit to 20 lines
        logs_section += "\n"

    # Build similar incidents section
    similar_incidents_section = ""
    if similar_incidents and len(similar_incidents) > 0:
        similar_incidents_section = "SIMILAR PAST INCIDENTS:\n"
        for idx, incident in enumerate(similar_incidents[:3], 1):
            similar_incidents_section += f"""
{idx}. {incident.get('description', 'No description')}
   - Root Cause: {incident.get('root_cause', 'Unknown')}
   - Resolution: {incident.get('resolution', 'Unknown')}
   - Similarity Score: {incident.get('score', 0):.2f}
"""

    # Format the prompt
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        service_name=service_name,
        metric_name=metric_name,
        current_value=current_value,
        threshold=threshold,
        severity=severity,
        affected_services=", ".join(affected_services) if affected_services else "unknown",
        cluster=cluster,
        namespace=namespace,
        timestamp=timestamp,
        logs_section=logs_section,
        similar_incidents_section=similar_incidents_section
    )

    return prompt
