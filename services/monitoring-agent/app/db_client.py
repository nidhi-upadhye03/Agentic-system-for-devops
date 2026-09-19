"""
Database Client for Monitoring Agent

Handles PostgreSQL operations for storing incidents.
"""
import json
import logging
import asyncpg
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseClient:
    """PostgreSQL database client for incident storage"""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool: Optional[asyncpg.Pool] = None
        logger.info(f"Database client initialized: {host}:{port}/{database}")

    async def connect(self):
        """Establish database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("✓ Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("✓ Disconnected from PostgreSQL")

    async def store_incident(
        self,
        incident_id: str,
        event_type: str,
        severity: str,
        metric_name: str,
        metric_value: float,
        threshold: Optional[float],
        message: str,
        labels: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store an incident in the database

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.pool:
            logger.error("Database pool not initialized")
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO incidents (
                        incident_id, event_type, severity, metric_name,
                        metric_value, threshold, message, labels, metadata,
                        source, status, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (incident_id) DO UPDATE SET
                        updated_at = $13,
                        status = $11
                    """,
                    incident_id,
                    event_type,
                    severity,
                    metric_name,
                    metric_value,
                    threshold,
                    message,
                    json.dumps(labels) if labels else '{}',  # Convert dict to JSON string
                    json.dumps(metadata) if metadata else '{}',  # Convert dict to JSON string
                    "monitoring-agent",
                    "detected",
                    datetime.utcnow(),
                    datetime.utcnow()
                )

            logger.debug(f"Stored incident: {incident_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing incident {incident_id}: {e}", exc_info=True)
            return False

    async def update_incident_status(
        self,
        incident_id: str,
        status: str
    ) -> bool:
        """Update incident status"""
        if not self.pool:
            logger.error("Database pool not initialized")
            return False

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE incidents
                    SET status = $1, updated_at = $2
                    WHERE incident_id = $3
                    """,
                    status,
                    datetime.utcnow(),
                    incident_id
                )

            logger.debug(f"Updated incident {incident_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Error updating incident {incident_id}: {e}")
            return False

    async def get_recent_incidents(self, limit: int = 100) -> list:
        """Get recent incidents from database"""
        if not self.pool:
            logger.error("Database pool not initialized")
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT *
                    FROM incidents
                    ORDER BY created_at DESC
                    LIMIT $1
                    """,
                    limit
                )

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching incidents: {e}")
            return []

    async def check_active_incident(self, metric_name: str, service_name: str) -> Optional[str]:
        """
        Check if there is an active incident for the given metric and service.
        Returns incident_id if found, None otherwise.
        PRODUCTION: 5 minute window to prevent duplicate incident processing
        """
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                # Check for incidents that are not resolved or closed
                # PRODUCTION: 5 minute window to prevent rapid re-triggering
                row = await conn.fetchrow(
                    """
                    SELECT incident_id
                    FROM incidents
                    WHERE metric_name = $1
                    AND (labels->>'service' = $2 OR labels->>'pod' = $2)
                    AND status NOT IN ('resolved', 'closed', 'false_positive')
                    AND updated_at > NOW() - INTERVAL '5 minutes'
                    LIMIT 1
                    """,
                    metric_name,
                    service_name
                )
                return row['incident_id'] if row else None
        except Exception as e:
            logger.error(f"Error checking active incidents: {e}")
            return None
