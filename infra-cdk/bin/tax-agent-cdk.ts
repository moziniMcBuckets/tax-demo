#!/usr/bin/env node
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Tax Agent CDK Entry Point
 * 
 * This is the main entry point for the CDK application.
 * It loads configuration and creates the main stack.
 */

import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { TaxAgentMainStack } from '../lib/tax-agent-main-stack';
import { ConfigManager } from '../lib/utils/config-manager';

const app = new cdk.App();

// Load configuration from config.yaml
const configManager = new ConfigManager();
const config = configManager.getConfig();

// Create main stack
new TaxAgentMainStack(app, `${config.stack_name_base}-main`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  config: config,
  description: 'Tax Document Collection Agent - Main Stack',
});

app.synth();
