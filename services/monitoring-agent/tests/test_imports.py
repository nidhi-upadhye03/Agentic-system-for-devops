"""
Basic import test for monitoring agent modules
"""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing module imports...")

    try:
        print("  ✓ Importing config...")
        from config import config, MonitoringConfig

        print("  ✓ Importing prometheus_client...")
        from prometheus_client import Prometheus, PrometheusError

        print("  ✓ Importing k8s_client...")
        from k8s_client import K8sClient, K8sError

        print("  ✓ Importing anomaly_detector...")
        from anomaly_detector import AnomalyDetector

        print("  ✓ Importing event_publisher...")
        from event_publisher import EventPublisher, EventPublisherError

        print("\n✅ All modules imported successfully!")
        return True

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")

    try:
        from config import config

        print(f"  ✓ Agent name: {config.agent_name}")
        print(f"  ✓ Agent version: {config.agent_version}")
        print(f"  ✓ Prometheus URL: {config.prometheus_url}")
        print(f"  ✓ RabbitMQ host: {config.rabbitmq_host}")
        print(f"  ✓ CPU threshold: {config.cpu_threshold}%")
        print(f"  ✓ Memory threshold: {config.memory_threshold}%")
        print(f"  ✓ Metrics to monitor: {len(config.metrics_to_monitor)} metrics")

        print("\n✅ Configuration loaded successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Configuration error: {e}")
        return False


def test_anomaly_detector():
    """Test anomaly detector basic functionality"""
    print("\nTesting anomaly detector...")

    try:
        from anomaly_detector import AnomalyDetector

        detector = AnomalyDetector(sensitivity=2.0, min_data_points=5)

        # Add normal data points
        for i in range(10):
            detector.add_data_point("test_metric", 50.0 + i)

        # Test normal value
        is_anomaly = detector.is_anomaly("test_metric", 55.0)
        print(f"  ✓ Normal value (55.0): anomaly={is_anomaly}")

        # Test anomalous value
        is_anomaly = detector.is_anomaly("test_metric", 150.0)
        print(f"  ✓ Anomalous value (150.0): anomaly={is_anomaly}")

        # Get statistics
        stats = detector.get_statistics("test_metric")
        print(f"  ✓ Statistics: mean={stats['mean']:.2f}, std={stats['std']:.2f}")

        print("\n✅ Anomaly detector working correctly!")
        return True

    except Exception as e:
        print(f"\n❌ Anomaly detector error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("MONITORING AGENT - MODULE TEST")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Import test", test_imports()))
    results.append(("Config test", test_config()))
    results.append(("Anomaly detector test", test_anomaly_detector()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    # Exit code
    all_passed = all(result[1] for result in results)
    sys.exit(0 if all_passed else 1)
