#!/bin/bash

echo "Installing dependencies for Claude chat integration..."

# Install Anthropic SDK
npm install @anthropic-ai/sdk

echo "✓ Dependencies installed!"
echo ""
echo "Next steps:"
echo "1. Add your Anthropic API key to .env.local:"
echo "   ANTHROPIC_API_KEY=sk-ant-your-api-key-here"
echo ""
echo "2. If you want to use a service role key for Supabase (recommended):"
echo "   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key"
echo ""
echo "3. Restart your Next.js dev server"