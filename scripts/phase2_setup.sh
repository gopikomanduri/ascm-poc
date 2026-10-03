#!/bin/bash
#
# ASCM v4.0 Phase 2: Complete Setup Script
# Installs all dependencies, OSS repos, and configures environment
#
# Usage: bash scripts/phase2_setup.sh
#

set -e  # Exit on error

echo "=== ASCM v4.0 Phase 2 Setup ==="
echo "Starting at: $(date)"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR_DIR="$PROJECT_ROOT/vendor"
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$VENDOR_DIR" "$LOG_DIR"

echo ""
echo "📦 Step 1: Update Python Packages"
echo "================================="
pip install --upgrade pip setuptools wheel
pip install -r "$PROJECT_ROOT/requirements.txt"
echo "✓ Packages installed"

echo ""
echo "🔌 Step 2: Clone OpenOutreach Repository"
echo "=========================================="
if [ -d "$VENDOR_DIR/openoutreach" ]; then
    echo "  (already cloned, updating...)"
    cd "$VENDOR_DIR/openoutreach"
    git pull origin main
else
    echo "  Cloning from https://github.com/eracle/OpenOutreach..."
    git clone https://github.com/eracle/OpenOutreach.git "$VENDOR_DIR/openoutreach"
fi
cd "$VENDOR_DIR/openoutreach"
pip install -e .
echo "✓ OpenOutreach installed"

echo ""
echo "🎨 Step 3: Clone ai-marketing-skills Repository"
echo "==============================================="
if [ -d "$VENDOR_DIR/ai-marketing-skills" ]; then
    echo "  (already cloned, updating...)"
    cd "$VENDOR_DIR/ai-marketing-skills"
    git pull origin main
else
    echo "  Cloning from https://github.com/ericosiu/ai-marketing-skills..."
    git clone https://github.com/ericosiu/ai-marketing-skills.git "$VENDOR_DIR/ai-marketing-skills"
fi
cd "$VENDOR_DIR/ai-marketing-skills"
pip install -e .
echo "✓ ai-marketing-skills installed"

echo ""
echo "🧩 Step 4: Install Composio (Tool Execution)"
echo "=============================================="
pip install composio[openai]==0.24.0
echo "✓ Composio installed"

echo ""
echo "⏱️  Step 5: Install Temporal SDK"
echo "================================="
pip install temporalio==1.34.0
pip install "temporalio[testing]"
echo "✓ Temporal SDK installed"

echo ""
echo "🐘 Step 6: PostgreSQL Setup"
echo "============================"
DB_NAME="${DATABASE_NAME:-ascm_v4}"
DB_USER="${DATABASE_USER:-postgres}"

if command -v createdb &> /dev/null; then
    if psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        echo "  (database $DB_NAME already exists)"
    else
        echo "  Creating database: $DB_NAME"
        createdb "$DB_NAME"
    fi

    echo "  Applying migrations..."
    psql -U "$DB_USER" -d "$DB_NAME" < "$PROJECT_ROOT/migrations/0001_base_schema.sql" || true
    psql -U "$DB_USER" -d "$DB_NAME" < "$PROJECT_ROOT/migrations/0002_orchestrator.sql" || true
    psql -U "$DB_USER" -d "$DB_NAME" < "$PROJECT_ROOT/migrations/0003_domain_knowledge.sql" || true
    psql -U "$DB_USER" -d "$DB_NAME" < "$PROJECT_ROOT/migrations/0004_v3_agents.sql" || true
    psql -U "$DB_USER" -d "$DB_NAME" < "$PROJECT_ROOT/migrations/0005_v4_gtm_autonomous_campaigns.sql" || true

    echo "  Verifying schema..."
    psql -U "$DB_USER" -d "$DB_NAME" -c "\dt gtm_*" | head -5
    echo "✓ PostgreSQL configured"
else
    echo "  ⚠️  PostgreSQL not found. Skipping database setup."
    echo "  (Install with: brew install postgresql or apt-get install postgresql)"
fi

echo ""
echo "🔐 Step 7: Environment Configuration"
echo "===================================="
ENV_FILE="$PROJECT_ROOT/.env.local"
if [ -f "$ENV_FILE" ]; then
    echo "  (.env.local already exists)"
else
    echo "  Creating .env.local template..."
    cat > "$ENV_FILE" << 'ENVEOF'
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/ascm_v4
DB_POOL_SIZE=20

# Temporal
TEMPORAL_HOST=localhost
TEMPORAL_PORT=7233

# API
API_PORT=8000
API_HOST=0.0.0.0

# Webhook Security
WEBHOOK_SECRET=$(openssl rand -base64 32)
WEBHOOK_TIMEOUT_SECONDS=30

# LLM APIs
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Service APIs (fill in as you configure)
OPENOUTREACH_API_KEY=
BETTERCONTACT_API_KEY=
SMARTLEAD_API_KEY=
INSTANTLY_API_KEY=
COMPOSIO_API_KEY=
SLACK_WEBHOOK_URL=

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM_EMAIL=
SMTP_FROM_PASSWORD=

# Feature Flags
DEBUG=False
LOG_LEVEL=INFO
ENABLE_FOUNDER_NOTIFICATIONS=True
ENABLE_REPLY_SUPPRESSION=True
ENVEOF

    echo "  ✓ .env.local created"
    echo "  ⚠️  Update .env.local with your API keys!"
fi

echo ""
echo "🧪 Step 8: Test Python Imports"
echo "==============================="
python -c "
import sys
try:
    import openoutreach
    print('  ✓ openoutreach')
except ImportError as e:
    print(f'  ✗ openoutreach: {e}')

try:
    import composio
    print('  ✓ composio')
except ImportError as e:
    print(f'  ✗ composio: {e}')

try:
    import temporalio
    print('  ✓ temporalio')
except ImportError as e:
    print(f'  ✗ temporalio: {e}')

try:
    import asyncpg
    print('  ✓ asyncpg')
except ImportError as e:
    print(f'  ✗ asyncpg: {e}')

try:
    import fastapi
    print('  ✓ fastapi')
except ImportError as e:
    print(f'  ✗ fastapi: {e}')
"

echo ""
echo "📝 Step 9: Verify Project Structure"
echo "===================================="
echo "  Checking critical directories..."
for dir in "migrations" "orchestrator/workflows" "orchestrator/api" "orchestrator/gtm" "vendor"; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        echo "  ✓ $dir"
    else
        echo "  ✗ $dir (missing!)"
    fi
done

echo ""
echo "✅ Phase 2 Setup Complete!"
echo "=========================="
echo ""
echo "Next Steps:"
echo "1. Update .env.local with your API keys"
echo "2. Start Temporal server:"
echo "   temporal server start-dev"
echo "   (or: docker run -d -p 7233:7233 temporalio/auto-setup:latest)"
echo "3. Start FastAPI webhook server:"
echo "   cd $PROJECT_ROOT"
echo "   python -m uvicorn orchestrator.api.webhooks:app --reload"
echo "4. Test workflows:"
echo "   python scripts/test_workflow.py"
echo "5. Run integration tests:"
echo "   pytest tests/ -v"
echo ""
echo "Documentation:"
echo "- Phase 2 Guide: $PROJECT_ROOT/PHASE_2_IMPLEMENTATION_GUIDE.md"
echo "- Full Setup Guide: $PROJECT_ROOT/orchestrator/api/webhooks.py"
echo ""
echo "Started at: $(date)"
