#!/bin/sh
# Entrypoint script to replace BACKEND_URL placeholder in nginx config

set -e

# Default backend URL if not provided
BACKEND_URL=${BACKEND_URL:-http://approval-backend:3000}

echo "Configuring nginx with BACKEND_URL: $BACKEND_URL"

# Replace BACKEND_URL_PLACEHOLDER in nginx config
sed -i "s|BACKEND_URL_PLACEHOLDER|$BACKEND_URL|g" /etc/nginx/conf.d/default.conf

echo "Nginx configuration updated"
cat /etc/nginx/conf.d/default.conf

# Start nginx
exec nginx -g 'daemon off;'
