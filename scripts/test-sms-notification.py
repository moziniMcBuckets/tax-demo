#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Test SMS Notification Functionality

Tests the SMS notification feature by:
1. Verifying SNS permissions
2. Sending a test SMS
3. Checking usage tracking
"""

import boto3
import json
import sys
from datetime import datetime

# Initialize clients
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

def test_sns_permissions():
    """Test if SNS permissions are configured correctly."""
    print("Testing SNS permissions...")
    try:
        # Try to get SMS attributes
        response = sns.get_sms_attributes(attributes=['MonthlySpendLimit'])
        print(f"✓ SNS permissions OK")
        print(f"  Current spending limit: ${response.get('attributes', {}).get('MonthlySpendLimit', 'Not set')}")
        return True
    except Exception as e:
        print(f"✗ SNS permissions failed: {e}")
        return False

def set_spending_limit(limit_usd=10.0):
    """Set SNS monthly spending limit."""
    print(f"\nSetting SNS spending limit to ${limit_usd}...")
    try:
        sns.set_sms_attributes(
            attributes={'MonthlySpendLimit': str(limit_usd)}
        )
        print(f"✓ Spending limit set to ${limit_usd}/month")
        return True
    except Exception as e:
        print(f"✗ Failed to set spending limit: {e}")
        return False

def send_test_sms(phone_number):
    """
    Send a test SMS message.
    
    Args:
        phone_number: E.164 format phone number (e.g., +12065551234)
    """
    print(f"\nSending test SMS to {phone_number}...")
    
    # Validate phone format
    import re
    if not re.match(r'^\+1[2-9]\d{9}$', phone_number):
        print(f"✗ Invalid phone number format. Must be E.164 format: +1XXXXXXXXXX")
        return False
    
    try:
        response = sns.publish(
            PhoneNumber=phone_number,
            Message='Test SMS from Tax Agent. SMS notifications are now enabled! Reply STOP to opt out.',
            MessageAttributes={
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                },
                'AWS.SNS.SMS.SenderID': {
                    'DataType': 'String',
                    'StringValue': 'YourFirm'
                }
            }
        )
        message_id = response['MessageId']
        print(f"✓ SMS sent successfully!")
        print(f"  Message ID: {message_id}")
        return True
    except Exception as e:
        print(f"✗ Failed to send SMS: {e}")
        return False

def verify_lambda_config(function_name):
    """Verify Lambda function has SMS_SENDER_ID configured."""
    print(f"\nVerifying Lambda configuration: {function_name}...")
    try:
        response = lambda_client.get_function_configuration(
            FunctionName=function_name
        )
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        if 'SMS_SENDER_ID' in env_vars:
            print(f"✓ SMS_SENDER_ID configured: {env_vars['SMS_SENDER_ID']}")
            return True
        else:
            print(f"✗ SMS_SENDER_ID not found in environment variables")
            return False
    except Exception as e:
        print(f"✗ Failed to get Lambda config: {e}")
        return False

def check_usage_tracking(table_name='tax-agent-usage'):
    """Check if SMS usage is being tracked."""
    print(f"\nChecking usage tracking in {table_name}...")
    try:
        table = dynamodb.Table(table_name)
        
        # Scan for SMS usage entries
        response = table.scan(
            FilterExpression='resource_type = :rt',
            ExpressionAttributeValues={':rt': 'sms_sent'},
            Limit=5
        )
        
        count = response.get('Count', 0)
        if count > 0:
            print(f"✓ Found {count} SMS usage entries")
            for item in response.get('Items', []):
                print(f"  - {item.get('timestamp')}: {item.get('quantity')} SMS, ${item.get('estimated_cost')}")
            return True
        else:
            print(f"  No SMS usage entries yet (this is normal for first test)")
            return True
    except Exception as e:
        print(f"✗ Failed to check usage: {e}")
        return False

def main():
    """Run all SMS tests."""
    print("=" * 60)
    print("SMS Notification Test Suite")
    print("=" * 60)
    
    # Get phone number from command line
    if len(sys.argv) < 2:
        print("\nUsage: python3 test-sms-notification.py +1XXXXXXXXXX")
        print("Example: python3 test-sms-notification.py +12065551234")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    
    results = []
    
    # Test 1: SNS Permissions
    results.append(("SNS Permissions", test_sns_permissions()))
    
    # Test 2: Set Spending Limit
    results.append(("Spending Limit", set_spending_limit(10.0)))
    
    # Test 3: Verify Lambda Config
    results.append(("Lambda Config (batch-operations)", verify_lambda_config('tax-agent-batch-operations')))
    results.append(("Lambda Config (send-link)", verify_lambda_config('tax-agent-gateway___send_upload_link')))
    
    # Test 4: Send Test SMS
    results.append(("Send Test SMS", send_test_sms(phone_number)))
    
    # Test 5: Check Usage Tracking
    results.append(("Usage Tracking", check_usage_tracking()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! SMS notifications are ready to use.")
        print("\nNext steps:")
        print("1. Update a client with phone number and sms_enabled=true")
        print("2. Test sending upload link via agent or UI")
        print("3. Verify SMS delivery and cost tracking")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
