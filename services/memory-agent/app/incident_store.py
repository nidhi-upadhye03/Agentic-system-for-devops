"""
Incident Store - PostgreSQL Storage

Handles storage and retrieval of incidents, analyses, and resolutions.
"""
import logging
import asyncpg
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.config import config

logger = logging.getLogger(__name__)


class IncidentStore:
    """PostgreSQL storage for incidents and resolutions"""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
        timeout: int = 30
    ):
        """
        Initialize incident store

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.timeout = timeout
        self.pool = None

    async def connect(self) -> bool:
        """
        Connect to PostgreSQL and create connection pool

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to PostgreSQL at {self.host}:{self.port}/{self.database}")

            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                timeout=self.timeout
            )

            # Create tables if they don't exist
            await self._create_tables()

            logger.info("✓ PostgreSQL connection pool created")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}", exc_info=True)
            return False

    async def disconnect(self):
        """Close PostgreSQL connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

    async def _create_tables(self):
        """Create necessary tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Incidents table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id VARCHAR(255) PRIMARY KEY,
                    metric_name VARCHAR(255) NOT NULL,
                    target VARCHAR(255) NOT NULL,
                    severity VARCHAR(50) NOT NULL,
                    current_value FLOAT NOT NULL,
                    threshold FLOAT NOT NULL,
                    detected_at TIMESTAMP NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Analyses table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    analysis_id SERIAL PRIMARY KEY,
                    incident_id VARCHAR(255) REFERENCES incidents(incident_id),
                    root_cause TEXT NOT NULL,
                    confidence FLOAT NOT NULL,
                    reasoning TEXT,
                    analyzed_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Resolutions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS resolutions (
                    resolution_id SERIAL PRIMARY KEY,
                    incident_id VARCHAR(255) REFERENCES incidents(incident_id),
                    action_type VARCHAR(255) NOT NULL,
                    action_details JSONB NOT NULL,
                    execution_status VARCHAR(50) NOT NULL,
                    execution_result JSONB,
                    success BOOLEAN NOT NULL,
                    executed_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Patterns table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id SERIAL PRIMARY KEY,
                    pattern_type VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    incident_ids TEXT[] NOT NULL,
                    occurrence_count INT NOT NULL,
                    first_seen TIMESTAMP NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Create indices
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_detected_at
                ON incidents(detected_at DESC)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_severity
                ON incidents(severity)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_target
                ON incidents(target)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_incident_id
                ON analyses(incident_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_resolutions_incident_id
                ON resolutions(incident_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_last_seen
                ON patterns(last_seen DESC)
            """)

            logger.info("✓ Database tables created/verified")

    async def store_incident(self, incident: Dict[str, Any]) -> bool:
        """
        Store incident in database

        Args:
            incident: Incident data

        Returns:
            True if stored successfully
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO incidents (
                        incident_id, metric_name, target, severity,
                        current_value, threshold, detected_at, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (incident_id) DO NOTHING
                """,
                    incident.get("incident_id"),
                    incident.get("metric_name"),
                    incident.get("target"),
                    incident.get("severity"),
                    incident.get("current_value"),
                    incident.get("threshold"),
                    datetime.fromisoformat(incident.get("timestamp").replace("Z", "+00:00")),
                    incident.get("metadata", {})
                )

            logger.info(f"Stored incident: {incident.get('incident_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to store incident: {e}", exc_info=True)
            return False

    async def store_analysis(
        self,
        incident_id: str,
        analysis: Dict[str, Any]
    ) -> bool:
        """
        Store analysis result

        Args:
            incident_id: Incident ID
            analysis: Analysis data

        Returns:
            True if stored successfully
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO analyses (
                        incident_id, root_cause, confidence, reasoning, analyzed_at
                    ) VALUES ($1, $2, $3, $4, $5)
                """,
                    incident_id,
                    analysis.get("root_cause", ""),
                    analysis.get("confidence", 0.0),
                    analysis.get("reasoning", ""),
                    datetime.now()
                )

            logger.info(f"Stored analysis for incident: {incident_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store analysis: {e}", exc_info=True)
            return False

    async def store_resolution(
        self,
        incident_id: str,
        action: Dict[str, Any],
        execution_result: Dict[str, Any],
        success: bool
    ) -> bool:
        """
        Store resolution/action execution

        Args:
            incident_id: Incident ID
            action: Action details
            execution_result: Execution result
            success: Whether action succeeded

        Returns:
            True if stored successfully
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO resolutions (
                        incident_id, action_type, action_details,
                        execution_status, execution_result, success, executed_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    incident_id,
                    action.get("type", "unknown"),
                    action.get("details", {}),
                    execution_result.get("status", "unknown"),
                    execution_result,
                    success,
                    datetime.now()
                )

            logger.info(f"Stored resolution for incident: {incident_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store resolution: {e}", exc_info=True)
            return False

    async def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """
        Get incident by ID

        Args:
            incident_id: Incident ID

        Returns:
            Incident data or None
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM incidents WHERE incident_id = $1
                """, incident_id)

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Failed to get incident: {e}", exc_info=True)
            return None

    async def get_similar_incidents(
        self,
        metric_name: str,
        target: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get similar past incidents

        Args:
            metric_name: Metric name to match
            target: Target to match
            limit: Maximum results

        Returns:
            List of similar incidents
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT i.*, a.root_cause, a.confidence, r.success
                    FROM incidents i
                    LEFT JOIN analyses a ON i.incident_id = a.incident_id
                    LEFT JOIN resolutions r ON i.incident_id = r.incident_id
                    WHERE i.metric_name = $1 AND i.target = $2
                    ORDER BY i.detected_at DESC
                    LIMIT $3
                """, metric_name, target, limit)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get similar incidents: {e}", exc_info=True)
            return []

    async def get_successful_resolutions(
        self,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get successful resolutions for learning

        Args:
            days: Look back days
            limit: Maximum results

        Returns:
            List of successful resolutions
        """
        try:
            async with self.pool.acquire() as conn:
                since = datetime.now() - timedelta(days=days)

                rows = await conn.fetch("""
                    SELECT i.*, a.root_cause, a.confidence,
                           r.action_type, r.action_details, r.execution_result
                    FROM incidents i
                    JOIN analyses a ON i.incident_id = a.incident_id
                    JOIN resolutions r ON i.incident_id = r.incident_id
                    WHERE r.success = TRUE
                    AND r.executed_at >= $1
                    AND a.confidence >= $2
                    ORDER BY r.executed_at DESC
                    LIMIT $3
                """, since, config.successful_resolution_threshold, limit)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get successful resolutions: {e}", exc_info=True)
            return []

    async def store_pattern(self, pattern: Dict[str, Any]) -> Optional[int]:
        """
        Store detected pattern

        Args:
            pattern: Pattern data

        Returns:
            Pattern ID or None
        """
        try:
            async with self.pool.acquire() as conn:
                pattern_id = await conn.fetchval("""
                    INSERT INTO patterns (
                        pattern_type, description, incident_ids,
                        occurrence_count, first_seen, last_seen, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING pattern_id
                """,
                    pattern.get("pattern_type"),
                    pattern.get("description"),
                    pattern.get("incident_ids", []),
                    pattern.get("occurrence_count", 0),
                    pattern.get("first_seen"),
                    pattern.get("last_seen"),
                    pattern.get("metadata", {})
                )

            logger.info(f"Stored pattern: {pattern_id}")
            return pattern_id

        except Exception as e:
            logger.error(f"Failed to store pattern: {e}", exc_info=True)
            return None

    async def get_recent_patterns(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recently detected patterns

        Args:
            days: Look back days

        Returns:
            List of patterns
        """
        try:
            async with self.pool.acquire() as conn:
                since = datetime.now() - timedelta(days=days)

                rows = await conn.fetch("""
                    SELECT * FROM patterns
                    WHERE last_seen >= $1
                    ORDER BY occurrence_count DESC, last_seen DESC
                """, since)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent patterns: {e}", exc_info=True)
            return []

    async def cleanup_old_data(self):
        """Clean up old incidents and resolutions"""
        try:
            async with self.pool.acquire() as conn:
                incident_cutoff = datetime.now() - timedelta(days=config.incident_retention_days)

                # Delete old incidents and related data
                result = await conn.execute("""
                    DELETE FROM incidents WHERE detected_at < $1
                """, incident_cutoff)

                logger.info(f"Cleaned up old data: {result}")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}", exc_info=True)
