#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Conversion script: Tax-Demo → Vela Operations Squad
# Run from repo root

echo "🚀 Converting repo to Vela Operations Squad..."
echo ""

# Step 1: Backup check
echo "Step 1: Checking backup branch exists..."
if git show-ref --verify --quiet refs/heads/backup-tax-demo-final; then
    echo "✅ Backup branch exists: backup-tax-demo-final"
else
    echo "⚠️  Creating backup branch..."
    git branch backup-tax-demo-final
    git push origin backup-tax-demo-final
fi
echo ""

# Step 2: Delete tax-specific files
echo "Step 2: Removing tax-specific files..."
rm -f docs/COST_ESTIMATE_10_ACCOUNTANTS.md
rm -f "docs/test1 (1).pdf"
rm -f scripts/seed-tax-test-data.py
rm -f scripts/test-tax-agent.py
rm -f scripts/test-tax-gateway.py
rm -f scripts/update-client-accountant-id.py
echo "✅ Tax-specific files removed"
echo ""

# Step 3: Rename config files
echo "Step 3: Renaming configuration files..."
if [ -f "infra-cdk/config-tax-agent.yaml" ]; then
    cp infra-cdk/config-tax-agent.yaml infra-cdk/config-operations-squad.yaml
    echo "✅ Created config-operations-squad.yaml"
fi
echo ""

# Step 4: Create new agent directory
echo "Step 4: Creating Operations Squad structure..."
mkdir -p patterns/strands-multi-agent
touch patterns/strands-multi-agent/__init__.py
echo "✅ Created patterns/strands-multi-agent/"
echo ""

# Step 5: Summary
echo "========================================="
echo "✅ Conversion Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Review changes: git status"
echo "2. Update config-operations-squad.yaml"
echo "3. Build operations_squad.py (Week 1)"
echo "4. Build gateway tools (Week 1-3)"
echo "5. Test and deploy (Week 4)"
echo ""
echo "📚 See docs/START_HERE.md for Week 1 tasks"
echo ""
