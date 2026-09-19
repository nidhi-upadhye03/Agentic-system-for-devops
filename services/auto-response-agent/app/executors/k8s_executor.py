"""
Kubernetes Executor - Executes remediation actions on Kubernetes clusters

This module implements the BaseExecutor interface for Kubernetes environments.
It uses the Kubernetes Python client to perform operations like scaling,
restarting pods, and rolling back deployments.

Classes:
    - K8sExecutor: Kubernetes executor implementation
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from .base import BaseExecutor, ExecutionResult, ActionType

logger = logging.getLogger(__name__)


class K8sExecutor(BaseExecutor):
    """
    Executor implementation for Kubernetes clusters

    Uses Kubernetes Python client to execute remediation actions on
    deployments, pods, and other Kubernetes resources.
    """

    def __init__(
        self,
        in_cluster: bool = False,
        namespace: str = "default",
        kubeconfig_path: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize Kubernetes executor

        Args:
            in_cluster: Whether running inside K8s cluster
            namespace: Default namespace for operations
            kubeconfig_path: Path to kubeconfig file (optional)
            dry_run: If True, only simulate operations (no actual changes)
        """
        super().__init__(dry_run=dry_run)
        self.namespace = namespace
        self.kubeconfig_path = kubeconfig_path
        self.in_cluster = in_cluster
        self.available = False
        self.apps_v1 = None
        self.core_v1 = None

        self._initialize_client()

    def _initialize_client(self):
        """Initialize Kubernetes client"""
        try:
            if self.in_cluster:
                k8s_config.load_incluster_config()
                logger.info("✓ Loaded in-cluster Kubernetes configuration")
            else:
                if self.kubeconfig_path:
                    k8s_config.load_kube_config(config_file=self.kubeconfig_path)
                    logger.info(f"✓ Loaded kubeconfig from {self.kubeconfig_path}")
                else:
                    k8s_config.load_kube_config()
                    logger.info("✓ Loaded kubeconfig from default location")

            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            self.available = True

        except Exception as e:
            logger.warning(f"Kubernetes client not available: {e}")
            logger.warning("Running in degraded mode - K8s operations will fail")
            self.available = False

    async def restart(
        self,
        target: str,
        namespace: Optional[str] = None,
        grace_period: int = 30,
        **kwargs
    ) -> ExecutionResult:
        """
        Restart pods in a deployment by deleting them (K8s recreates automatically)

        Args:
            target: Deployment name
            namespace: Namespace (uses default if None)
            grace_period: Grace period for pod deletion (seconds)
            **kwargs: Additional parameters (label_selector)

        Returns:
            ExecutionResult with restart details
        """
        start_time = time.time()
        ns = namespace or self.namespace

        if not self.available:
            return self._create_result(
                action=ActionType.RESTART.value,
                status="failed",
                target=target,
                namespace=ns,
                execution_time=time.time() - start_time,
                error="Kubernetes client not available"
            )

        try:
            # Get pods for this deployment
            label_selector = kwargs.get('label_selector', f"app={target}")
            pods = self.core_v1.list_namespaced_pod(
                namespace=ns,
                label_selector=label_selector
            )

            if not pods.items:
                logger.warning(f"No pods found for deployment {target}")
                return self._create_result(
                    action=ActionType.RESTART.value,
                    status="skipped",
                    target=target,
                    namespace=ns,
                    execution_time=time.time() - start_time,
                    details={"reason": "No pods found", "label_selector": label_selector}
                )

            logger.info(f"Restarting {len(pods.items)} pods for deployment {target}")

            if self.dry_run:
                logger.info("[DRY RUN] Would restart pods (no actual change)")
                return self._create_result(
                    action=ActionType.RESTART.value,
                    status="dry_run",
                    target=target,
                    namespace=ns,
                    execution_time=time.time() - start_time,
                    details={
                        "pods_to_restart": [p.metadata.name for p in pods.items],
                        "count": len(pods.items)
                    }
                )

            # Delete pods (K8s will recreate them)
            restarted = []
            for pod in pods.items:
                self.core_v1.delete_namespaced_pod(
                    name=pod.metadata.name,
                    namespace=ns,
                    grace_period_seconds=grace_period
                )
                restarted.append(pod.metadata.name)
                logger.info(f"✓ Deleted pod {pod.metadata.name} (will be recreated)")

            logger.info(f"✓ Restarted {len(restarted)} pods for deployment {target}")

            return self._create_result(
                action=ActionType.RESTART.value,
                status="success",
                target=target,
                namespace=ns,
                execution_time=time.time() - start_time,
                details={
                    "pods_restarted": restarted,
                    "count": len(restarted),
                    "grace_period": grace_period
                }
            )

        except ApiException as e:
            logger.error(f"Failed to restart pods for {target}: {e}")
            return self._create_result(
                action=ActionType.RESTART.value,
                status="failed",
                target=target,
                namespace=ns,
                execution_time=time.time() - start_time,
                error=str(e)
            )

    async def scale(
        self,
        target: str,
        replicas: int,
        namespace: Optional[str] = None,
        min_replicas: int = 1,
        max_replicas: int = 10,
        **kwargs
    ) -> ExecutionResult:
        """
        Scale a deployment to target replica count

        Args:
            target: Deployment name
            replicas: Target replica count
            namespace: Namespace (uses default if None)
            min_replicas: Minimum allowed replicas
            max_replicas: Maximum allowed replicas
            **kwargs: Additional parameters

        Returns:
            ExecutionResult with scaling details
        """
        start_time = time.time()
        ns = namespace or self.namespace

        if not self.available:
            return self._create_result(
                action=ActionType.SCALE.value,
                status="failed",
                target=target,
                namespace=ns,
                execution_time=time.time() - start_time,
                error="Kubernetes client not available"
            )

        # Validate and clamp replica count
        replicas = self._validate_replicas(replicas, min_replicas, max_replicas)

        try:
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(target, ns)
            old_replicas = deployment.spec.replicas

            logger.info(f"Scaling deployment {target} from {old_replicas} to {replicas} replicas")

            if self.dry_run:
                logger.info("[DRY RUN] Would scale deployment (no actual change)")
                return self._create_result(
                    action=ActionType.SCALE.value,
                    status="dry_run",
                    target=target,
                    namespace=ns,
                    execution_time=time.time() - start_time,
                    details={
                        "old_replicas": old_replicas,
                        "new_replicas": replicas
                    }
                )

            # Update replica count
            deployment.spec.replicas = replicas

            # Apply update
            self.apps_v1.patch_namespaced_deployment(
                name=target,
                namespace=ns,
                body=deployment
            )

            logger.info(f"✓ Scaled deployment {target} to {replicas} replicas")

            return self._create_result(
                action=ActionType.SCALE.value,
                status="success",
                target=target,
                namespace=ns,
                execution_time=time.time() - start_time,
                details={
                    "old_replicas": old_replicas,
                    "new_replicas": replicas
                }
            )

        except ApiException as e:
            logger.error(f"Failed to scale deployment {target}: {e}")
            return self._create_result(
                action=ActionType.SCALE.value,
                status="failed",
                target=target,
                namespace=ns,
                execution_time=time.time() - start_time,
                error=str(e)
            )

    async def rollback(
        self,
        target: str,
        namespace: Optional[str] = None,
        revision: Optional[int] = None,
        **kwargs
    ) -> ExecutionResult:
        """
        Rollback deployment to previous revision

        Note: Python K8s client doesn't have native rollback API.
        This triggers a restart with rollback annotation.
        For production, use kubectl rollout undo or implement full rollback logic.

        Args:
            target: Deployment name
            namespace: Namespace (uses default if None)
            revision: Specific revision to rollback to (None = previous)
            **kwargs: Additional parameters

        Returns:
            ExecutionResult with rollback details
        """
        start_time = time.time()
        ns = namespace or self.namespace
        target_revision = revision or 0  # 0 means previous

        if not self.available:
            return self._create_result(
                action=ActionType.ROLLBACK.value,
                status="failed",
                target=target,
                namespace=ns,
                execution_time=time.time() - start_time,
                error="Kubernetes client not available"
            )

        try:
            logger.info(f"Rolling back deployment {target} to revision {target_revision or 'previous'}")

            if self.dry_run:
                logger.info("[DRY RUN] Would rollback deployment (no actual change)")
                return self._create_result(
                    action=ActionType.ROLLBACK.value,
                    status="dry_run",
                    target=target,
                    namespace=ns,
                    execution_time=time.time() - start_time,
                    details={"target_revision": target_revision}
                )

            deployment = self.apps_v1.read_namespaced_deployment(target, ns)

            # Add rollback annotation to trigger restart
            if not deployment.metadata.annotations:
                deployment.metadata.annotations = {}

            deployment.metadata.annotations["kubectl.kubernetes.io/restartedAt"] = datetime.utcnow().isoformat()

            self.apps_v1.patch_namespaced_deployment(
                name=target,
                namespace=ns,
                body=deployment
            )

            logger.info(f"✓ Triggered rollback for deployment {target}")

            return self._create_result(
                action=ActionType.ROLLBACK.value,
                status="success",
                target=target,
                namespace=ns,
                execution_time=time.time() - start_time,
                details={
                    "target_revision": target_revision,
                    "note": "Triggered restart - for full rollback, use kubectl rollout undo"
                }
            )

        except ApiException as e:
            logger.error(f"Failed to rollback deployment {target}: {e}")
            return self._create_result(
                action=ActionType.ROLLBACK.value,
                status="failed",
                target=target,
                namespace=ns,
                execution_time=time.time() - start_time,
                error=str(e)
            )

    async def health_check(self) -> bool:
        """
        Check if Kubernetes executor is available and healthy

        Returns:
            True if K8s client can connect and execute operations
        """
        if not self.available:
            return False

        try:
            # Try to list namespaces as a health check
            self.core_v1.list_namespace(limit=1)
            return True
        except Exception as e:
            logger.warning(f"K8s health check failed: {e}")
            return False

    def get_executor_type(self) -> str:
        """Get executor type identifier"""
        return "kubernetes"

    async def get_status(
        self,
        target: str,
        namespace: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get current deployment status

        Args:
            target: Deployment name
            namespace: Namespace (uses default if None)
            **kwargs: Additional parameters

        Returns:
            Dictionary with deployment status details
        """
        ns = namespace or self.namespace

        if not self.available:
            return {
                "name": target,
                "namespace": ns,
                "error": "Kubernetes client not available",
                "timestamp": datetime.utcnow().isoformat()
            }

        try:
            deployment = self.apps_v1.read_namespaced_deployment(target, ns)

            return {
                "name": target,
                "namespace": ns,
                "replicas": {
                    "desired": deployment.spec.replicas,
                    "current": deployment.status.replicas,
                    "ready": deployment.status.ready_replicas,
                    "available": deployment.status.available_replicas
                },
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message
                    }
                    for c in (deployment.status.conditions or [])
                ],
                "timestamp": datetime.utcnow().isoformat()
            }

        except ApiException as e:
            logger.error(f"Failed to get deployment status for {target}: {e}")
            return {
                "name": target,
                "namespace": ns,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def is_available(self) -> bool:
        """
        Check if K8s client is available (backward compatibility)

        Returns:
            True if client is initialized and available
        """
        return self.available

    async def validate_action(
        self,
        action_type: str,
        target: str,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate if an action can be performed (backward compatibility)

        Args:
            action_type: Type of action (scale, restart, rollback)
            target: Target deployment name
            namespace: Namespace

        Returns:
            Validation result dictionary
        """
        if not self.available:
            return {
                "valid": False,
                "reason": "Kubernetes client not available"
            }

        ns = namespace or self.namespace

        try:
            # Check if deployment exists
            deployment = self.apps_v1.read_namespaced_deployment(target, ns)

            # Check if deployment is healthy
            if not deployment.status.available_replicas:
                return {
                    "valid": False,
                    "reason": f"Deployment {target} has no available replicas"
                }

            return {
                "valid": True,
                "deployment": target,
                "namespace": ns,
                "current_replicas": deployment.spec.replicas
            }

        except ApiException as e:
            return {
                "valid": False,
                "reason": f"Deployment {target} not found: {str(e)}"
            }
