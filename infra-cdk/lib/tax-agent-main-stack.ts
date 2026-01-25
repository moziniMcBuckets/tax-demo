// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Tax Agent Main Stack
 * 
 * Main orchestrator stack that creates and coordinates all nested stacks:
 * - CognitoStack: User authentication and authorization
 * - TaxAgentBackendStack: AgentCore runtime, gateway, and tools
 * - AmplifyHostingStack: Frontend hosting
 * 
 * This follows the FAST pattern of creating Amplify first to get predictable URLs,
 * then Cognito with those URLs, then Backend with Cognito details.
 */

import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { AppConfig } from './utils/config-manager';
import { CognitoStack } from './cognito-stack';
import { TaxAgentBackendStack } from './tax-agent-backend-stack';
import { AmplifyHostingStack } from './amplify-hosting-stack';

export interface TaxAgentMainStackProps extends cdk.StackProps {
  config: AppConfig;
}

export class TaxAgentMainStack extends cdk.Stack {
  public readonly cognitoStack: CognitoStack;
  public readonly backendStack: TaxAgentBackendStack;
  public readonly amplifyHostingStack: AmplifyHostingStack;

  constructor(scope: Construct, id: string, props: TaxAgentMainStackProps) {
    const description = 'Tax Document Collection Agent - Main Stack (v0.3.0)';
    super(scope, id, { ...props, description });

    // Step 1: Create Amplify stack to get predictable domain
    this.amplifyHostingStack = new AmplifyHostingStack(this, `${id}-amplify`, {
      config: props.config,
    });

    // Step 2: Create Cognito stack with Amplify URLs for callbacks
    this.cognitoStack = new CognitoStack(this, `${id}-cognito`, {
      config: props.config,
      callbackUrls: ['http://localhost:3000', this.amplifyHostingStack.amplifyUrl],
    });

    // Step 3: Create backend stack with Cognito details and Amplify URL
    this.backendStack = new TaxAgentBackendStack(this, `${id}-backend`, {
      config: props.config,
      userPoolId: this.cognitoStack.userPoolId,
      userPoolClientId: this.cognitoStack.userPoolClientId,
      userPoolDomain: this.cognitoStack.userPoolDomain,
      frontendUrl: this.amplifyHostingStack.amplifyUrl,
    });

    // ========================================
    // Stack Outputs
    // ========================================

    new cdk.CfnOutput(this, 'AmplifyAppId', {
      value: this.amplifyHostingStack.amplifyApp.appId,
      description: 'Amplify App ID - use this for manual deployment',
      exportName: `${props.config.stack_name_base}-AmplifyAppId`,
    });

    new cdk.CfnOutput(this, 'AmplifyUrl', {
      value: this.amplifyHostingStack.amplifyUrl,
      description: 'Frontend Application URL',
      exportName: `${props.config.stack_name_base}-AmplifyUrl`,
    });

    new cdk.CfnOutput(this, 'AmplifyConsoleUrl', {
      value: `https://console.aws.amazon.com/amplify/apps/${this.amplifyHostingStack.amplifyApp.appId}`,
      description: 'Amplify Console URL for monitoring deployments',
    });

    new cdk.CfnOutput(this, 'CognitoUserPoolId', {
      value: this.cognitoStack.userPoolId,
      description: 'Cognito User Pool ID',
      exportName: `${props.config.stack_name_base}-CognitoUserPoolId`,
    });

    new cdk.CfnOutput(this, 'CognitoClientId', {
      value: this.cognitoStack.userPoolClientId,
      description: 'Cognito User Pool Client ID',
      exportName: `${props.config.stack_name_base}-CognitoClientId`,
    });

    new cdk.CfnOutput(this, 'CognitoDomain', {
      value: `${this.cognitoStack.userPoolDomain.domainName}.auth.${cdk.Aws.REGION}.amazoncognito.com`,
      description: 'Cognito Domain for OAuth',
      exportName: `${props.config.stack_name_base}-CognitoDomain`,
    });

    new cdk.CfnOutput(this, 'RuntimeArn', {
      value: this.backendStack.runtimeArn,
      description: 'AgentCore Runtime ARN',
      exportName: `${props.config.stack_name_base}-RuntimeArn`,
    });

    new cdk.CfnOutput(this, 'MemoryArn', {
      value: this.backendStack.memoryArn,
      description: 'AgentCore Memory ARN',
      exportName: `${props.config.stack_name_base}-MemoryArn`,
    });

    new cdk.CfnOutput(this, 'GatewayUrl', {
      value: this.backendStack.gatewayUrl,
      description: 'AgentCore Gateway URL',
      exportName: `${props.config.stack_name_base}-GatewayUrl`,
    });

    new cdk.CfnOutput(this, 'StagingBucketName', {
      value: this.amplifyHostingStack.stagingBucket.bucketName,
      description: 'S3 bucket for Amplify deployment staging',
      exportName: `${props.config.stack_name_base}-StagingBucket`,
    });

    // Tax-specific outputs
    new cdk.CfnOutput(this, 'DeploymentInstructions', {
      value: 'Run: python scripts/deploy-frontend.py',
      description: 'Next step: Deploy frontend',
    });
  }
}
