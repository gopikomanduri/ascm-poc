#!/bin/bash
# 🚀 ASCM v4.0 - Real API Setup Script
# Configures environment variables for real API calls

set -e

echo "🔌 ASCM Real API Configuration"
echo "======================================"
echo ""

# Check if .env file exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists"
    read -p "Do you want to overwrite it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled"
        exit 1
    fi
fi

# Collect API keys interactively
echo "📝 Enter your API keys (leave blank to use mock data for that service):"
echo ""

read -p "OpenOutreach API Key (or press Enter): " openoutreach_key
read -p "OpenOutreach Endpoint [http://localhost:8080]: " openoutreach_endpoint
openoutreach_endpoint=${openoutreach_endpoint:-"http://localhost:8080"}

echo ""

read -p "Smartlead API Key (or press Enter): " smartlead_key
read -p "Smartlead Domain [reply.smartlead.ai]: " smartlead_domain
smartlead_domain=${smartlead_domain:-"reply.smartlead.ai"}

echo ""

read -p "Buffer API Key (or press Enter): " buffer_key
read -p "Buffer LinkedIn Profile ID (or press Enter): " buffer_linkedin_id
read -p "Buffer Twitter Profile ID (or press Enter): " buffer_twitter_id

echo ""

read -p "NeverBounce API Key (optional, press Enter): " neverbounce_key

echo ""
echo "======================================"
echo "🔐 Creating .env file..."
echo ""

cat > .env << EOF
# OpenOutreach Configuration
OPENOUTREACH_API_KEY="${openoutreach_key}"
OPENOUTREACH_ENDPOINT="${openoutreach_endpoint}"

# Smartlead Configuration
SMARTLEAD_API_KEY="${smartlead_key}"
SMARTLEAD_DOMAIN="${smartlead_domain}"

# Buffer Configuration
BUFFER_API_KEY="${buffer_key}"
BUFFER_LINKEDIN_PROFILE_ID="${buffer_linkedin_id}"
BUFFER_TWITTER_PROFILE_ID="${buffer_twitter_id}"

# NeverBounce Configuration (Optional)
NEVERBOUNCE_API_KEY="${neverbounce_key}"

# Application Settings
LLM_PROVIDER="ollama"
OLLAMA_HOST="http://localhost:11434"
OLLAMA_MODEL="phi4-mini:latest"
EOF

echo "✅ .env file created"
echo ""
echo "📋 Configuration Summary:"
echo "======================================"
[ -n "$openoutreach_key" ] && echo "✅ OpenOutreach: Configured" || echo "⚪ OpenOutreach: Using mock data"
[ -n "$smartlead_key" ] && echo "✅ Smartlead: Configured" || echo "⚪ Smartlead: Using mock data"
[ -n "$buffer_key" ] && echo "✅ Buffer: Configured" || echo "⚪ Buffer: Using mock data"
[ -n "$neverbounce_key" ] && echo "✅ NeverBounce: Configured" || echo "⚪ NeverBounce: Using default scores"
echo ""
echo "======================================"
echo "🚀 Next Steps:"
echo ""
echo "1. Load environment variables:"
echo "   source .env"
echo ""
echo "2. Run GTM campaign:"
echo "   python -m orchestrator.experiments.first_gtm_campaign"
echo ""
echo "3. View logs:"
echo "   tail -f /Users/komanduri/Downloads/projects/googledeepagenthackathon/goproject/payment-gateway/ASCM/execution_trace_*.log"
echo ""
echo "4. Check for real API calls:"
echo "   grep '\[REAL API\]' /Users/komanduri/Downloads/projects/googledeepagenthackathon/goproject/payment-gateway/ASCM/execution_trace_*.log"
echo ""
echo "======================================"
echo "✨ Configuration complete!"
