#!/usr/bin/env node
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Tax Agent CDK Entry Point
 * 
 * Uses the standard FAST stack with tax agent configuration.
 * Tax-specific Lambda tools are deployed separately or added to the Gateway incrementally.
 */

import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FastMainStack } from '../lib/fast-main-stack';
import { ConfigManager } from '../lib/utils/config-manager';

const app = new cdk.App();

// Load configuration from config.yaml
const configManager = new ConfigManager('config.yaml');
const config = configManager.getProps();

// Create main stack using FAST pattern
new FastMainStack(app, `${config.stack_name_base}-main`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  config: config,
});

app.synth();
