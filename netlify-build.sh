#!/bin/bash
# Netlify build script to inject Sentry DSN into HTML files
# This script replaces {{SENTRY_DSN}} placeholder with the actual DSN from environment variable

# Fetch Git LFS files if git-lfs is available
if command -v git-lfs &> /dev/null; then
    echo "🔧 Fetching Git LFS files..."
    git lfs pull
    echo "✅ Git LFS files fetched"
fi

if [ -n "$SENTRY_DSN" ]; then
    echo "🔧 Injecting Sentry DSN into HTML files..."
    find app -name "*.html" -type f -exec sed -i.bak "s|{{SENTRY_DSN}}|$SENTRY_DSN|g" {} \;
    find app -name "*.html.bak" -delete  # Clean up backup files
    echo "✅ Sentry DSN injected successfully"
else
    echo "⚠️ SENTRY_DSN not set - Sentry will be disabled"
fi

echo "✅ Build complete"

