#!/bin/bash
# Bada'a Montessori Website — Deploy to Vercel
set -e

PROJECT_DIR="/Users/mohamedmontaser/Documents/Claude/Projects/montessori website"
cd "$PROJECT_DIR"

echo ""
echo "🌱 Bada'a Montessori — Deploying to Vercel"
echo "============================================"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install --no-audit --no-fund

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
  echo "⚡ Installing Vercel CLI..."
  npm install -g vercel --no-audit --no-fund
fi

echo ""
echo "🚀 Deploying to Vercel..."
echo "(If first time, Vercel will ask you to log in)"
echo ""

npx vercel --prod

echo ""
echo "✅ Deployment complete!"
