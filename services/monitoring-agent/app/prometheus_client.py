"""
Prometheus Client - Query Prometheus metrics

This module provides an async interface to query Prometheus metrics.
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger(__name__)


class PrometheusError(Exception):
    """Custom exception for Prometheus-related errors"""
    pass


class Prometheus:
    """Async Prometheus client for querying metrics"""

    def __init__(self, prometheus_url: str, timeout: int = 30):
        """
        Initialize Prometheus client

        Args:
            prometheus_url: Base URL of Prometheus server (e.g., http://prometheus:9090)
            timeout: Request timeout in seconds
        """
        self.base_url = prometheus_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"Prometheus client initialized: {self.base_url}")

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Prometheus client session closed")

    async def query(self, query_string: str) -> List[Dict[str, Any]]:
        """
        Execute instant Prometheus query

        Args:
            query_string: PromQL query string

        Returns:
            List of metric results with 'metric' and 'value' keys

        Example:
            results = await prom.query('up{job="my-service"}')
            # [{'metric': {'job': 'my-service', '__name__': 'up'}, 'value': [timestamp, '1']}]
        """
        await self._ensure_session()

        url = f"{self.base_url}/api/v1/query"
        params = {"query": query_string}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise PrometheusError(
                        f"Prometheus query failed (status {response.status}): {text}"
                    )

                data = await response.json()

                if data.get("status") != "success":
                    raise PrometheusError(
                        f"Prometheus query error: {data.get('error', 'Unknown error')}"
                    )

                result = data.get("data", {}).get("result", [])
                logger.debug(f"Query returned {len(result)} results: {query_string}")
                return result

        except aiohttp.ClientError as e:
            raise PrometheusError(f"Network error querying Prometheus: {str(e)}") from e
        except Exception as e:
            raise PrometheusError(f"Unexpected error querying Prometheus: {str(e)}") from e

    async def query_range(
        self,
        query_string: str,
        start: datetime,
        end: datetime,
        step: str = "15s"
    ) -> List[Dict[str, Any]]:
        """
        Execute range Prometheus query

        Args:
            query_string: PromQL query string
            start: Start time
            end: End time
            step: Query resolution step (e.g., '15s', '1m', '5m')

        Returns:
            List of metric results with 'metric' and 'values' keys

        Example:
            start = datetime.now() - timedelta(hours=1)
            end = datetime.now()
            results = await prom.query_range('rate(http_requests[5m])', start, end, '1m')
        """
        await self._ensure_session()

        url = f"{self.base_url}/api/v1/query_range"
        params = {
            "query": query_string,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise PrometheusError(
                        f"Prometheus range query failed (status {response.status}): {text}"
                    )

                data = await response.json()

                if data.get("status") != "success":
                    raise PrometheusError(
                        f"Prometheus range query error: {data.get('error', 'Unknown error')}"
                    )

                result = data.get("data", {}).get("result", [])
                logger.debug(f"Range query returned {len(result)} series: {query_string}")
                return result

        except aiohttp.ClientError as e:
            raise PrometheusError(f"Network error querying Prometheus: {str(e)}") from e
        except Exception as e:
            raise PrometheusError(f"Unexpected error querying Prometheus: {str(e)}") from e

    async def get_metric_labels(self, metric_name: str) -> List[str]:
        """
        Get all label names for a specific metric

        Args:
            metric_name: Name of the metric

        Returns:
            List of label names

        Example:
            labels = await prom.get_metric_labels('http_requests_total')
            # ['job', 'instance', 'method', 'status']
        """
        await self._ensure_session()

        url = f"{self.base_url}/api/v1/labels"
        params = {"match[]": metric_name}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise PrometheusError(
                        f"Failed to get labels (status {response.status}): {text}"
                    )

                data = await response.json()

                if data.get("status") != "success":
                    raise PrometheusError(
                        f"Label query error: {data.get('error', 'Unknown error')}"
                    )

                labels = data.get("data", [])
                logger.debug(f"Metric {metric_name} has {len(labels)} labels")
                return labels

        except aiohttp.ClientError as e:
            raise PrometheusError(f"Network error getting labels: {str(e)}") from e
        except Exception as e:
            raise PrometheusError(f"Unexpected error getting labels: {str(e)}") from e

    async def health_check(self) -> bool:
        """
        Check if Prometheus server is healthy

        Returns:
            True if healthy, False otherwise
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/-/healthy"
            async with self.session.get(url) as response:
                is_healthy = response.status == 200
                logger.debug(f"Prometheus health check: {'OK' if is_healthy else 'FAILED'}")
                return is_healthy
        except Exception as e:
            logger.error(f"Prometheus health check failed: {e}")
            return False

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
