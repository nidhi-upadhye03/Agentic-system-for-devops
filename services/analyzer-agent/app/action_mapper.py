"""
Action Mapper - Converts LLM output to structured recommendations

Implements multiple parsing strategies:
1. JSON parsing (preferred) - Parse structured JSON response
2. Regex extraction (fallback) - Extract from natural language
3. Keyword matching (last resort) - Basic keyword-based extraction
"""
import json
import re
import logging
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Valid action types for incident remediation"""
    RESTART = "restart"
    SCALE = "scale"
    ROLLBACK = "rollback"
    INVESTIGATE = "investigate"


class Recommendation:
    """Structured recommendation for incident remediation"""

    def __init__(
        self,
        action_type: str,
        target_service: str,
        target_type: str = "deployment",
        parameters: Dict[str, Any] = None,
        rationale: str = "",
        criticality: str = "medium",
        estimated_impact: str = ""
    ):
        self.action_type = action_type
        self.target_service = target_service
        self.target_type = target_type
        self.parameters = parameters or {}
        self.rationale = rationale
        self.criticality = criticality
        self.estimated_impact = estimated_impact

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.action_type,
            "action_type": self.action_type,  # For auto-response-agent compatibility
            "action": self.rationale,
            "target": self.target_service,
            "target_type": self.target_type,
            "criticality": self.criticality,
            "replicas": self.parameters.get("replicas"),
            "reasoning": self.rationale,
            "parameters": self.parameters
        }

    def __repr__(self):
        return f"Recommendation(action={self.action_type}, target={self.target_service})"


class ActionMapper:
    """Maps LLM output to structured recommendations"""

    @staticmethod
    def parse_llm_response(
        llm_output: str,
        fallback_service: str = "unknown"
    ) -> List[Recommendation]:
        """
        Parse LLM output and extract recommendations.
        Tries multiple parsing strategies in order:
        1. JSON parsing (preferred)
        2. Regex extraction (fallback)
        3. Keyword matching (last resort)

        Args:
            llm_output: Raw LLM response text
            fallback_service: Service name to use if not found in response

        Returns:
            List of Recommendation objects
        """
        recommendations = []

        # Strategy 1: Try JSON parsing
        try:
            recommendations = ActionMapper._parse_json(llm_output, fallback_service)
            if recommendations:
                logger.info(f"✓ Parsed LLM response: {len(recommendations)} recommendations found via JSON")
                return recommendations
        except Exception as e:
            logger.debug(f"JSON parsing failed: {e}")

        # Strategy 2: Try regex extraction
        try:
            recommendations = ActionMapper._parse_with_regex(llm_output, fallback_service)
            if recommendations:
                logger.info(f"✓ Parsed LLM response: {len(recommendations)} recommendations found via regex")
                return recommendations
        except Exception as e:
            logger.debug(f"Regex parsing failed: {e}")

        # Strategy 3: Keyword matching
        try:
            recommendations = ActionMapper._parse_with_keywords(llm_output, fallback_service)
            if recommendations:
                logger.info(f"✓ Parsed LLM response: {len(recommendations)} recommendations found via keywords")
                return recommendations
        except Exception as e:
            logger.debug(f"Keyword parsing failed: {e}")

        logger.warning("All parsing strategies failed, returning empty recommendations")
        return []

    @staticmethod
    def _parse_json(llm_output: str, fallback_service: str) -> List[Recommendation]:
        """
        Parse structured JSON response from LLM

        Args:
            llm_output: Raw LLM response
            fallback_service: Fallback service name

        Returns:
            List of Recommendation objects
        """
        # Remove markdown code blocks if present
        cleaned = re.sub(r'```json\s*|\s*```', '', llm_output, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        # Parse JSON
        data = json.loads(cleaned)

        recommendations = []

        # Check if recommendations are in the response
        if 'recommendations' in data and isinstance(data['recommendations'], list):
            for rec_data in data['recommendations']:
                try:
                    # Validate action type
                    action_type_raw = rec_data.get('action_type', '').upper()
                    if action_type_raw not in ['RESTART', 'SCALE', 'ROLLBACK', 'INVESTIGATE']:
                        logger.warning(f"Invalid action_type: {action_type_raw}")
                        continue

                    # Map to our enum
                    action_type = action_type_raw.lower()

                    # Extract fields
                    target_service = rec_data.get('target_service', fallback_service)
                    target_type = rec_data.get('target_type', 'deployment')
                    parameters = rec_data.get('parameters', {})
                    rationale = rec_data.get('rationale', '')
                    criticality = rec_data.get('criticality', 'medium')
                    estimated_impact = rec_data.get('estimated_impact', '')

                    rec = Recommendation(
                        action_type=action_type,
                        target_service=target_service,
                        target_type=target_type,
                        parameters=parameters,
                        rationale=rationale,
                        criticality=criticality,
                        estimated_impact=estimated_impact
                    )

                    if ActionMapper.validate_recommendation(rec):
                        recommendations.append(rec)
                        logger.debug(f"✓ Validated recommendation: {rec}")
                    else:
                        logger.warning(f"Failed validation: {rec}")

                except Exception as e:
                    logger.warning(f"Failed to parse recommendation: {e}")
                    continue

        return recommendations

    @staticmethod
    def _parse_with_regex(llm_output: str, fallback_service: str) -> List[Recommendation]:
        """
        Extract recommendations using regex patterns from natural language

        Args:
            llm_output: Raw LLM response
            fallback_service: Fallback service name

        Returns:
            List of Recommendation objects
        """
        recommendations = []

        # Pattern 1: "RESTART the api-service because..."
        restart_pattern = r'(?:RESTART|restart|Restart)\s+(?:the\s+)?([a-z0-9-]+)(?:\s+service)?.*?(?:because|due to|to|:)\s+([^.]+)'
        for match in re.finditer(restart_pattern, llm_output, re.IGNORECASE):
            service_name = match.group(1)
            rationale = match.group(2).strip()

            rec = Recommendation(
                action_type=ActionType.RESTART.value,
                target_service=service_name,
                target_type="deployment",
                parameters={},
                rationale=rationale,
                criticality="medium"
            )
            recommendations.append(rec)
            logger.debug(f"Extracted RESTART via regex: {service_name}")

        # Pattern 2: "SCALE the api-service to 3 replicas"
        scale_pattern = r'(?:SCALE|scale|Scale)\s+(?:the\s+)?([a-z0-9-]+).*?to\s+(\d+)\s+replica'
        for match in re.finditer(scale_pattern, llm_output, re.IGNORECASE):
            service_name = match.group(1)
            replicas = int(match.group(2))

            rec = Recommendation(
                action_type=ActionType.SCALE.value,
                target_service=service_name,
                target_type="deployment",
                parameters={"replicas": replicas},
                rationale=f"Scale to {replicas} replicas",
                criticality="medium"
            )
            recommendations.append(rec)
            logger.debug(f"Extracted SCALE via regex: {service_name} to {replicas}")

        # Pattern 3: "ROLLBACK api-service to version..."
        rollback_pattern = r'(?:ROLLBACK|rollback|Rollback)\s+(?:the\s+)?([a-z0-9-]+)(?:\s+to\s+version\s+([^\s]+))?'
        for match in re.finditer(rollback_pattern, llm_output, re.IGNORECASE):
            service_name = match.group(1)
            version = match.group(2) if match.group(2) else "previous"

            rec = Recommendation(
                action_type=ActionType.ROLLBACK.value,
                target_service=service_name,
                target_type="deployment",
                parameters={"to_version": version},
                rationale=f"Rollback to {version}",
                criticality="high"
            )
            recommendations.append(rec)
            logger.debug(f"Extracted ROLLBACK via regex: {service_name}")

        return recommendations

    @staticmethod
    def _parse_with_keywords(llm_output: str, fallback_service: str) -> List[Recommendation]:
        """
        Fallback: Extract service names and guess action from keywords

        Args:
            llm_output: Raw LLM response
            fallback_service: Fallback service name

        Returns:
            List of Recommendation objects
        """
        recommendations = []

        # Extract service names (common patterns: test-app, api-service, etc.)
        service_pattern = r'\b([a-z0-9]+-[a-z0-9]+(?:-[a-z0-9]+)?)\b'
        services_found = list(set(re.findall(service_pattern, llm_output, re.IGNORECASE)))

        if not services_found:
            services_found = [fallback_service]

        # Check for restart keywords
        if re.search(r'\brestart\b', llm_output, re.IGNORECASE):
            for service in services_found[:1]:  # Only first service
                rec = Recommendation(
                    action_type=ActionType.RESTART.value,
                    target_service=service,
                    target_type="deployment",
                    parameters={},
                    rationale="Extracted from natural language suggestion",
                    criticality="medium"
                )
                recommendations.append(rec)
                logger.debug(f"Extracted RESTART via keywords: {service}")

        # Check for scale keywords
        if re.search(r'\bscale\b|\bincrease\s+replica', llm_output, re.IGNORECASE):
            for service in services_found[:1]:
                # Try to extract replica count
                replica_match = re.search(r'(\d+)\s+replica', llm_output, re.IGNORECASE)
                replicas = int(replica_match.group(1)) if replica_match else 3

                rec = Recommendation(
                    action_type=ActionType.SCALE.value,
                    target_service=service,
                    target_type="deployment",
                    parameters={"replicas": replicas},
                    rationale="Extracted from natural language suggestion",
                    criticality="low"
                )
                recommendations.append(rec)
                logger.debug(f"Extracted SCALE via keywords: {service}")

        # Check for rollback keywords
        if re.search(r'\brollback\b', llm_output, re.IGNORECASE):
            for service in services_found[:1]:
                rec = Recommendation(
                    action_type=ActionType.ROLLBACK.value,
                    target_service=service,
                    target_type="deployment",
                    parameters={},
                    rationale="Extracted from natural language suggestion",
                    criticality="high"
                )
                recommendations.append(rec)
                logger.debug(f"Extracted ROLLBACK via keywords: {service}")

        return recommendations

    @staticmethod
    def validate_recommendation(rec: Recommendation) -> bool:
        """
        Validate that recommendation is safe to execute

        Args:
            rec: Recommendation to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if not rec.target_service or rec.target_service == "unknown":
            logger.warning(f"Invalid recommendation: missing target_service")
            return False

        # Validate action type
        valid_actions = [ActionType.RESTART.value, ActionType.SCALE.value,
                        ActionType.ROLLBACK.value, ActionType.INVESTIGATE.value]
        if rec.action_type not in valid_actions:
            logger.warning(f"Invalid recommendation: unknown action_type {rec.action_type}")
            return False

        # Service name must be alphanumeric with hyphens only
        if not re.match(r'^[a-z0-9-]+$', rec.target_service, re.IGNORECASE):
            logger.warning(f"Invalid recommendation: invalid service name {rec.target_service}")
            return False

        # Skip INVESTIGATE actions (not executable)
        if rec.action_type == ActionType.INVESTIGATE.value:
            logger.debug(f"Skipping INVESTIGATE action: {rec.rationale}")
            return False

        return True
