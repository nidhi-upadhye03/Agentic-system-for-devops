FROM prom/prometheus:v2.48.0

# Copy Azure-specific Prometheus configuration
COPY prometheus-azure.yml /etc/prometheus/prometheus.yml

# Expose Prometheus port
EXPOSE 9090

# Use default Prometheus entrypoint
# Prometheus will read /etc/prometheus/prometheus.yml automatically
