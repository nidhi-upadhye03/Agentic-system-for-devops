"""
Action Validator Module

Validates recommended actions before execution with comprehensive safety checks.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ActionValidator:
    """Validate and assess safety of recommended actions"""

    def __init__(
        self,
        auto_execute_threshold: int = 95,
        require_approval_actions: List[str] = None,
        require_approval_criticality: List[str] = None,
        max_scale_replicas: int = 10,
        min_scale_replicas: int = 1
    ):
        """
        Initialize action validator

        Args:
            auto_execute_threshold: Confidence threshold for auto-execution (%)
            require_approval_actions: Actions that always require approval
            require_approval_criticality: Criticality levels requiring approval
            max_scale_replicas: Maximum allowed replica count
            min_scale_replicas: Minimum allowed replica count
        """
        self.auto_execute_threshold = auto_execute_threshold
        self.require_approval_actions = require_approval_actions or [
            "rollback_deployment",
            "delete_pods",
            "update_config",
            "scale_down_critical"
        ]
        self.require_approval_criticality = require_approval_criticality or [
            "critical",
            "high"
        ]
        self.max_scale_replicas = max_scale_replicas
        self.min_scale_replicas = min_scale_replicas

        # Track recent actions to prevent action storms
        self.recent_actions: Dict[str, List[datetime]] = {}
        self.action_cooldown = timedelta(minutes=5)
        self.max_actions_per_target = 3  # Max actions per target in cooldown period

    async def validate_recommendation(
        self,
        recommendation: Dict[str, Any],
        incident: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a single recommendation

        Args:
            recommendation: Recommended action details
            incident: Source incident details
            analysis: Analysis results

        Returns:
            Validation result with decision and reasoning
        """
        action_type = recommendation.get("action_type")
        target = recommendation.get("target")
        confidence = recommendation.get("confidence", 0)
        criticality = incident.get("severity", "medium")

        logger.info(f"Validating recommendation: {action_type} on {target} (confidence: {confidence}%)")

        # Safety checks
        validation_results = []

        # 1. Check if action type is allowed
        if not self._is_action_type_valid(action_type):
            return {
                "valid": False,
                "requires_approval": True,
                "auto_execute": False,
                "reason": f"Unknown or disallowed action type: {action_type}",
                "checks_passed": 0,
                "checks_failed": 1
            }

        # 2. Check confidence threshold
        confidence_check = self._check_confidence(confidence, action_type, criticality)
        validation_results.append(confidence_check)

        # 3. Check action parameters
        params_check = self._check_action_parameters(action_type, recommendation)
        validation_results.append(params_check)

        # 4. Check action cooldown (prevent action storms)
        cooldown_check = self._check_action_cooldown(target, action_type)
        validation_results.append(cooldown_check)

        # 5. Check criticality requirements
        criticality_check = self._check_criticality_requirements(action_type, criticality)
        validation_results.append(criticality_check)

        # 6. Check mandatory approval actions
        approval_check = self._check_mandatory_approval(action_type)
        validation_results.append(approval_check)

        # Aggregate results
        checks_passed = sum(1 for c in validation_results if c["passed"])
        checks_failed = len(validation_results) - checks_passed

        # Determine if action is valid
        all_checks_passed = all(c["passed"] for c in validation_results)

        # Determine if approval is required
        requires_approval = any(
            c.get("requires_approval", False) for c in validation_results
        )

        # Determine if auto-execution is allowed
        auto_execute = (
            all_checks_passed and
            not requires_approval and
            confidence >= self.auto_execute_threshold
        )

        # Build validation summary
        reasons = [c["reason"] for c in validation_results if not c["passed"]]
        approval_reasons = [
            c["reason"] for c in validation_results
            if c.get("requires_approval", False)
        ]

        result = {
            "valid": all_checks_passed,
            "requires_approval": requires_approval,
            "auto_execute": auto_execute,
            "checks_passed": checks_passed,
            "checks_failed": checks_failed,
            "validation_details": validation_results,
            "timestamp": datetime.utcnow().isoformat()
        }

        if reasons:
            result["failure_reasons"] = reasons

        if approval_reasons:
            result["approval_reasons"] = approval_reasons
        elif requires_approval:
            result["approval_reasons"] = ["Action requires human approval"]

        if not reasons and not approval_reasons:
            result["reason"] = "All safety checks passed"

        logger.info(
            f"Validation result: valid={result['valid']}, "
            f"requires_approval={requires_approval}, "
            f"auto_execute={auto_execute}"
        )

        return result

    def _is_action_type_valid(self, action_type: str) -> bool:
        """Check if action type is recognized and allowed"""
        allowed_actions = [
            "scale_deployment",
            "restart_pods",
            "rollback_deployment",
            "update_config",
            "increase_resources",
            "clear_cache"
        ]
        return action_type in allowed_actions

    def _check_confidence(
        self,
        confidence: int,
        action_type: str,
        criticality: str
    ) -> Dict[str, Any]:
        """Check if confidence level is sufficient"""
        # Higher confidence required for critical actions
        if criticality in ["critical", "high"]:
            min_confidence = 80
        else:
            min_confidence = 70

        passed = confidence >= min_confidence

        return {
            "check": "confidence_threshold",
            "passed": passed,
            "reason": (
                f"Confidence {confidence}% meets minimum {min_confidence}%" if passed
                else f"Confidence {confidence}% below minimum {min_confidence}%"
            ),
            "requires_approval": not passed or confidence < self.auto_execute_threshold
        }

    def _check_action_parameters(
        self,
        action_type: str,
        recommendation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate action-specific parameters"""
        params = recommendation.get("parameters", {})

        if action_type == "scale_deployment":
            replicas = params.get("replicas")

            if replicas is None:
                return {
                    "check": "action_parameters",
                    "passed": False,
                    "reason": "Missing required parameter: replicas",
                    "requires_approval": False
                }

            if not isinstance(replicas, int) or replicas < 0:
                return {
                    "check": "action_parameters",
                    "passed": False,
                    "reason": f"Invalid replica count: {replicas}",
                    "requires_approval": False
                }

            if replicas < self.min_scale_replicas or replicas > self.max_scale_replicas:
                return {
                    "check": "action_parameters",
                    "passed": False,
                    "reason": (
                        f"Replica count {replicas} outside safe range "
                        f"[{self.min_scale_replicas}, {self.max_scale_replicas}]"
                    ),
                    "requires_approval": True
                }

        # Add more parameter validation for other action types as needed

        return {
            "check": "action_parameters",
            "passed": True,
            "reason": "Action parameters are valid",
            "requires_approval": False
        }

    def _check_action_cooldown(
        self,
        target: str,
        action_type: str
    ) -> Dict[str, Any]:
        """Check if we're performing too many actions on same target"""
        now = datetime.utcnow()
        key = f"{target}:{action_type}"

        # Clean up old entries
        if key in self.recent_actions:
            self.recent_actions[key] = [
                ts for ts in self.recent_actions[key]
                if now - ts < self.action_cooldown
            ]

        # Check action count
        recent_count = len(self.recent_actions.get(key, []))

        if recent_count >= self.max_actions_per_target:
            return {
                "check": "action_cooldown",
                "passed": False,
                "reason": (
                    f"Too many {action_type} actions on {target} "
                    f"({recent_count} in last {self.action_cooldown.seconds // 60} minutes). "
                    "Possible action storm."
                ),
                "requires_approval": True
            }

        return {
            "check": "action_cooldown",
            "passed": True,
            "reason": f"Action cooldown check passed ({recent_count}/{self.max_actions_per_target})",
            "requires_approval": False
        }

    def _check_criticality_requirements(
        self,
        action_type: str,
        criticality: str
    ) -> Dict[str, Any]:
        """Check if criticality level requires approval"""
        requires_approval = criticality in self.require_approval_criticality

        return {
            "check": "criticality_requirements",
            "passed": True,  # Always pass, but may require approval
            "reason": (
                f"{criticality.upper()} criticality requires approval"
                if requires_approval
                else f"{criticality.upper()} criticality allows auto-execution"
            ),
            "requires_approval": requires_approval
        }

    def _check_mandatory_approval(self, action_type: str) -> Dict[str, Any]:
        """Check if action type mandates approval"""
        requires_approval = action_type in self.require_approval_actions

        return {
            "check": "mandatory_approval",
            "passed": True,  # Always pass, but may require approval
            "reason": (
                f"Action type '{action_type}' requires mandatory approval"
                if requires_approval
                else f"Action type '{action_type}' does not require mandatory approval"
            ),
            "requires_approval": requires_approval
        }

    def record_action(self, target: str, action_type: str):
        """Record an action for cooldown tracking"""
        key = f"{target}:{action_type}"
        if key not in self.recent_actions:
            self.recent_actions[key] = []

        self.recent_actions[key].append(datetime.utcnow())
        logger.debug(f"Recorded action: {key}")

    async def validate_batch(
        self,
        recommendations: List[Dict[str, Any]],
        incident: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple recommendations

        Args:
            recommendations: List of recommended actions
            incident: Source incident
            analysis: Analysis results

        Returns:
            List of validation results
        """
        results = []

        for recommendation in recommendations:
            result = await self.validate_recommendation(
                recommendation,
                incident,
                analysis
            )
            result["recommendation"] = recommendation
            results.append(result)

        logger.info(
            f"Validated {len(results)} recommendations: "
            f"{sum(1 for r in results if r['auto_execute'])} can auto-execute, "
            f"{sum(1 for r in results if r['requires_approval'])} require approval"
        )

        return results

    def get_validation_summary(
        self,
        validation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate summary of validation results

        Args:
            validation_results: List of validation results

        Returns:
            Summary statistics
        """
        total = len(validation_results)
        valid = sum(1 for r in validation_results if r["valid"])
        auto_execute = sum(1 for r in validation_results if r["auto_execute"])
        requires_approval = sum(1 for r in validation_results if r["requires_approval"])
        failed = total - valid

        return {
            "total_recommendations": total,
            "valid_recommendations": valid,
            "invalid_recommendations": failed,
            "auto_executable": auto_execute,
            "requires_approval": requires_approval,
            "timestamp": datetime.utcnow().isoformat()
        }
