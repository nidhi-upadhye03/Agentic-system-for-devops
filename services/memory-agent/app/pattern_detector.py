"""
Pattern Detector - Recurring Issue Detection

Analyzes incidents to detect recurring patterns and trends.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from app.config import config

logger = logging.getLogger(__name__)


class PatternDetector:
    """Detects recurring patterns in incidents"""

    def __init__(
        self,
        incident_store,
        vector_store,
        similarity_threshold: float = 0.85,
        min_occurrences: int = 3,
        time_window_hours: int = 168  # 7 days
    ):
        """
        Initialize pattern detector

        Args:
            incident_store: IncidentStore instance
            vector_store: VectorStore instance
            similarity_threshold: Minimum similarity to consider incidents related
            min_occurrences: Minimum occurrences to flag as pattern
            time_window_hours: Time window for pattern detection (hours)
        """
        self.incident_store = incident_store
        self.vector_store = vector_store
        self.similarity_threshold = similarity_threshold
        self.min_occurrences = min_occurrences
        self.time_window_hours = time_window_hours

    async def detect_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect recurring patterns in recent incidents

        Returns:
            List of detected patterns
        """
        try:
            logger.info("Starting pattern detection")

            patterns = []

            # Detect exact match patterns (same metric + target)
            exact_patterns = await self._detect_exact_patterns()
            patterns.extend(exact_patterns)

            # Detect semantic patterns (similar but not identical)
            semantic_patterns = await self._detect_semantic_patterns()
            patterns.extend(semantic_patterns)

            # Detect temporal patterns (time-based)
            temporal_patterns = await self._detect_temporal_patterns()
            patterns.extend(temporal_patterns)

            logger.info(f"Detected {len(patterns)} patterns")
            return patterns

        except Exception as e:
            logger.error(f"Pattern detection failed: {e}", exc_info=True)
            return []

    async def _detect_exact_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect exact match patterns (same metric + target recurring)

        Returns:
            List of exact patterns
        """
        patterns = []

        try:
            # Get recent incidents grouped by metric + target
            days = self.time_window_hours // 24
            since = datetime.now() - timedelta(days=days)

            # Query all recent incidents
            async with self.incident_store.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT metric_name, target, severity,
                           COUNT(*) as occurrence_count,
                           array_agg(incident_id) as incident_ids,
                           MIN(detected_at) as first_seen,
                           MAX(detected_at) as last_seen
                    FROM incidents
                    WHERE detected_at >= $1
                    GROUP BY metric_name, target, severity
                    HAVING COUNT(*) >= $2
                    ORDER BY COUNT(*) DESC
                """, since, self.min_occurrences)

                for row in rows:
                    pattern = {
                        "pattern_type": "exact_match",
                        "description": f"{row['metric_name']} on {row['target']} - {row['severity']} severity",
                        "metric_name": row["metric_name"],
                        "target": row["target"],
                        "severity": row["severity"],
                        "incident_ids": row["incident_ids"],
                        "occurrence_count": row["occurrence_count"],
                        "first_seen": row["first_seen"],
                        "last_seen": row["last_seen"],
                        "metadata": {
                            "time_window_hours": self.time_window_hours
                        }
                    }

                    patterns.append(pattern)

                    # Store pattern in database
                    await self.incident_store.store_pattern(pattern)

            logger.info(f"Found {len(patterns)} exact match patterns")

        except Exception as e:
            logger.error(f"Failed to detect exact patterns: {e}", exc_info=True)

        return patterns

    async def _detect_semantic_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect semantic patterns using vector similarity

        Returns:
            List of semantic patterns
        """
        patterns = []

        try:
            # Get recent incidents
            days = self.time_window_hours // 24
            since = datetime.now() - timedelta(days=days)

            async with self.incident_store.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT i.*, a.root_cause
                    FROM incidents i
                    LEFT JOIN analyses a ON i.incident_id = a.incident_id
                    WHERE i.detected_at >= $1
                    ORDER BY i.detected_at DESC
                """, since)

                incidents = [dict(row) for row in rows]

            # Group similar incidents using vector search
            clusters = await self._cluster_similar_incidents(incidents)

            # Create patterns from clusters
            for cluster in clusters:
                if len(cluster) >= self.min_occurrences:
                    # Get common attributes
                    metric_names = set(inc["metric_name"] for inc in cluster)
                    targets = set(inc["target"] for inc in cluster)

                    pattern = {
                        "pattern_type": "semantic_similarity",
                        "description": f"Similar issues across: {', '.join(list(targets)[:3])}",
                        "metric_names": list(metric_names),
                        "targets": list(targets),
                        "incident_ids": [inc["incident_id"] for inc in cluster],
                        "occurrence_count": len(cluster),
                        "first_seen": min(inc["detected_at"] for inc in cluster),
                        "last_seen": max(inc["detected_at"] for inc in cluster),
                        "metadata": {
                            "similarity_threshold": self.similarity_threshold,
                            "common_root_causes": self._extract_common_root_causes(cluster)
                        }
                    }

                    patterns.append(pattern)

                    # Store pattern
                    await self.incident_store.store_pattern(pattern)

            logger.info(f"Found {len(patterns)} semantic patterns")

        except Exception as e:
            logger.error(f"Failed to detect semantic patterns: {e}", exc_info=True)

        return patterns

    async def _detect_temporal_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect time-based patterns (e.g., daily spikes, weekly occurrences)

        Returns:
            List of temporal patterns
        """
        patterns = []

        try:
            # Get incidents from last 4 weeks for temporal analysis
            since = datetime.now() - timedelta(days=28)

            async with self.incident_store.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT metric_name, target,
                           EXTRACT(DOW FROM detected_at) as day_of_week,
                           EXTRACT(HOUR FROM detected_at) as hour_of_day,
                           COUNT(*) as occurrence_count,
                           array_agg(incident_id) as incident_ids
                    FROM incidents
                    WHERE detected_at >= $1
                    GROUP BY metric_name, target, day_of_week, hour_of_day
                    HAVING COUNT(*) >= $2
                    ORDER BY COUNT(*) DESC
                """, since, self.min_occurrences)

                for row in rows:
                    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                    day_name = day_names[int(row["day_of_week"])]

                    pattern = {
                        "pattern_type": "temporal",
                        "description": f"{row['metric_name']} on {row['target']} - occurs on {day_name} around {int(row['hour_of_day'])}:00",
                        "metric_name": row["metric_name"],
                        "target": row["target"],
                        "incident_ids": row["incident_ids"],
                        "occurrence_count": row["occurrence_count"],
                        "first_seen": since,
                        "last_seen": datetime.now(),
                        "metadata": {
                            "day_of_week": int(row["day_of_week"]),
                            "day_name": day_name,
                            "hour_of_day": int(row["hour_of_day"]),
                            "analysis_window_days": 28
                        }
                    }

                    patterns.append(pattern)

                    # Store pattern
                    await self.incident_store.store_pattern(pattern)

            logger.info(f"Found {len(patterns)} temporal patterns")

        except Exception as e:
            logger.error(f"Failed to detect temporal patterns: {e}", exc_info=True)

        return patterns

    async def _cluster_similar_incidents(
        self,
        incidents: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Cluster incidents by vector similarity

        Args:
            incidents: List of incidents

        Returns:
            List of clusters (each cluster is a list of incidents)
        """
        clusters = []
        processed = set()

        for incident in incidents:
            incident_id = incident.get("incident_id")
            if incident_id in processed:
                continue

            # Find similar incidents
            similar = await self.vector_store.search_similar_incidents(
                incident=incident,
                limit=20,
                min_score=self.similarity_threshold
            )

            if len(similar) >= self.min_occurrences:
                cluster = [incident]

                for sim in similar:
                    sim_id = sim.get("incident_id")
                    if sim_id != incident_id and sim_id not in processed:
                        # Find full incident data
                        full_incident = next(
                            (inc for inc in incidents if inc.get("incident_id") == sim_id),
                            None
                        )
                        if full_incident:
                            cluster.append(full_incident)
                            processed.add(sim_id)

                if len(cluster) >= self.min_occurrences:
                    clusters.append(cluster)
                    processed.add(incident_id)

        return clusters

    def _extract_common_root_causes(
        self,
        incidents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract common root causes from incident cluster

        Args:
            incidents: List of incidents

        Returns:
            List of common root cause keywords
        """
        root_causes = [
            inc.get("root_cause", "")
            for inc in incidents
            if inc.get("root_cause")
        ]

        if not root_causes:
            return []

        # Simple keyword extraction (count common words)
        word_counts = defaultdict(int)
        for cause in root_causes:
            words = cause.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_counts[word] += 1

        # Get top common words
        common = sorted(
            word_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return [word for word, count in common if count > 1]

    async def analyze_pattern_trends(
        self,
        pattern_id: int
    ) -> Dict[str, Any]:
        """
        Analyze trends for a specific pattern

        Args:
            pattern_id: Pattern ID

        Returns:
            Trend analysis
        """
        try:
            # Get pattern from database
            async with self.incident_store.pool.acquire() as conn:
                pattern = await conn.fetchrow("""
                    SELECT * FROM patterns WHERE pattern_id = $1
                """, pattern_id)

                if not pattern:
                    return {}

                # Analyze incident frequency over time
                incident_ids = pattern["incident_ids"]

                rows = await conn.fetch("""
                    SELECT DATE(detected_at) as date, COUNT(*) as count
                    FROM incidents
                    WHERE incident_id = ANY($1)
                    GROUP BY DATE(detected_at)
                    ORDER BY date
                """, incident_ids)

                daily_counts = {row["date"].isoformat(): row["count"] for row in rows}

                # Calculate trend
                counts = list(daily_counts.values())
                is_increasing = len(counts) > 1 and counts[-1] > counts[0]
                avg_daily = sum(counts) / len(counts) if counts else 0

                return {
                    "pattern_id": pattern_id,
                    "pattern_type": pattern["pattern_type"],
                    "total_occurrences": pattern["occurrence_count"],
                    "daily_average": avg_daily,
                    "is_increasing": is_increasing,
                    "daily_counts": daily_counts,
                    "time_span_days": (pattern["last_seen"] - pattern["first_seen"]).days
                }

        except Exception as e:
            logger.error(f"Failed to analyze pattern trends: {e}", exc_info=True)
            return {}

    async def get_pattern_recommendations(
        self,
        pattern: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations based on detected pattern

        Args:
            pattern: Pattern data

        Returns:
            List of recommendations
        """
        recommendations = []

        pattern_type = pattern.get("pattern_type")
        occurrence_count = pattern.get("occurrence_count", 0)

        if pattern_type == "exact_match":
            recommendations.append(
                f"⚠️ {pattern.get('metric_name')} on {pattern.get('target')} has occurred {occurrence_count} times"
            )
            recommendations.append(
                "Consider implementing proactive monitoring or auto-scaling for this resource"
            )

        elif pattern_type == "semantic_similarity":
            targets = pattern.get("targets", [])
            recommendations.append(
                f"Similar issues detected across {len(targets)} targets"
            )
            recommendations.append(
                "This may indicate a systemic issue - consider reviewing shared infrastructure"
            )

        elif pattern_type == "temporal":
            metadata = pattern.get("metadata", {})
            day_name = metadata.get("day_name", "unknown")
            hour = metadata.get("hour_of_day", 0)

            recommendations.append(
                f"Pattern occurs regularly on {day_name} around {hour}:00"
            )
            recommendations.append(
                f"Consider scheduling preventive actions before {day_name} {hour}:00"
            )

        return recommendations
