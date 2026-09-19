"""
Base Executor - Abstract interface for all executor implementations

This module defines the abstract base class that all executor implementations
must inherit from. It provides a consistent interface for executing remediation
actions regardless of the underlying orchestration platform.

Classes:
    - ActionType: Enum of supported action types
    - ExecutionResult: Standardized result object
    - BaseExecutor: Abstract base class for executors
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


class ActionType(Enum):
    """Supported action types for remediation"""
    RESTART = "restart"
    SCALE = "scale"
    ROLLBACK = "rollback"
    HEALTH_CHECK = "health_check"


@dataclass
class ExecutionResult:
    """
    Standardized result object for all executor operations

    Attributes:
        action: Action type that was executed
        status: Execution status (success, failed, dry_run, skipped)
        target: Target service/deployment name
        namespace: Namespace/environment (optional)
        executor_type: Type of executor used (docker-compose, kubernetes)
        timestamp: When the action was executed
        execution_time: How long the action took (seconds)
        details: Additional details about the execution
        error: Error message if failed (optional)
        metadata: Additional metadata (optional)
    """
    action: str
    status: str
    target: str
    executor_type: str
    timestamp: str
    execution_time: float
    details: Dict[str, Any] = field(default_factory=dict)
    namespace: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "action": self.action,
            "status": self.status,
            "target": self.target,
            "namespace": self.namespace,
            "executor_type": self.executor_type,
            "timestamp": self.timestamp,
            "execution_time": self.execution_time,
            "details": self.details,
            "error": self.error,
            "metadata": self.metadata
        }

    def is_success(self) -> bool:
        """Check if execution was successful"""
        return self.status == "success"

    def is_failure(self) -> bool:
        """Check if execution failed"""
        return self.status == "failed"


class BaseExecutor(ABC):
    """
    Abstract base class for all executor implementations

    All concrete executor classes (DockerComposeExecutor, K8sExecutor, etc.)
    must inherit from this class and implement all abstract methods.

    This ensures a consistent interface across different orchestration platforms.
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize base executor

        Args:
            dry_run: If True, simulate actions without actually executing them
        """
        self.dry_run = dry_run

    @abstractmethod
    async def restart(
        self,
        target: str,
        namespace: Optional[str] = None,
        grace_period: int = 30,
        **kwargs
    ) -> ExecutionResult:
        """
        Restart a service/deployment

        Args:
            target: Service or deployment name to restart
            namespace: Namespace/environment (optional)
            grace_period: Grace period for graceful shutdown (seconds)
            **kwargs: Additional executor-specific parameters

        Returns:
            ExecutionResult with status and details

        Raises:
            RuntimeError: If restart fails
        """
        pass

    @abstractmethod
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
        Scale a service/deployment to target replica count

        Args:
            target: Service or deployment name to scale
            replicas: Target replica count
            namespace: Namespace/environment (optional)
            min_replicas: Minimum allowed replicas (safety check)
            max_replicas: Maximum allowed replicas (safety check)
            **kwargs: Additional executor-specific parameters

        Returns:
            ExecutionResult with status and details

        Raises:
            RuntimeError: If scaling fails
            ValueError: If replicas out of bounds
        """
        pass

    @abstractmethod
    async def rollback(
        self,
        target: str,
        namespace: Optional[str] = None,
        revision: Optional[int] = None,
        **kwargs
    ) -> ExecutionResult:
        """
        Rollback a deployment to previous revision

        Args:
            target: Service or deployment name to rollback
            namespace: Namespace/environment (optional)
            revision: Specific revision to rollback to (None = previous)
            **kwargs: Additional executor-specific parameters

        Returns:
            ExecutionResult with status and details

        Raises:
            RuntimeError: If rollback fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if executor is available and healthy

        Returns:
            True if executor can execute actions, False otherwise
        """
        pass

    @abstractmethod
    def get_executor_type(self) -> str:
        """
        Get the type of this executor

        Returns:
            Executor type identifier (e.g., "docker-compose", "kubernetes")
        """
        pass

    @abstractmethod
    async def get_status(
        self,
        target: str,
        namespace: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get current status of a service/deployment

        Args:
            target: Service or deployment name
            namespace: Namespace/environment (optional)
            **kwargs: Additional executor-specific parameters

        Returns:
            Dictionary with status information (replicas, health, etc.)
        """
        pass

    def _create_result(
        self,
        action: str,
        status: str,
        target: str,
        execution_time: float,
        details: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Helper method to create standardized ExecutionResult

        Args:
            action: Action type
            status: Execution status
            target: Target service/deployment
            execution_time: Time taken to execute (seconds)
            details: Additional details
            namespace: Namespace/environment
            error: Error message if failed
            metadata: Additional metadata

        Returns:
            ExecutionResult object
        """
        return ExecutionResult(
            action=action,
            status=status,
            target=target,
            namespace=namespace,
            executor_type=self.get_executor_type(),
            timestamp=datetime.utcnow().isoformat(),
            execution_time=execution_time,
            details=details or {},
            error=error,
            metadata=metadata or {}
        )

    def _validate_replicas(
        self,
        replicas: int,
        min_replicas: int,
        max_replicas: int
    ) -> int:
        """
        Validate and clamp replica count to allowed range

        Args:
            replicas: Requested replica count
            min_replicas: Minimum allowed
            max_replicas: Maximum allowed

        Returns:
            Clamped replica count
        """
        if replicas < min_replicas:
            return min_replicas
        if replicas > max_replicas:
            return max_replicas
        return replicas
