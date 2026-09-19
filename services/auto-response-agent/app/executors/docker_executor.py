"""
Docker Compose Executor - Executes actions using Docker Compose

This executor implementation uses docker-compose commands to perform
remediation actions in a Docker Compose environment.

Classes:
    - DockerComposeExecutor: Executor for Docker Compose orchestrated services

Example Usage:
    executor = DockerComposeExecutor(
        compose_file="/path/to/docker-compose.yml",
        dry_run=False
    )

    # Restart a service
    result = await executor.restart("test-app")

    # Scale a service
    result = await executor.scale("test-app", replicas=3)
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base import BaseExecutor, ExecutionResult, ActionType

logger = logging.getLogger(__name__)


class DockerComposeExecutor(BaseExecutor):
    """
    Executor implementation for Docker Compose

    This executor uses docker-compose CLI commands to perform actions
    on services defined in a docker-compose.yml file.

    Attributes:
        compose_file: Path to docker-compose.yml file
        project_name: Docker Compose project name (optional)
        dry_run: If True, simulate actions without executing
    """

    def __init__(
        self,
        compose_file: str = "/compose/docker-compose.yml",
        project_name: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize Docker Compose executor

        Args:
            compose_file: Path to docker-compose.yml file
            project_name: Docker Compose project name (optional)
            dry_run: If True, simulate actions without executing
        """
        super().__init__(dry_run=dry_run)
        self.compose_file = compose_file
        self.project_name = project_name
        self._available = None  # Cached availability check

        logger.info(f"Initialized DockerComposeExecutor")
        logger.info(f"  Compose file: {self.compose_file}")
        logger.info(f"  Project name: {self.project_name or 'auto-detected'}")
        logger.info(f"  Dry-run mode: {self.dry_run}")

    async def restart(
        self,
        target: str,
        namespace: Optional[str] = None,
        grace_period: int = 30,
        **kwargs
    ) -> ExecutionResult:
        """
        Restart a Docker Compose service

        Args:
            target: Service name to restart (e.g., "test-app")
            namespace: Not used in Docker Compose (kept for interface compatibility)
            grace_period: Timeout for restart operation (seconds)
            **kwargs: Additional parameters (ignored)

        Returns:
            ExecutionResult with restart status

        Raises:
            RuntimeError: If restart fails
        """
        start_time = time.time()
        logger.info(f"Restarting service: {target}")

        # Validate service exists
        if not await self._service_exists(target):
            error = f"Service '{target}' not found in compose file"
            logger.error(error)
            return self._create_result(
                action=ActionType.RESTART.value,
                status="failed",
                target=target,
                execution_time=time.time() - start_time,
                error=error
            )

        if self.dry_run:
            logger.info(f"[DRY RUN] Would restart service: {target}")
            return self._create_result(
                action=ActionType.RESTART.value,
                status="dry_run",
                target=target,
                execution_time=time.time() - start_time,
                details={"message": "Dry run - no actual restart performed"}
            )

        # Execute docker-compose restart
        command = self._build_command(["restart", "-t", str(grace_period), target])
        result = await self._run_command(command, timeout=grace_period + 30)

        execution_time = time.time() - start_time

        if result["returncode"] == 0:
            logger.info(f"✓ Successfully restarted {target} in {execution_time:.2f}s")
            return self._create_result(
                action=ActionType.RESTART.value,
                status="success",
                target=target,
                execution_time=execution_time,
                details={
                    "stdout": result["stdout"],
                    "grace_period": grace_period
                }
            )
        else:
            error = result["stderr"] or "Unknown error"
            logger.error(f"Failed to restart {target}: {error}")
            return self._create_result(
                action=ActionType.RESTART.value,
                status="failed",
                target=target,
                execution_time=execution_time,
                error=error,
                details={"stdout": result["stdout"], "stderr": result["stderr"]}
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
        Scale a Docker Compose service

        Args:
            target: Service name to scale
            replicas: Target replica count
            namespace: Not used in Docker Compose
            min_replicas: Minimum allowed replicas (safety check)
            max_replicas: Maximum allowed replicas (safety check)
            **kwargs: Additional parameters

        Returns:
            ExecutionResult with scale status

        Raises:
            RuntimeError: If scaling fails
        """
        start_time = time.time()
        logger.info(f"Scaling service {target} to {replicas} replicas")

        # Validate service exists
        if not await self._service_exists(target):
            error = f"Service '{target}' not found in compose file"
            logger.error(error)
            return self._create_result(
                action=ActionType.SCALE.value,
                status="failed",
                target=target,
                execution_time=time.time() - start_time,
                error=error
            )

        # Validate and clamp replicas
        original_replicas = replicas
        replicas = self._validate_replicas(replicas, min_replicas, max_replicas)
        if replicas != original_replicas:
            logger.warning(
                f"Replica count adjusted from {original_replicas} to {replicas} "
                f"(min: {min_replicas}, max: {max_replicas})"
            )

        if self.dry_run:
            logger.info(f"[DRY RUN] Would scale service {target} to {replicas} replicas")
            return self._create_result(
                action=ActionType.SCALE.value,
                status="dry_run",
                target=target,
                execution_time=time.time() - start_time,
                details={
                    "message": "Dry run - no actual scaling performed",
                    "target_replicas": replicas
                }
            )

        # Execute docker-compose up --scale
        command = self._build_command([
            "up", "-d", "--no-recreate",
            f"--scale", f"{target}={replicas}"
        ])
        result = await self._run_command(command, timeout=120)

        execution_time = time.time() - start_time

        if result["returncode"] == 0:
            logger.info(f"✓ Successfully scaled {target} to {replicas} replicas in {execution_time:.2f}s")
            return self._create_result(
                action=ActionType.SCALE.value,
                status="success",
                target=target,
                execution_time=execution_time,
                details={
                    "replicas": replicas,
                    "original_request": original_replicas,
                    "stdout": result["stdout"]
                }
            )
        else:
            error = result["stderr"] or "Unknown error"
            logger.error(f"Failed to scale {target}: {error}")
            return self._create_result(
                action=ActionType.SCALE.value,
                status="failed",
                target=target,
                execution_time=execution_time,
                error=error,
                details={"stdout": result["stdout"], "stderr": result["stderr"]}
            )

    async def rollback(
        self,
        target: str,
        namespace: Optional[str] = None,
        revision: Optional[int] = None,
        **kwargs
    ) -> ExecutionResult:
        """
        Rollback a service (Docker Compose has no native rollback, so restart)

        Note: Docker Compose doesn't have built-in rollback functionality.
        This implementation simply restarts the service as a basic rollback.
        For true rollback, you would need to change the image tag and recreate.

        Args:
            target: Service name to rollback
            namespace: Not used in Docker Compose
            revision: Not supported in Docker Compose
            **kwargs: Additional parameters

        Returns:
            ExecutionResult with rollback status
        """
        start_time = time.time()
        logger.info(f"Rollback requested for {target}")
        logger.warning(
            "Docker Compose doesn't support native rollback. "
            "Performing service restart as basic rollback."
        )

        if revision:
            logger.warning(f"Revision parameter ({revision}) ignored for Docker Compose")

        # Rollback = restart for Docker Compose
        result = await self.restart(target, namespace=namespace, grace_period=30)

        # Update action type to rollback
        result.action = ActionType.ROLLBACK.value
        result.metadata["rollback_method"] = "restart"
        result.metadata["note"] = "Docker Compose rollback performed as service restart"

        return result

    async def health_check(self) -> bool:
        """
        Check if Docker Compose executor is available

        Returns:
            True if docker-compose CLI is available and compose file exists
        """
        if self._available is not None:
            return self._available

        logger.info("Performing Docker Compose health check...")

        # Check 1: docker-compose command available
        try:
            result = await self._run_command("docker-compose --version", timeout=5)
            if result["returncode"] != 0:
                logger.error("docker-compose command not available")
                self._available = False
                return False
            logger.info(f"✓ Docker Compose version: {result['stdout'].strip()}")
        except Exception as e:
            logger.error(f"Failed to check docker-compose version: {e}")
            self._available = False
            return False

        # Check 2: Compose file exists
        if not os.path.exists(self.compose_file):
            logger.error(f"Compose file not found: {self.compose_file}")
            self._available = False
            return False
        logger.info(f"✓ Compose file found: {self.compose_file}")

        # Check 3: Can parse compose file
        try:
            command = self._build_command(["config", "--services"])
            result = await self._run_command(command, timeout=10)
            if result["returncode"] != 0:
                logger.error(f"Failed to parse compose file: {result['stderr']}")
                self._available = False
                return False
            services = result["stdout"].strip().split("\n")
            logger.info(f"✓ Found {len(services)} services in compose file")
        except Exception as e:
            logger.error(f"Failed to parse compose file: {e}")
            self._available = False
            return False

        logger.info("✓ Docker Compose executor is healthy")
        self._available = True
        return True

    def get_executor_type(self) -> str:
        """Get executor type identifier"""
        return "docker-compose"

    async def get_status(
        self,
        target: str,
        namespace: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get current status of a service

        Args:
            target: Service name
            namespace: Not used in Docker Compose
            **kwargs: Additional parameters

        Returns:
            Dictionary with service status
        """
        logger.info(f"Getting status for service: {target}")

        # Check if service exists
        if not await self._service_exists(target):
            return {
                "service": target,
                "exists": False,
                "error": "Service not found"
            }

        # Get service status using docker-compose ps
        command = self._build_command(["ps", "--all", target])
        result = await self._run_command(command, timeout=10)

        if result["returncode"] != 0:
            return {
                "service": target,
                "exists": True,
                "error": result["stderr"],
                "status": "unknown"
            }

        return {
            "service": target,
            "exists": True,
            "status": "running" if "Up" in result["stdout"] else "stopped",
            "details": result["stdout"],
            "timestamp": time.time()
        }

    # Helper methods

    async def _service_exists(self, service_name: str) -> bool:
        """
        Check if a service exists in the compose file

        Args:
            service_name: Name of service to check

        Returns:
            True if service exists, False otherwise
        """
        try:
            command = self._build_command(["config", "--services"])
            result = await self._run_command(command, timeout=10)

            if result["returncode"] != 0:
                logger.error(f"Failed to list services: {result['stderr']}")
                return False

            services = result["stdout"].strip().split("\n")
            exists = service_name in services

            if exists:
                logger.debug(f"✓ Service '{service_name}' exists")
            else:
                logger.debug(f"✗ Service '{service_name}' not found. Available: {services}")

            return exists

        except Exception as e:
            logger.error(f"Error checking service existence: {e}")
            return False

    def _build_command(self, args: List[str]) -> str:
        """
        Build docker-compose command with file and project arguments

        Args:
            args: List of command arguments

        Returns:
            Complete command string
        """
        cmd_parts = ["docker-compose"]

        # Add compose file
        if self.compose_file:
            cmd_parts.extend(["-f", self.compose_file])

        # Add project name
        if self.project_name:
            cmd_parts.extend(["-p", self.project_name])

        # Add command arguments
        cmd_parts.extend(args)

        return " ".join(cmd_parts)

    async def _run_command(
        self,
        command: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Execute a shell command asynchronously

        Args:
            command: Command to execute
            timeout: Timeout in seconds

        Returns:
            Dictionary with returncode, stdout, stderr, execution_time
        """
        start_time = time.time()
        logger.debug(f"Executing command: {command}")

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            execution_time = time.time() - start_time

            result = {
                "returncode": process.returncode,
                "stdout": stdout.decode("utf-8") if stdout else "",
                "stderr": stderr.decode("utf-8") if stderr else "",
                "execution_time": execution_time
            }

            logger.debug(
                f"Command completed in {execution_time:.2f}s "
                f"(returncode: {process.returncode})"
            )

            return result

        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout}s: {command}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "execution_time": timeout
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Command failed: {e}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": execution_time
            }
