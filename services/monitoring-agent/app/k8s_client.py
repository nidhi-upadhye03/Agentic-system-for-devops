"""
Kubernetes Client - Interact with Kubernetes API

This module provides an async interface to query Kubernetes resources.
"""
import logging
from typing import List, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class K8sError(Exception):
    """Custom exception for Kubernetes-related errors"""
    pass


class K8sClient:
    """Kubernetes client for querying cluster resources"""

    def __init__(self, in_cluster: bool = True, namespace: str = "default"):
        """
        Initialize Kubernetes client

        Args:
            in_cluster: True if running inside K8s cluster, False for local dev
            namespace: Default namespace to query
        """
        self.namespace = namespace
        self.in_cluster = in_cluster
        self.core_api: Optional[client.CoreV1Api] = None
        self.apps_api: Optional[client.AppsV1Api] = None

        try:
            if in_cluster:
                # Load in-cluster config (when running as pod)
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes config")
            else:
                # Load kubeconfig from ~/.kube/config (local dev)
                config.load_kube_config()
                logger.info("Loaded kubeconfig from local machine")

            self.core_api = client.CoreV1Api()
            self.apps_api = client.AppsV1Api()
            logger.info(f"K8s client initialized (namespace: {namespace})")

        except Exception as e:
            logger.warning(f"Failed to initialize K8s client: {e}")
            logger.warning("K8s features will be disabled")

    def is_available(self) -> bool:
        """Check if K8s client is available"""
        return self.core_api is not None

    async def get_pods(self, namespace: Optional[str] = None) -> List:
        """
        Get all pods in namespace

        Args:
            namespace: Namespace to query (defaults to self.namespace)

        Returns:
            List of V1Pod objects

        Example:
            pods = await k8s.get_pods()
            for pod in pods:
                print(f"Pod: {pod.metadata.name}, Status: {pod.status.phase}")
        """
        if not self.is_available():
            raise K8sError("K8s client not available")

        ns = namespace or self.namespace

        try:
            response = self.core_api.list_namespaced_pod(namespace=ns)
            logger.debug(f"Found {len(response.items)} pods in namespace {ns}")
            return response.items

        except ApiException as e:
            raise K8sError(f"Failed to list pods in namespace {ns}: {e.reason}") from e
        except Exception as e:
            raise K8sError(f"Unexpected error listing pods: {str(e)}") from e

    async def get_pod_status(self, pod_name: str, namespace: Optional[str] = None):
        """
        Get detailed status of a specific pod

        Args:
            pod_name: Name of the pod
            namespace: Namespace (defaults to self.namespace)

        Returns:
            V1Pod object

        Example:
            pod = await k8s.get_pod_status('my-pod-123')
            print(f"Phase: {pod.status.phase}")
            print(f"Conditions: {pod.status.conditions}")
        """
        if not self.is_available():
            raise K8sError("K8s client not available")

        ns = namespace or self.namespace

        try:
            pod = self.core_api.read_namespaced_pod(name=pod_name, namespace=ns)
            logger.debug(f"Retrieved status for pod {pod_name}")
            return pod

        except ApiException as e:
            if e.status == 404:
                raise K8sError(f"Pod {pod_name} not found in namespace {ns}") from e
            raise K8sError(f"Failed to get pod {pod_name}: {e.reason}") from e
        except Exception as e:
            raise K8sError(f"Unexpected error getting pod status: {str(e)}") from e

    async def get_deployments(self, namespace: Optional[str] = None) -> List:
        """
        Get all deployments in namespace

        Args:
            namespace: Namespace to query (defaults to self.namespace)

        Returns:
            List of V1Deployment objects

        Example:
            deployments = await k8s.get_deployments()
            for deploy in deployments:
                print(f"Deployment: {deploy.metadata.name}")
                print(f"Replicas: {deploy.spec.replicas}/{deploy.status.ready_replicas}")
        """
        if not self.is_available():
            raise K8sError("K8s client not available")

        ns = namespace or self.namespace

        try:
            response = self.apps_api.list_namespaced_deployment(namespace=ns)
            logger.debug(f"Found {len(response.items)} deployments in namespace {ns}")
            return response.items

        except ApiException as e:
            raise K8sError(f"Failed to list deployments in namespace {ns}: {e.reason}") from e
        except Exception as e:
            raise K8sError(f"Unexpected error listing deployments: {str(e)}") from e

    async def get_services(self, namespace: Optional[str] = None) -> List:
        """
        Get all services in namespace

        Args:
            namespace: Namespace to query (defaults to self.namespace)

        Returns:
            List of V1Service objects

        Example:
            services = await k8s.get_services()
            for svc in services:
                print(f"Service: {svc.metadata.name}, Type: {svc.spec.type}")
        """
        if not self.is_available():
            raise K8sError("K8s client not available")

        ns = namespace or self.namespace

        try:
            response = self.core_api.list_namespaced_service(namespace=ns)
            logger.debug(f"Found {len(response.items)} services in namespace {ns}")
            return response.items

        except ApiException as e:
            raise K8sError(f"Failed to list services in namespace {ns}: {e.reason}") from e
        except Exception as e:
            raise K8sError(f"Unexpected error listing services: {str(e)}") from e

    async def get_nodes(self) -> List:
        """
        Get all nodes in cluster

        Returns:
            List of V1Node objects

        Example:
            nodes = await k8s.get_nodes()
            for node in nodes:
                print(f"Node: {node.metadata.name}")
                for condition in node.status.conditions:
                    print(f"  {condition.type}: {condition.status}")
        """
        if not self.is_available():
            raise K8sError("K8s client not available")

        try:
            response = self.core_api.list_node()
            logger.debug(f"Found {len(response.items)} nodes in cluster")
            return response.items

        except ApiException as e:
            raise K8sError(f"Failed to list nodes: {e.reason}") from e
        except Exception as e:
            raise K8sError(f"Unexpected error listing nodes: {str(e)}") from e

    async def health_check(self) -> bool:
        """
        Check if K8s API is accessible

        Returns:
            True if accessible, False otherwise
        """
        if not self.is_available():
            return False

        try:
            # Try to list namespaces as health check
            self.core_api.list_namespace(limit=1)
            logger.debug("K8s health check: OK")
            return True
        except Exception as e:
            logger.error(f"K8s health check failed: {e}")
            return False
