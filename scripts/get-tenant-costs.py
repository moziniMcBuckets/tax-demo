#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Get Per-Tenant Costs

Shows usage and costs broken down by accountant (tenant).
This is the recommended approach for multi-tenant SaaS cost tracking.

Usage:
    python3 scripts/get-tenant-costs.py [--month YYYY-MM] [--accountant-id ID]
    
Examples:
    # All tenants, current month
    python3 scripts/get-tenant-costs.py
    
    # Specific tenant
    python3 scripts/get-tenant-costs.py --accountant-id e8a1f3a0-8001-70a0-3ed9-3d4b95fc7500
    
    # Specific month
    python3 scripts/get-tenant-costs.py --month 2026-01
"""

import boto3
import sys
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('tax-agent-usage')

def get_month_prefix(month_str=None):
    """Get month prefix for filtering (YYYY-MM format)."""
    if month_str:
        return month_str
    return datetime.now().strftime('%Y-%m')

def main():
    """Main entry point."""
    # Parse arguments
    month = None
    accountant_id = None
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--month' and i + 1 < len(sys.argv):
            month = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--accountant-id' and i + 1 < len(sys.argv):
            accountant_id = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    month_prefix = get_month_prefix(month)
    
    print("=" * 80)
    print("Tax Document Agent - Per-Tenant Cost Report")
    print("=" * 80)
    print(f"Month: {month_prefix}")
    if accountant_id:
        print(f"Accountant: {accountant_id}")
    else:
        print("Showing: All accountants")
    print()
    
    try:
        # Query usage table
        if accountant_id:
            # Specific accountant
            response = table.query(
                KeyConditionExpression='accountant_id = :aid AND begins_with(#ts, :month)',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':aid': accountant_id,
                    ':month': month_prefix
                }
            )
        else:
            # All accountants - scan with filter
            response = table.scan(
                FilterExpression='begins_with(#m, :month)',
                ExpressionAttributeNames={'#m': 'month'},
                ExpressionAttributeValues={':month': month_prefix}
            )
        
        items = response.get('Items', [])
        
        if not items:
            print("No usage data found for this period.")
            print("\nNote: Usage is tracked in real-time as operations occur.")
            print("Try using the app (send emails, upload links, etc.) to generate usage data.")
            return
        
        # Aggregate by accountant and resource type
        tenant_costs = defaultdict(lambda: {
            'total_cost': Decimal('0'),
            'operations': defaultdict(lambda: {'count': 0, 'cost': Decimal('0')})
        })
        
        for item in items:
            aid = item['accountant_id']
            resource_type = item['resource_type']
            cost = item.get('estimated_cost', Decimal('0'))
            
            tenant_costs[aid]['total_cost'] += cost
            tenant_costs[aid]['operations'][resource_type]['count'] += 1
            tenant_costs[aid]['operations'][resource_type]['cost'] += cost
        
        # Display results
        print("Per-Tenant Costs:")
        print("-" * 80)
        
        # Sort by total cost (highest first)
        sorted_tenants = sorted(tenant_costs.items(), key=lambda x: x[1]['total_cost'], reverse=True)
        
        for aid, data in sorted_tenants:
            print(f"\nAccountant: {aid}")
            print(f"Total Cost: ${data['total_cost']:.4f}")
            print(f"Operations:")
            
            for resource_type, stats in data['operations'].items():
                print(f"  - {resource_type}: {stats['count']} operations, ${stats['cost']:.4f}")
        
        print("\n" + "=" * 80)
        
        # Summary
        total_all_tenants = sum(data['total_cost'] for _, data in sorted_tenants)
        print(f"\nSummary:")
        print(f"  Total tenants: {len(sorted_tenants)}")
        print(f"  Total operations: {sum(item.get('quantity', 1) for item in items)}")
        print(f"  Total cost: ${total_all_tenants:.4f}")
        print(f"  Average per tenant: ${total_all_tenants / len(sorted_tenants):.4f}")
        
        # Cost breakdown by resource type
        print(f"\nCost Breakdown by Resource Type:")
        resource_totals = defaultdict(lambda: {'count': 0, 'cost': Decimal('0')})
        for item in items:
            rt = item['resource_type']
            resource_totals[rt]['count'] += 1
            resource_totals[rt]['cost'] += item.get('estimated_cost', Decimal('0'))
        
        for rt, stats in sorted(resource_totals.items(), key=lambda x: x[1]['cost'], reverse=True):
            print(f"  - {rt}: {stats['count']} operations, ${stats['cost']:.4f}")
        
        print("\n" + "=" * 80)
        
        # Billing recommendations
        print("\nBilling Recommendations:")
        print(f"  1. Charge per operation:")
        for rt, stats in resource_totals.items():
            avg_cost = stats['cost'] / stats['count'] if stats['count'] > 0 else 0
            markup = avg_cost * Decimal('1.5')  # 50% markup
            print(f"     - {rt}: ${markup:.4f} per operation (cost: ${avg_cost:.4f}, markup: 50%)")
        
        print(f"\n  2. Monthly subscription:")
        if sorted_tenants:
            avg_monthly = total_all_tenants / len(sorted_tenants)
            subscription_price = avg_monthly * Decimal('2')  # 2x cost
            print(f"     - Base price: ${subscription_price:.2f}/month per tenant")
            print(f"     - Covers average usage of ${avg_monthly:.2f}")
        
        print(f"\n  3. Tiered pricing:")
        print(f"     - Starter: $10/month (up to 50 operations)")
        print(f"     - Professional: $25/month (up to 200 operations)")
        print(f"     - Enterprise: $50/month (unlimited)")
        
    except Exception as e:
        print(f"Error retrieving usage data: {e}")
        print("\nTroubleshooting:")
        print("1. Verify usage table exists: aws dynamodb describe-table --table-name tax-agent-usage")
        print("2. Check if usage tracking is enabled in Lambda environment variables")
        print("3. Use the app to generate some usage data")
        sys.exit(1)

if __name__ == '__main__':
    main()
