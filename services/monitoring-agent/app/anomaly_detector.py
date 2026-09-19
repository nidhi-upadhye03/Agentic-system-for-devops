"""
Anomaly Detector - Statistical anomaly detection

This module implements Z-score based anomaly detection for time series metrics.
"""
import logging
from collections import defaultdict, deque
from typing import Dict, Deque, Optional
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Statistical anomaly detector using Z-score method"""

    def __init__(self, sensitivity: float = 2.0, min_data_points: int = 10, max_history: int = 100):
        """
        Initialize anomaly detector

        Args:
            sensitivity: Number of standard deviations for anomaly threshold (default: 2.0)
            min_data_points: Minimum data points before detecting anomalies (default: 10)
            max_history: Maximum history size per metric series (default: 100)

        Example:
            detector = AnomalyDetector(sensitivity=2.5, min_data_points=20)
        """
        self.sensitivity = sensitivity
        self.min_data_points = min_data_points
        self.max_history = max_history

        # Store historical data for each metric series
        self.history: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=max_history))

        # Store latest anomaly scores
        self.scores: Dict[str, float] = {}

        logger.info(
            f"Anomaly detector initialized (sensitivity={sensitivity}, "
            f"min_points={min_data_points}, max_history={max_history})"
        )

    def add_data_point(self, series_id: str, value: float):
        """
        Add a data point to the historical series

        Args:
            series_id: Unique identifier for the metric series
            value: Metric value

        Example:
            detector.add_data_point('cpu_pod_1', 75.3)
        """
        self.history[series_id].append(value)
        logger.debug(f"Added data point to {series_id}: {value} (history size: {len(self.history[series_id])})")

    def is_anomaly(self, series_id: str, value: float) -> bool:
        """
        Check if a value is anomalous for the given series

        Args:
            series_id: Unique identifier for the metric series
            value: Current metric value to check

        Returns:
            True if anomalous, False otherwise

        Example:
            if detector.is_anomaly('cpu_pod_1', 95.0):
                print("Anomaly detected!")
        """
        # Add current value to history
        self.add_data_point(series_id, value)

        # Get historical data
        data = list(self.history[series_id])

        # Need minimum data points for detection
        if len(data) < self.min_data_points:
            logger.debug(f"Not enough data for {series_id}: {len(data)}/{self.min_data_points}")
            self.scores[series_id] = 0.0
            return False

        # Calculate Z-score
        z_score = self._calculate_z_score(data, value)
        self.scores[series_id] = abs(z_score)

        # Check if anomaly
        is_anomalous = abs(z_score) > self.sensitivity

        if is_anomalous:
            logger.info(
                f"Anomaly detected in {series_id}: value={value:.2f}, "
                f"z-score={z_score:.2f}, threshold={self.sensitivity}"
            )

        return is_anomalous

    def _calculate_z_score(self, data: list, value: float) -> float:
        """
        Calculate Z-score for a value given historical data

        Z-score = (value - mean) / std_dev

        Args:
            data: Historical data points
            value: Current value

        Returns:
            Z-score (number of standard deviations from mean)
        """
        if len(data) < 2:
            return 0.0

        # Calculate mean and std
        mean = np.mean(data)
        std = np.std(data)

        # Handle zero std (all values identical)
        if std == 0:
            return 0.0 if value == mean else float('inf')

        z_score = (value - mean) / std
        return z_score

    def get_score(self, series_id: str) -> float:
        """
        Get the latest anomaly score for a series

        Args:
            series_id: Unique identifier for the metric series

        Returns:
            Anomaly score (absolute Z-score)

        Example:
            score = detector.get_score('cpu_pod_1')
            print(f"Anomaly score: {score}")
        """
        return self.scores.get(series_id, 0.0)

    def get_statistics(self, series_id: str) -> Optional[Dict[str, float]]:
        """
        Get statistical summary for a series

        Args:
            series_id: Unique identifier for the metric series

        Returns:
            Dict with mean, std, min, max, current values or None if not enough data

        Example:
            stats = detector.get_statistics('cpu_pod_1')
            print(f"Mean: {stats['mean']}, Std: {stats['std']}")
        """
        data = list(self.history.get(series_id, []))

        if len(data) < 2:
            return None

        return {
            "mean": float(np.mean(data)),
            "std": float(np.std(data)),
            "min": float(np.min(data)),
            "max": float(np.max(data)),
            "current": float(data[-1]),
            "data_points": len(data),
            "anomaly_score": self.scores.get(series_id, 0.0)
        }

    def reset_series(self, series_id: str):
        """
        Reset history for a specific series

        Args:
            series_id: Unique identifier for the metric series

        Example:
            detector.reset_series('cpu_pod_1')
        """
        if series_id in self.history:
            self.history[series_id].clear()
            self.scores.pop(series_id, None)
            logger.info(f"Reset history for series: {series_id}")

    def reset_all(self):
        """
        Reset all historical data

        Example:
            detector.reset_all()
        """
        self.history.clear()
        self.scores.clear()
        logger.info("Reset all anomaly detector history")

    def get_tracked_series(self) -> list:
        """
        Get list of all tracked series IDs

        Returns:
            List of series IDs

        Example:
            series = detector.get_tracked_series()
            print(f"Tracking {len(series)} series")
        """
        return list(self.history.keys())

    def calculate_iqr_anomaly(self, series_id: str, value: float) -> bool:
        """
        Alternative anomaly detection using IQR (Interquartile Range) method

        This is more robust to outliers than Z-score method.

        Args:
            series_id: Unique identifier for the metric series
            value: Current metric value to check

        Returns:
            True if anomalous, False otherwise

        Example:
            if detector.calculate_iqr_anomaly('cpu_pod_1', 95.0):
                print("Anomaly detected (IQR method)!")
        """
        data = list(self.history.get(series_id, []))

        if len(data) < self.min_data_points:
            return False

        # Calculate IQR
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1

        # Calculate bounds
        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        # Check if value is outside bounds
        is_anomalous = value < lower_bound or value > upper_bound

        if is_anomalous:
            logger.info(
                f"IQR anomaly detected in {series_id}: value={value:.2f}, "
                f"bounds=[{lower_bound:.2f}, {upper_bound:.2f}]"
            )

        return is_anomalous
