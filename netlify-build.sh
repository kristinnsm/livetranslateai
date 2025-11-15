#!/bin/bash
# Netlify build script to inject Sentry DSN into HTML files
# This script replaces {{SENTRY_DSN}} placeholder with the actual DSN from environment variable

if [ -n "$SENTRY_DSN" ]; then
    echo "🔧 Injecting Sentry DSN into HTML files..."
    find app -name "*.html" -type f -exec sed -i.bak "s|{{SENTRY_DSN}}|$SENTRY_DSN|g" {} \;
    find app -name "*.html.bak" -delete  # Clean up backup files
    echo "✅ Sentry DSN injected successfully"
else
    echo "⚠️ SENTRY_DSN not set - Sentry will be disabled"
fi

echo "✅ Build complete"

