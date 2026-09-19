"""
Executor Factory - Auto-detects environment and creates appropriate executor

This module provides factory methods to automatically detect the execution
environment (Docker Compose vs Kubernetes) and instantiate the appropriate
executor implementation.

Detection Logic:
    1. Check EXECUTOR_TYPE environment variable (explicit override)
    2. Check KUBERNETES_SERVICE_HOST (running in K8s cluster)
    3. Check for ~/.kube/config (K8s client configured)
    4. Check for /var/run/docker.sock (Docker available)
    5. Default to Docker Compose

Classes:
    - ExecutorFactory: Factory for creating executor instances
"""

import os
import logging
from typing import Optional
from pathlib import Path

from .base import BaseExecutor
from .docker_executor import DockerComposeExecutor
from .k8s_executor import K8sExecutor

logger = logging.getLogger(__name__)


class ExecutorFactory:
    """
    Factory class for creating appropriate executor instances

    This factory automatically detects the execution environment and returns
    the appropriate executor implementation (Docker Compose or Kubernetes).
    """

    @staticmethod
    def create_executor(
        executor_type: Optional[str] = None,
        dry_run: bool = False,
        **kwargs
    ) -> BaseExecutor:
        """
        Create an executor instance based on environment detection

        Args:
            executor_type: Explicit executor type ("docker-compose" or "kubernetes").
                          If None, auto-detection is performed.
            dry_run: If True, executor will simulate actions without executing
            **kwargs: Additional executor-specific configuration:
                - For Docker: compose_file, project_name
                - For K8s: in_cluster, namespace, kubeconfig_path

        Returns:
            BaseExecutor: Appropriate executor instance

        Raises:
            ValueError: If invalid executor_type is specified

        Example:
            # Auto-detect environment
            executor = ExecutorFactory.create_executor()

            # Explicit Docker Compose
            executor = ExecutorFactory.create_executor(
                executor_type="docker-compose",
                compose_file="/app/docker-compose.yml"
            )

            # Explicit Kubernetes
            executor = ExecutorFactory.create_executor(
                executor_type="kubernetes",
                namespace="production"
            )
        """
        # If explicit type provided, use it
        if executor_type:
            executor_type = executor_type.lower()
            logger.info(f"Using explicit executor type: {executor_type}")

            if executor_type == "docker-compose":
                return ExecutorFactory._create_docker_executor(dry_run, **kwargs)
            elif executor_type == "kubernetes":
                return ExecutorFactory._create_k8s_executor(dry_run, **kwargs)
            else:
                raise ValueError(
                    f"Invalid executor_type: {executor_type}. "
                    f"Must be 'docker-compose' or 'kubernetes'"
                )

        # Auto-detect environment
        detected_type = ExecutorFactory._auto_detect_executor()
        logger.info(f"Auto-detected executor type: {detected_type}")

        if detected_type == "docker-compose":
            return ExecutorFactory._create_docker_executor(dry_run, **kwargs)
        else:
            return ExecutorFactory._create_k8s_executor(dry_run, **kwargs)

    @staticmethod
    def _create_docker_executor(dry_run: bool = False, **kwargs) -> DockerComposeExecutor:
        """
        Create Docker Compose executor instance

        Args:
            dry_run: Dry run mode
            **kwargs: Docker-specific config (compose_file, project_name)

        Returns:
            DockerComposeExecutor instance
        """
        compose_file = kwargs.get('compose_file') or os.getenv(
            'DOCKER_COMPOSE_FILE',
            '/compose/docker-compose.yml'
        )
        project_name = kwargs.get('project_name') or os.getenv(
            'DOCKER_COMPOSE_PROJECT'
        )

        logger.info(
            f"Creating DockerComposeExecutor: "
            f"compose_file={compose_file}, project_name={project_name}, "
            f"dry_run={dry_run}"
        )

        return DockerComposeExecutor(
            compose_file=compose_file,
            project_name=project_name,
            dry_run=dry_run
        )

    @staticmethod
    def _create_k8s_executor(dry_run: bool = False, **kwargs) -> K8sExecutor:
        """
        Create Kubernetes executor instance

        Args:
            dry_run: Dry run mode
            **kwargs: K8s-specific config (in_cluster, namespace, kubeconfig_path)

        Returns:
            K8sExecutor instance
        """
        # Check if running in-cluster
        in_cluster = kwargs.get('in_cluster')
        if in_cluster is None:
            in_cluster = os.getenv('KUBERNETES_SERVICE_HOST') is not None

        namespace = kwargs.get('namespace') or os.getenv(
            'K8S_NAMESPACE',
            'default'
        )

        kubeconfig_path = kwargs.get('kubeconfig_path') or os.getenv(
            'KUBECONFIG'
        )

        logger.info(
            f"Creating K8sExecutor: "
            f"in_cluster={in_cluster}, namespace={namespace}, "
            f"kubeconfig_path={kubeconfig_path}, dry_run={dry_run}"
        )

        return K8sExecutor(
            in_cluster=in_cluster,
            namespace=namespace,
            kubeconfig_path=kubeconfig_path,
            dry_run=dry_run
        )

    @staticmethod
    def _auto_detect_executor() -> str:
        """
        Auto-detect which executor to use based on environment

        Detection logic (in priority order):
            1. EXECUTOR_TYPE env var (explicit override)
            2. KUBERNETES_SERVICE_HOST env var (running in K8s)
            3. ~/.kube/config file exists (K8s client configured)
            4. /var/run/docker.sock exists (Docker available)
            5. Default to docker-compose

        Returns:
            str: "docker-compose" or "kubernetes"
        """
        # 1. Check explicit environment variable override
        executor_type_env = os.getenv('EXECUTOR_TYPE')
        if executor_type_env:
            executor_type_env = executor_type_env.lower()
            if executor_type_env in ['docker-compose', 'docker', 'compose']:
                logger.info("EXECUTOR_TYPE env var set to docker-compose")
                return "docker-compose"
            elif executor_type_env in ['kubernetes', 'k8s', 'kube']:
                logger.info("EXECUTOR_TYPE env var set to kubernetes")
                return "kubernetes"
            else:
                logger.warning(
                    f"Invalid EXECUTOR_TYPE value: {executor_type_env}. "
                    f"Continuing with auto-detection."
                )

        # 2. Check if running inside Kubernetes cluster
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            logger.info("Detected KUBERNETES_SERVICE_HOST - running in K8s cluster")
            return "kubernetes"

        # 3. Check for kubeconfig file
        kubeconfig_path = os.getenv('KUBECONFIG') or os.path.expanduser('~/.kube/config')
        if os.path.exists(kubeconfig_path):
            logger.info(f"Detected kubeconfig at {kubeconfig_path}")
            return "kubernetes"

        # 4. Check for Docker socket
        docker_sock = '/var/run/docker.sock'
        if os.path.exists(docker_sock):
            logger.info(f"Detected Docker socket at {docker_sock}")
            return "docker-compose"

        # 5. Default to Docker Compose
        logger.info(
            "No K8s or Docker environment detected. "
            "Defaulting to docker-compose"
        )
        return "docker-compose"

    @staticmethod
    def get_available_executors() -> dict:
        """
        Check which executors are available in the current environment

        Returns:
            dict: Dictionary with availability status for each executor type
                {
                    "docker-compose": {"available": bool, "reason": str},
                    "kubernetes": {"available": bool, "reason": str},
                    "detected": str  # Auto-detected executor type
                }

        Example:
            >>> ExecutorFactory.get_available_executors()
            {
                "docker-compose": {
                    "available": True,
                    "reason": "Docker socket found at /var/run/docker.sock"
                },
                "kubernetes": {
                    "available": False,
                    "reason": "No kubeconfig found"
                },
                "detected": "docker-compose"
            }
        """
        result = {}

        # Check Docker Compose availability
        docker_sock = '/var/run/docker.sock'
        if os.path.exists(docker_sock):
            result["docker-compose"] = {
                "available": True,
                "reason": f"Docker socket found at {docker_sock}"
            }
        else:
            result["docker-compose"] = {
                "available": False,
                "reason": f"Docker socket not found at {docker_sock}"
            }

        # Check Kubernetes availability
        k8s_reasons = []
        k8s_available = False

        if os.getenv('KUBERNETES_SERVICE_HOST'):
            k8s_available = True
            k8s_reasons.append("Running in K8s cluster (KUBERNETES_SERVICE_HOST set)")

        kubeconfig_path = os.getenv('KUBECONFIG') or os.path.expanduser('~/.kube/config')
        if os.path.exists(kubeconfig_path):
            k8s_available = True
            k8s_reasons.append(f"Kubeconfig found at {kubeconfig_path}")

        if k8s_available:
            result["kubernetes"] = {
                "available": True,
                "reason": "; ".join(k8s_reasons)
            }
        else:
            result["kubernetes"] = {
                "available": False,
                "reason": "No K8s environment detected (no KUBERNETES_SERVICE_HOST, no kubeconfig)"
            }

        # Add detected type
        result["detected"] = ExecutorFactory._auto_detect_executor()

        return result
