#!/bin/bash
# Netlify build script to inject Sentry DSN into HTML files
# This script replaces {{SENTRY_DSN}} placeholder with the actual DSN from environment variable

# Install and setup Git LFS to fetch large files
echo "🔧 Setting up Git LFS..."
if ! command -v git-lfs &> /dev/null; then
    echo "📦 Installing Git LFS..."
    # Try to install git-lfs (Netlify uses Ubuntu)
    curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash
    apt-get install -y git-lfs || {
        echo "⚠️ Could not install git-lfs via apt, trying alternative..."
        # Alternative: download binary directly
        wget https://github.com/git-lfs/git-lfs/releases/download/v3.6.1/git-lfs-linux-amd64-v3.6.1.tar.gz -O /tmp/git-lfs.tar.gz
        tar -xzf /tmp/git-lfs.tar.gz -C /tmp
        export PATH="$PATH:/tmp/git-lfs"
    }
fi

# Initialize and fetch LFS files
if command -v git-lfs &> /dev/null || command -v git-lfs-linux-amd64 &> /dev/null; then
    echo "🔧 Initializing Git LFS..."
    git lfs install || /tmp/git-lfs install
    echo "🔧 Fetching Git LFS files..."
    git lfs pull || /tmp/git-lfs pull
    echo "✅ Git LFS files fetched"
else
    echo "⚠️ Git LFS not available - large files may not be served correctly"
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

