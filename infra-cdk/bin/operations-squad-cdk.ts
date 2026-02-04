#!/usr/bin/env node
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * RainCity Operations Squad CDK App
 * 
 * Minimal deployment for testing Operations Squad
 */

import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { OperationsSquadStack } from '../lib/operations-squad-stack';

const app = new cdk.App();

new OperationsSquadStack(app, 'RainCityOperationsSquad', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-west-2',
  },
  description: 'RainCity Operations Squad - AI agents for home services',
});

app.synth();
