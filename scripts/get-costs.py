#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Get Cost and Usage for Tax Agent

Retrieves cost information for all resources tagged with the tax agent project.
Shows costs broken down by service and provides monthly totals.

Usage:
    python3 scripts/get-costs.py [--month YYYY-MM]
    
Example:
    python3 scripts/get-costs.py --month 2026-01
"""

import boto3
import json
import sys
from datetime import datetime, timedelta
from decimal import Decimal

ce = boto3.client('ce', region_name='us-east-1')  # Cost Explorer is us-east-1 only

def get_month_range(month_str=None):
    """Get start and end dates for a month."""
    if month_str:
        # Parse YYYY-MM format
        year, month = map(int, month_str.split('-'))
        start = datetime(year, month, 1)
    else:
        # Current month
        now = datetime.now()
        start = datetime(now.year, now.month, 1)
    
    # Calculate end of month
    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)
    
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

def decimal_default(obj):
    """JSON serializer for Decimal objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def main():
    """Main entry point."""
    # Parse arguments
    month = None
    if len(sys.argv) > 2 and sys.argv[1] == '--month':
        month = sys.argv[2]
    
    start_date, end_date = get_month_range(month)
    
    print("=" * 60)
    print("Tax Document Agent - Cost Report")
    print("=" * 60)
    print(f"Period: {start_date} to {end_date}")
    print()
    
    try:
        # Get costs by service
        response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost', 'UsageQuantity'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ],
            Filter={
                'Tags': {
                    'Key': 'Project',
                    'Values': ['TaxDocumentAgent']
                }
            }
        )
        
        # Parse results
        results = response.get('ResultsByTime', [])
        
        if not results:
            print("No cost data available for this period.")
            print("\nNote: Cost data may take 24-48 hours to appear after resource creation.")
            return
        
        total_cost = Decimal('0')
        service_costs = []
        
        for result in results:
            for group in result.get('Groups', []):
                service = group['Keys'][0]
                cost = Decimal(group['Metrics']['BlendedCost']['Amount'])
                usage = group['Metrics']['UsageQuantity']['Amount']
                
                if cost > 0:
                    service_costs.append({
                        'service': service,
                        'cost': cost,
                        'usage': usage
                    })
                    total_cost += cost
        
        # Sort by cost (highest first)
        service_costs.sort(key=lambda x: x['cost'], reverse=True)
        
        # Display results
        print("Costs by Service:")
        print("-" * 60)
        print(f"{'Service':<40} {'Cost':>10} {'Usage':>8}")
        print("-" * 60)
        
        for item in service_costs:
            print(f"{item['service']:<40} ${item['cost']:>9.2f} {float(item['usage']):>8.1f}")
        
        print("-" * 60)
        print(f"{'TOTAL':<40} ${total_cost:>9.2f}")
        print("=" * 60)
        
        # Show top 3 services
        if service_costs:
            print("\nTop 3 Cost Drivers:")
            for i, item in enumerate(service_costs[:3], 1):
                percentage = (item['cost'] / total_cost * 100) if total_cost > 0 else 0
                print(f"  {i}. {item['service']}: ${item['cost']:.2f} ({percentage:.1f}%)")
        
        print("\nCost Breakdown:")
        print(f"  Daily average: ${total_cost / 30:.2f}")
        print(f"  Projected monthly: ${total_cost:.2f}")
        
        # Save to file
        output_file = f"cost-report-{start_date}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'period': {'start': start_date, 'end': end_date},
                'total_cost': float(total_cost),
                'services': [
                    {
                        'service': item['service'],
                        'cost': float(item['cost']),
                        'usage': float(item['usage'])
                    }
                    for item in service_costs
                ]
            }, f, indent=2)
        
        print(f"\n✓ Detailed report saved to: {output_file}")
        
    except Exception as e:
        print(f"Error retrieving cost data: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure Cost Explorer is enabled in your AWS account")
        print("2. Wait 24-48 hours after resource creation for data to appear")
        print("3. Verify tags are applied: aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=TaxDocumentAgent")
        sys.exit(1)

if __name__ == '__main__':
    main()
