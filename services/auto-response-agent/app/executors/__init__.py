"""
Executor Module - Abstraction for executing remediation actions

This module provides a unified interface for executing actions across different
orchestration platforms (Docker Compose, Kubernetes, etc.).

Exports:
    - BaseExecutor: Abstract base class for all executors
    - ExecutionResult: Standardized result object
    - ActionType: Enum of supported action types
    - ExecutorFactory: Factory for creating appropriate executor instances
    - DockerComposeExecutor: Docker Compose executor implementation
    - K8sExecutor: Kubernetes executor implementation
"""

from .base import BaseExecutor, ExecutionResult, ActionType
from .factory import ExecutorFactory
from .docker_executor import DockerComposeExecutor
from .k8s_executor import K8sExecutor

__all__ = [
    'BaseExecutor',
    'ExecutionResult',
    'ActionType',
    'ExecutorFactory',
    'DockerComposeExecutor',
    'K8sExecutor',
]
