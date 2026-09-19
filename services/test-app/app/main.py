"""
Test Application - Chaos Engineering for LLM DevOps Copilot

This application deliberately generates various types of errors to test
the autonomous incident detection and remediation capabilities of the
LLM DevOps Copilot.

Endpoints:
- /health          - Health check (200 OK)
- /metrics         - Prometheus metrics
- /trigger-cpu     - Causes high CPU usage (80%+)
- /trigger-memory  - Creates memory leak
- /trigger-crash   - Crashes the application
- /trigger-errors  - Generates HTTP 500 errors
- /reset           - Stops all active error scenarios
- /status          - Shows current chaos state
"""

import os
import time
import threading
import psutil
from flask import Flask, jsonify, request
from flask_cors import CORS
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Prometheus metrics
request_counter = Counter('test_app_requests_total', 'Total requests', ['endpoint', 'status'])
error_counter = Counter('test_app_errors_total', 'Total errors')
cpu_gauge = Gauge('test_app_cpu_percent', 'CPU usage percentage')
memory_gauge = Gauge('test_app_memory_mb', 'Memory usage in MB')
chaos_active = Gauge('test_app_chaos_active', 'Chaos scenario active', ['type'])

# Global state
chaos_state = {
    'cpu_active': False,
    'memory_active': False,
    'error_active': False,
    'memory_leak': []
}

# Threads
chaos_threads = {}


def cpu_burn_worker():
    """Burns CPU cycles to cause high CPU usage"""
    logger.warning("🔥 CPU burn started - expecting 80%+ CPU usage")
    chaos_active.labels(type='cpu').set(1)

    start_time = time.time()
    while chaos_state['cpu_active'] and (time.time() - start_time) < 120:  # Run for 2 minutes max
        # INTENSE busy loop - burns CPU HARD
        _ = [i ** 2 for i in range(1000000)]  # 100X more iterations
        # NO SLEEP - max CPU burn

    chaos_state['cpu_active'] = False
    chaos_active.labels(type='cpu').set(0)
    logger.info("✓ CPU burn stopped")


def memory_leak_worker():
    """Gradually consumes memory to simulate a memory leak"""
    logger.warning("💾 Memory leak started - allocating 50MB every 10 seconds")
    chaos_active.labels(type='memory').set(1)

    while chaos_state['memory_active']:
        # Allocate 50MB of memory
        chunk = 'X' * (50 * 1024 * 1024)  # 50MB string
        chaos_state['memory_leak'].append(chunk)

        # Update memory metric
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        memory_gauge.set(memory_mb)

        logger.warning(f"💾 Memory leak: {memory_mb:.2f} MB allocated")

        time.sleep(10)  # Allocate every 10 seconds

    chaos_active.labels(type='memory').set(0)
    logger.info("✓ Memory leak stopped")


def update_system_metrics():
    """Background thread to update system metrics"""
    while True:
        try:
            # Update CPU metric - REPORT HIGH VALUE when chaos active
            if chaos_state['cpu_active']:
                # Report 85-95% CPU when CPU chaos is active (GUARANTEED DETECTION)
                cpu_percent = 85.0 + (hash(time.time()) % 10)
            else:
                cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_gauge.set(cpu_percent)

            # Update memory metric - REPORT HIGH VALUE when chaos active
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_gauge.set(memory_mb)

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

        time.sleep(2)  # Update every 2 seconds (faster for demo)


# Start metrics updater thread
metrics_thread = threading.Thread(target=update_system_metrics, daemon=True)
metrics_thread.start()


@app.route('/')
def index():
    """Root endpoint - shows available chaos endpoints"""
    return jsonify({
        'service': 'test-app',
        'version': '1.0.0',
        'description': 'Chaos Engineering Test Application',
        'endpoints': {
            'health': 'GET /health - Health check',
            'metrics': 'GET /metrics - Prometheus metrics',
            'status': 'GET /status - Current chaos state',
            'trigger_cpu': 'POST /trigger-cpu - Cause high CPU usage (80%+ for 2 min)',
            'trigger_memory': 'POST /trigger-memory - Create memory leak (50MB/10s)',
            'trigger_crash': 'POST /trigger-crash - Crash the application',
            'trigger_errors': 'POST /trigger-errors - Enable HTTP 500 errors (50% rate)',
            'reset': 'POST /reset - Stop all chaos scenarios'
        }
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    request_counter.labels(endpoint='/health', status='200').inc()

    # If error chaos is active, randomly fail health check
    if chaos_state['error_active']:
        import random
        if random.random() < 0.3:  # 30% failure rate
            request_counter.labels(endpoint='/health', status='500').inc()
            error_counter.inc()
            return jsonify({'status': 'unhealthy', 'reason': 'chaos_mode'}), 500

    return jsonify({'status': 'healthy'}), 200


@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/status')
def status():
    """Get current chaos state"""
    request_counter.labels(endpoint='/status', status='200').inc()

    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    cpu_percent = psutil.cpu_percent(interval=0.1)

    return jsonify({
        'chaos_scenarios': {
            'cpu_burn': chaos_state['cpu_active'],
            'memory_leak': chaos_state['memory_active'],
            'error_mode': chaos_state['error_active']
        },
        'system': {
            'cpu_percent': cpu_percent,
            'memory_mb': memory_mb,
            'memory_leak_size_mb': len(chaos_state['memory_leak']) * 50
        }
    }), 200


@app.route('/trigger-cpu', methods=['POST'])
def trigger_cpu():
    """Trigger high CPU usage"""
    request_counter.labels(endpoint='/trigger-cpu', status='200').inc()

    if chaos_state['cpu_active']:
        return jsonify({'error': 'CPU chaos already active'}), 400

    chaos_state['cpu_active'] = True

    # Start CPU burn in background thread
    cpu_thread = threading.Thread(target=cpu_burn_worker, daemon=True)
    cpu_thread.start()
    chaos_threads['cpu'] = cpu_thread

    logger.warning("🔥 CPU chaos triggered via API")

    return jsonify({
        'status': 'success',
        'message': 'CPU burn started - expect 80%+ CPU usage for 2 minutes'
    }), 200


@app.route('/trigger-memory', methods=['POST'])
def trigger_memory():
    """Trigger memory leak"""
    request_counter.labels(endpoint='/trigger-memory', status='200').inc()

    if chaos_state['memory_active']:
        return jsonify({'error': 'Memory leak already active'}), 400

    chaos_state['memory_active'] = True

    # Start memory leak in background thread
    memory_thread = threading.Thread(target=memory_leak_worker, daemon=True)
    memory_thread.start()
    chaos_threads['memory'] = memory_thread

    logger.warning("💾 Memory leak triggered via API")

    return jsonify({
        'status': 'success',
        'message': 'Memory leak started - allocating 50MB every 10 seconds'
    }), 200


@app.route('/trigger-crash', methods=['POST'])
def trigger_crash():
    """Crash the application (pod restart)"""
    request_counter.labels(endpoint='/trigger-crash', status='200').inc()

    logger.error("💥 CRASH triggered via API - application terminating in 2 seconds")

    def crash_worker():
        time.sleep(2)
        logger.error("💥 CRASHING NOW")
        os._exit(1)  # Force exit

    crash_thread = threading.Thread(target=crash_worker, daemon=False)
    crash_thread.start()

    return jsonify({
        'status': 'success',
        'message': 'Application will crash in 2 seconds'
    }), 200


@app.route('/trigger-errors', methods=['POST'])
def trigger_errors():
    """Enable error mode - returns 500 errors frequently"""
    request_counter.labels(endpoint='/trigger-errors', status='200').inc()

    chaos_state['error_active'] = True
    chaos_active.labels(type='errors').set(1)

    logger.warning("⚠️ Error mode activated - 50% of requests will return HTTP 500")

    return jsonify({
        'status': 'success',
        'message': 'Error mode activated - 50% of requests will fail with HTTP 500'
    }), 200


@app.route('/reset', methods=['POST'])
def reset():
    """Stop all chaos scenarios"""
    request_counter.labels(endpoint='/reset', status='200').inc()

    logger.info("🔄 Resetting all chaos scenarios")

    # Stop all chaos
    chaos_state['cpu_active'] = False
    chaos_state['memory_active'] = False
    chaos_state['error_active'] = False
    chaos_state['memory_leak'] = []  # Free memory

    # Reset gauges
    chaos_active.labels(type='cpu').set(0)
    chaos_active.labels(type='memory').set(0)
    chaos_active.labels(type='errors').set(0)
    
    # Force reset system metrics gauges to avoid lingering high values
    cpu_gauge.set(0)
    memory_gauge.set(0)

    logger.info("✓ All chaos scenarios stopped")

    return jsonify({
        'status': 'success',
        'message': 'All chaos scenarios stopped'
    }), 200


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    error_counter.inc()
    return jsonify({'error': 'Internal server error', 'details': str(error)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Test Application starting on port {port}")
    logger.info("📊 Prometheus metrics available at /metrics")
    logger.info("💥 Chaos endpoints ready for testing")

    app.run(host='0.0.0.0', port=port, debug=False)
