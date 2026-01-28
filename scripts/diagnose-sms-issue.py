#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Diagnose SMS Delivery Issues

Checks common reasons why SMS might not be delivered.
"""

import boto3
import json

sns = boto3.client('sns')
sts = boto3.client('sts')

print("=" * 60)
print("SMS Delivery Diagnostic Tool")
print("=" * 60)

# Get account info
identity = sts.get_caller_identity()
account_id = identity['Account']
region = boto3.session.Session().region_name

print(f"\nAccount: {account_id}")
print(f"Region: {region}")

# Check SNS SMS attributes
print("\n1. SNS SMS Configuration:")
try:
    attrs = sns.get_sms_attributes()
    print(f"   Spending Limit: ${attrs['attributes'].get('MonthlySpendLimit', 'Not set')}")
    print(f"   ✓ SNS is accessible")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Check origination numbers
print("\n2. Origination Numbers:")
try:
    numbers = sns.list_origination_numbers()
    if numbers['PhoneNumbers']:
        print(f"   ✓ {len(numbers['PhoneNumbers'])} origination number(s) configured")
        for num in numbers['PhoneNumbers']:
            print(f"     - {num.get('PhoneNumber')}")
    else:
        print(f"   ⚠️  No origination numbers configured")
        print(f"   This might be required for SMS delivery in your region")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Check if SMS is enabled in region
print("\n3. SMS Service Status:")
print(f"   Region: {region}")
if region == 'us-west-2':
    print(f"   ✓ SMS is supported in us-west-2")
else:
    print(f"   ⚠️  Verify SMS is supported in {region}")

# Recommendations
print("\n" + "=" * 60)
print("Diagnosis & Recommendations")
print("=" * 60)

print("\n📋 Likely Issues:")
print("1. AWS SNS SMS might require production access request")
print("2. US carriers may require origination number (not Sender ID)")
print("3. SMS delivery can take 1-5 minutes")
print("4. Some carriers block messages from unknown senders")

print("\n🔧 Solutions:")
print("\n1. Request SNS SMS Production Access:")
print("   - Go to AWS Console → SNS → Text messaging (SMS)")
print("   - Check if you're in 'Sandbox mode'")
print("   - Click 'Request production access' if needed")
print("   - Use case: Transactional messages")
print("   - Volume: 1,000-5,000 messages/month")

print("\n2. Alternative: Use Origination Number (10DLC):")
print("   - AWS Console → Pinpoint → SMS and voice → Phone numbers")
print("   - Request a dedicated phone number")
print("   - Register company and campaign (10DLC)")
print("   - Update code to use origination number instead of Sender ID")

print("\n3. Quick Test with Verified Number:")
print("   - AWS Console → SNS → Text messaging (SMS) → Sandbox")
print("   - Add your phone number to verified list")
print("   - Test again")

print("\n4. Wait and Check:")
print("   - SMS can take 1-5 minutes to deliver")
print("   - Check spam/blocked messages on your phone")
print("   - Try a different phone number")

print("\n📚 Documentation:")
print("   https://docs.aws.amazon.com/sns/latest/dg/sns-sms-sandbox.html")
print("   https://docs.aws.amazon.com/sns/latest/dg/channels-sms-originating-identities.html")

print("\n" + "=" * 60)
