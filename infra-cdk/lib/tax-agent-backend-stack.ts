// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Tax Agent Backend Stack
 * 
 * This stack creates the backend infrastructure for the tax document collection agent:
 * - 4 DynamoDB tables (clients, documents, followups, settings)
 * - S3 bucket for client documents
 * - 5 Gateway Lambda tools
 * - AgentCore Gateway with tool targets
 * - AgentCore Runtime with Strands agent
 * - AgentCore Memory
 * - EventBridge automation
 * - CloudWatch monitoring
 */

import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as agentcore from '@aws-cdk/aws-bedrock-agentcore-alpha';
import * as bedrockagentcore from 'aws-cdk-lib/aws-bedrockagentcore';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets';
import { Construct } from 'constructs';
import { AppConfig } from './utils/config-manager';
import { AgentCoreRole } from './utils/agentcore-role';
import * as path from 'path';
import * as fs from 'fs';

export interface TaxAgentBackendStackProps extends cdk.NestedStackProps {
  config: AppConfig;
  userPoolId: string;
  userPoolClientId: string;
  userPoolDomain: cognito.UserPoolDomain;
  frontendUrl: string;
}

export class TaxAgentBackendStack extends cdk.NestedStack {
  public readonly runtimeArn: string;
  public readonly memoryArn: string;
  public readonly gatewayUrl: string;

  constructor(scope: Construct, id: string, props: TaxAgentBackendStackProps) {
    super(scope, id, props);

    const userPool = cognito.UserPool.fromUserPoolId(
      this,
      'ImportedUserPool',
      props.userPoolId
    );

    // Create Machine-to-Machine authentication
    const { machineClient, resourceServer } = this.createMachineAuthentication(
      props.config,
      userPool
    );

    // Create DynamoDB tables
    const tables = this.createDynamoDBTables(props.config);

    // Create S3 bucket
    const clientBucket = this.createS3Bucket(props.config);

    // Create SNS topic
    const escalationTopic = this.createSNSTopic(props.config);

    // Create Gateway Lambda tools
    const lambdaFunctions = this.createGatewayLambdas(
      props.config,
      tables,
      clientBucket,
      escalationTopic
    );

    // Create Upload functionality (presigned URLs + S3 event processing)
    const uploadComponents = this.createUploadFunctionality(
      props.config,
      tables,
      clientBucket
    );

    // Create AgentCore Gateway
    const gateway = this.createAgentCoreGateway(
      props.config,
      userPool,
      machineClient,
      lambdaFunctions
    );

    this.gatewayUrl = gateway.attrGatewayUrl;

    // Create AgentCore Memory
    const memory = this.createAgentCoreMemory(props.config);
    this.memoryArn = memory.getAtt('MemoryArn').toString();

    // Create AgentCore Runtime
    const runtime = this.createAgentCoreRuntime(
      props.config,
      userPool,
      memory,
      gateway
    );

    this.runtimeArn = runtime.agentRuntimeArn;

    // Create EventBridge automation
    this.createEventBridgeAutomation(props.config, runtime, tables);

    // Create CloudWatch monitoring
    this.createCloudWatchMonitoring(props.config, lambdaFunctions, tables);

    // Store configuration in SSM
    this.createSSMParameters(props.config, machineClient);

    // Create outputs
    this.createOutputs(props.config, runtime, memory, gateway, clientBucket, escalationTopic, uploadComponents.uploadApi);
  }

  private createMachineAuthentication(
    config: AppConfig,
    userPool: cognito.IUserPool
  ): { machineClient: cognito.UserPoolClient; resourceServer: cognito.UserPoolResourceServer } {
    const resourceServer = new cognito.UserPoolResourceServer(this, 'ResourceServer', {
      userPool: userPool,
      identifier: `${config.stack_name_base}-gateway`,
      userPoolResourceServerName: `${config.stack_name_base}-gateway-resource-server`,
      scopes: [
        new cognito.ResourceServerScope({
          scopeName: 'read',
          scopeDescription: 'Read access to gateway',
        }),
        new cognito.ResourceServerScope({
          scopeName: 'write',
          scopeDescription: 'Write access to gateway',
        }),
      ],
    });

    const machineClient = new cognito.UserPoolClient(this, 'MachineClient', {
      userPool: userPool,
      userPoolClientName: `${config.stack_name_base}-machine-client`,
      generateSecret: true,
      oAuth: {
        flows: {
          clientCredentials: true,
        },
        scopes: [
          cognito.OAuthScope.resourceServer(
            resourceServer,
            new cognito.ResourceServerScope({
              scopeName: 'read',
              scopeDescription: 'Read access to gateway',
            })
          ),
          cognito.OAuthScope.resourceServer(
            resourceServer,
            new cognito.ResourceServerScope({
              scopeName: 'write',
              scopeDescription: 'Write access to gateway',
            })
          ),
        ],
      },
    });

    machineClient.node.addDependency(resourceServer);

    return { machineClient, resourceServer };
  }

  // Continue in next message...
}

  private createDynamoDBTables(config: AppConfig): {
    clientsTable: dynamodb.Table;
    documentsTable: dynamodb.Table;
    followupTable: dynamodb.Table;
    settingsTable: dynamodb.Table;
  } {
    // Clients Table with provisioned capacity for cost optimization
    const clientsTable = new dynamodb.Table(this, 'ClientsTable', {
      tableName: `${config.stack_name_base}-clients`,
      partitionKey: { name: 'client_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'tax_year', type: dynamodb.AttributeType.NUMBER },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Auto-scaling for burst traffic
    clientsTable.autoScaleReadCapacity({ minCapacity: 1, maxCapacity: 5 })
      .scaleOnUtilization({ targetUtilizationPercent: 70 });
    clientsTable.autoScaleWriteCapacity({ minCapacity: 1, maxCapacity: 3 })
      .scaleOnUtilization({ targetUtilizationPercent: 70 });

    // GSI for querying by accountant
    clientsTable.addGlobalSecondaryIndex({
      indexName: 'accountant-index',
      partitionKey: { name: 'accountant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      readCapacity: 1,
      writeCapacity: 1,
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Documents Table
    const documentsTable = new dynamodb.Table(this, 'DocumentsTable', {
      tableName: `${config.stack_name_base}-documents`,
      partitionKey: { name: 'client_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'document_type', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    documentsTable.autoScaleReadCapacity({ minCapacity: 1, maxCapacity: 5 })
      .scaleOnUtilization({ targetUtilizationPercent: 70 });
    documentsTable.autoScaleWriteCapacity({ minCapacity: 1, maxCapacity: 3 })
      .scaleOnUtilization({ targetUtilizationPercent: 70 });

    // Follow-up History Table
    const followupTable = new dynamodb.Table(this, 'FollowupTable', {
      tableName: `${config.stack_name_base}-followups`,
      partitionKey: { name: 'client_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'followup_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    followupTable.autoScaleReadCapacity({ minCapacity: 1, maxCapacity: 5 })
      .scaleOnUtilization({ targetUtilizationPercent: 70 });
    followupTable.autoScaleWriteCapacity({ minCapacity: 1, maxCapacity: 3 })
      .scaleOnUtilization({ targetUtilizationPercent: 70 });

    // Settings Table
    const settingsTable = new dynamodb.Table(this, 'SettingsTable', {
      tableName: `${config.stack_name_base}-settings`,
      partitionKey: { name: 'accountant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'settings_type', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    return { clientsTable, documentsTable, followupTable, settingsTable };
  }

  private createS3Bucket(config: AppConfig): s3.Bucket {
    const clientBucket = new s3.Bucket(this, 'ClientDocuments', {
      bucketName: `${config.stack_name_base}-client-docs-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      intelligentTieringConfigurations: [{
        name: 'TaxDocumentTiering',
        archiveAccessTierTime: cdk.Duration.days(90),
        deepArchiveAccessTierTime: cdk.Duration.days(180),
      }],
      lifecycleRules: [{
        transitions: [
          { storageClass: s3.StorageClass.GLACIER, transitionAfter: cdk.Duration.days(120) },
          { storageClass: s3.StorageClass.DEEP_ARCHIVE, transitionAfter: cdk.Duration.days(365) }
        ],
        expiration: cdk.Duration.days(2555), // 7 years for tax records
      }],
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    return clientBucket;
  }

  private createSNSTopic(config: AppConfig): sns.Topic {
    const escalationTopic = new sns.Topic(this, 'EscalationTopic', {
      topicName: `${config.stack_name_base}-escalations`,
      displayName: 'Tax Agent Client Escalations',
    });

    return escalationTopic;
  }

  private createGatewayLambdas(
    config: AppConfig,
    tables: {
      clientsTable: dynamodb.Table;
      documentsTable: dynamodb.Table;
      followupTable: dynamodb.Table;
      settingsTable: dynamodb.Table;
    },
    clientBucket: s3.Bucket,
    escalationTopic: sns.Topic
  ): {
    documentChecker: lambda.Function;
    emailSender: lambda.Function;
    statusTracker: lambda.Function;
    escalationManager: lambda.Function;
    requirementManager: lambda.Function;
  } {
    const sesFromEmail = `noreply@${config.stack_name_base}.example.com`;

    // Common Lambda layer
    const commonLayer = new lambda.LayerVersion(this, 'CommonLayer', {
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/layers/common')),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Common utilities for Gateway tools',
    });

    // Document Checker Lambda
    const documentChecker = new lambda.Function(this, 'DocumentChecker', {
      functionName: `${config.stack_name_base}-document-checker`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'document_checker_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/document_checker')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      layers: [commonLayer],
      environment: {
        CLIENTS_TABLE: tables.clientsTable.tableName,
        DOCUMENTS_TABLE: tables.documentsTable.tableName,
        CLIENT_BUCKET: clientBucket.bucketName,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    tables.clientsTable.grantReadData(documentChecker);
    tables.documentsTable.grantReadWriteData(documentChecker);
    clientBucket.grantRead(documentChecker);

    // Email Sender Lambda
    const emailSender = new lambda.Function(this, 'EmailSender', {
      functionName: `${config.stack_name_base}-email-sender`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'email_sender_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/email_sender')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      layers: [commonLayer],
      environment: {
        CLIENTS_TABLE: tables.clientsTable.tableName,
        FOLLOWUP_TABLE: tables.followupTable.tableName,
        SETTINGS_TABLE: tables.settingsTable.tableName,
        SES_FROM_EMAIL: sesFromEmail,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    tables.clientsTable.grantReadData(emailSender);
    tables.followupTable.grantReadWriteData(emailSender);
    tables.settingsTable.grantReadData(emailSender);
    emailSender.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail', 'ses:SendRawEmail'],
      resources: ['*'],
    }));

    // Status Tracker Lambda
    const statusTracker = new lambda.Function(this, 'StatusTracker', {
      functionName: `${config.stack_name_base}-status-tracker`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'status_tracker_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/status_tracker')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      layers: [commonLayer],
      environment: {
        CLIENTS_TABLE: tables.clientsTable.tableName,
        DOCUMENTS_TABLE: tables.documentsTable.tableName,
        FOLLOWUP_TABLE: tables.followupTable.tableName,
        SETTINGS_TABLE: tables.settingsTable.tableName,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    tables.clientsTable.grantReadData(statusTracker);
    tables.documentsTable.grantReadData(statusTracker);
    tables.followupTable.grantReadData(statusTracker);
    tables.settingsTable.grantReadData(statusTracker);

    // Escalation Manager Lambda
    const escalationManager = new lambda.Function(this, 'EscalationManager', {
      functionName: `${config.stack_name_base}-escalation-manager`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'escalation_manager_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/escalation_manager')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      layers: [commonLayer],
      environment: {
        CLIENTS_TABLE: tables.clientsTable.tableName,
        FOLLOWUP_TABLE: tables.followupTable.tableName,
        SETTINGS_TABLE: tables.settingsTable.tableName,
        SES_FROM_EMAIL: sesFromEmail,
        ESCALATION_SNS_TOPIC: escalationTopic.topicArn,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    tables.clientsTable.grantReadWriteData(escalationManager);
    tables.followupTable.grantReadWriteData(escalationManager);
    tables.settingsTable.grantReadData(escalationManager);
    escalationTopic.grantPublish(escalationManager);
    escalationManager.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail', 'ses:SendRawEmail'],
      resources: ['*'],
    }));

    // Requirement Manager Lambda
    const requirementManager = new lambda.Function(this, 'RequirementManager', {
      functionName: `${config.stack_name_base}-requirement-manager`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'requirement_manager_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/requirement_manager')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      layers: [commonLayer],
      environment: {
        CLIENTS_TABLE: tables.clientsTable.tableName,
        DOCUMENTS_TABLE: tables.documentsTable.tableName,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    tables.clientsTable.grantReadData(requirementManager);
    tables.documentsTable.grantReadWriteData(requirementManager);

    return {
      documentChecker,
      emailSender,
      statusTracker,
      escalationManager,
      requirementManager,
    };
  }

  private createUploadFunctionality(
    config: AppConfig,
    tables: {
      clientsTable: dynamodb.Table;
      documentsTable: dynamodb.Table;
      followupTable: dynamodb.Table;
      settingsTable: dynamodb.Table;
    },
    clientBucket: s3.Bucket
  ): {
    uploadManagerLambda: lambda.Function;
    documentProcessorLambda: lambda.Function;
    uploadApi: apigateway.RestApi;
  } {
    const sesFromEmail = `noreply@${config.stack_name_base}.example.com`;

    // Upload Manager Lambda - Generates presigned URLs
    const uploadManagerLambda = new lambda.Function(this, 'UploadManager', {
      functionName: `${config.stack_name_base}-upload-manager`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'upload_manager_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/upload_manager')),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      architecture: lambda.Architecture.ARM_64,
      environment: {
        CLIENT_BUCKET: clientBucket.bucketName,
        CLIENTS_TABLE: tables.clientsTable.tableName,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    clientBucket.grantPut(uploadManagerLambda);
    tables.clientsTable.grantReadData(uploadManagerLambda);

    // Document Processor Lambda - Processes S3 upload events
    const documentProcessorLambda = new lambda.Function(this, 'DocumentProcessor', {
      functionName: `${config.stack_name_base}-document-processor`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'document_processor_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/document_processor')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      environment: {
        DOCUMENTS_TABLE: tables.documentsTable.tableName,
        CLIENTS_TABLE: tables.clientsTable.tableName,
        SES_FROM_EMAIL: sesFromEmail,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    clientBucket.grantRead(documentProcessorLambda);
    tables.documentsTable.grantReadWriteData(documentProcessorLambda);
    tables.clientsTable.grantReadWriteData(documentProcessorLambda);
    documentProcessorLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail', 'ses:SendRawEmail'],
      resources: ['*'],
    }));

    // S3 Event Notification - Trigger processor on uploads
    clientBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(documentProcessorLambda),
      { suffix: '.pdf' }
    );

    // API Gateway for Upload URL Generation
    const uploadApi = new apigateway.RestApi(this, 'UploadApi', {
      restApiName: `${config.stack_name_base}-upload-api`,
      description: 'API for client document upload URLs',
      defaultCorsPreflightOptions: {
        allowOrigins: ['*'], // Restrict in production
        allowMethods: ['POST', 'OPTIONS'],
        allowHeaders: ['Content-Type'],
      },
      deployOptions: {
        stageName: 'prod',
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
      },
    });

    const uploadResource = uploadApi.root.addResource('upload-url');
    uploadResource.addMethod(
      'POST',
      new apigateway.LambdaIntegration(uploadManagerLambda)
    );

    // Store API URL in SSM
    new ssm.StringParameter(this, 'UploadApiUrlParam', {
      parameterName: `/${config.stack_name_base}/upload-api-url`,
      stringValue: uploadApi.url,
      description: 'Upload API Gateway URL',
    });

    return {
      uploadManagerLambda,
      documentProcessorLambda,
      uploadApi,
    };
  }

  private createAgentCoreGateway(
    config: AppConfig,
    userPool: cognito.IUserPool,
    machineClient: cognito.UserPoolClient,
    lambdaFunctions: {
      documentChecker: lambda.Function;
      emailSender: lambda.Function;
      statusTracker: lambda.Function;
      escalationManager: lambda.Function;
      requirementManager: lambda.Function;
    }
  ): bedrockagentcore.CfnGateway {
    // Create Gateway IAM role
    const gatewayRole = new iam.Role(this, 'GatewayRole', {
      assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com'),
      description: 'Role for AgentCore Gateway to invoke Lambda targets',
    });

    // Grant Gateway permission to invoke all Lambda functions
    Object.values(lambdaFunctions).forEach(fn => fn.grantInvoke(gatewayRole));

    // CloudWatch Logs permissions
    gatewayRole.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
      resources: [`arn:aws:logs:${this.region}:${this.account}:log-group:/aws/bedrock-agentcore/*`],
    }));

    // Load tool specifications
    const toolSpecs = [
      {
        name: 'check_client_documents',
        lambda: lambdaFunctions.documentChecker,
        specPath: '../../gateway/tools/document_checker/tool_spec.json',
      },
      {
        name: 'send_followup_email',
        lambda: lambdaFunctions.emailSender,
        specPath: '../../gateway/tools/email_sender/tool_spec.json',
      },
      {
        name: 'get_client_status',
        lambda: lambdaFunctions.statusTracker,
        specPath: '../../gateway/tools/status_tracker/tool_spec.json',
      },
      {
        name: 'escalate_client',
        lambda: lambdaFunctions.escalationManager,
        specPath: '../../gateway/tools/escalation_manager/tool_spec.json',
      },
      {
        name: 'update_document_requirements',
        lambda: lambdaFunctions.requirementManager,
        specPath: '../../gateway/tools/requirement_manager/tool_spec.json',
      },
    ];

    // Cognito OAuth2 configuration
    const cognitoIssuer = `https://cognito-idp.${this.region}.amazonaws.com/${userPool.userPoolId}`;
    const cognitoDiscoveryUrl = `${cognitoIssuer}/.well-known/openid-configuration`;

    // Create Gateway
    const gateway = new bedrockagentcore.CfnGateway(this, 'AgentCoreGateway', {
      name: `${config.stack_name_base}-gateway`,
      roleArn: gatewayRole.roleArn,
      protocolType: 'MCP',
      protocolConfiguration: {
        mcp: {
          supportedVersions: ['2025-03-26'],
        },
      },
      authorizerType: 'CUSTOM_JWT',
      authorizerConfiguration: {
        customJwtAuthorizer: {
          allowedClients: [machineClient.userPoolClientId],
          discoveryUrl: cognitoDiscoveryUrl,
        },
      },
      description: 'Tax Document Agent Gateway with 5 Lambda tool targets',
    });

    // Create Gateway Targets for each tool
    toolSpecs.forEach((tool, index) => {
      const toolSpec = JSON.parse(
        fs.readFileSync(path.join(__dirname, tool.specPath), 'utf8')
      );

      const target = new bedrockagentcore.CfnGatewayTarget(this, `GatewayTarget${index}`, {
        gatewayIdentifier: gateway.attrGatewayIdentifier,
        name: `${tool.name}_target`,
        description: `Lambda target for ${tool.name}`,
        targetConfiguration: {
          mcp: {
            lambda: {
              lambdaArn: tool.lambda.functionArn,
              toolSchema: {
                inlinePayload: toolSpec,
              },
            },
          },
        },
        credentialProviderConfigurations: [{
          credentialProviderType: 'GATEWAY_IAM_ROLE',
        }],
      });

      target.addDependency(gateway);
    });

    return gateway;
  }

  private createAgentCoreMemory(config: AppConfig): cdk.CfnResource {
    // Create AgentCore execution role
    const agentRole = new AgentCoreRole(this, 'AgentCoreRole');

    // Create memory resource with 120-day expiration for tax season
    const memory = new cdk.CfnResource(this, 'AgentMemory', {
      type: 'AWS::BedrockAgentCore::Memory',
      properties: {
        Name: cdk.Names.uniqueResourceName(this, { maxLength: 48 }),
        EventExpiryDuration: 120, // Tax season duration
        Description: `Tax document agent memory for ${config.stack_name_base}`,
        MemoryStrategies: [], // Short-term memory only
        MemoryExecutionRoleArn: agentRole.roleArn,
        Tags: {
          Name: `${config.stack_name_base}_Memory`,
          ManagedBy: 'CDK',
        },
      },
    });

    return memory;
  }

  private createAgentCoreRuntime(
    config: AppConfig,
    userPool: cognito.IUserPool,
    memory: cdk.CfnResource,
    gateway: bedrockagentcore.CfnGateway
  ): agentcore.Runtime {
    const pattern = config.backend?.pattern || 'strands-single-agent';
    const deploymentType = config.backend.deployment_type;

    // Create agent runtime artifact
    const agentRuntimeArtifact = agentcore.AgentRuntimeArtifact.fromAsset(
      path.resolve(__dirname, '..', '..'),
      {
        platform: ecr_assets.Platform.LINUX_ARM64, // Cost optimization
        file: `patterns/${pattern}/Dockerfile`,
      }
    );

    // Configure JWT authorizer
    const authorizerConfiguration = agentcore.RuntimeAuthorizerConfiguration.usingJWT(
      `https://cognito-idp.${this.region}.amazonaws.com/${userPool.userPoolId}/.well-known/openid-configuration`,
      [props.userPoolClientId]
    );

    // Create execution role
    const agentRole = new AgentCoreRole(this, 'RuntimeRole');

    // Add memory permissions
    const memoryArn = memory.getAtt('MemoryArn').toString();
    agentRole.addToPolicy(new iam.PolicyStatement({
      sid: 'MemoryResourceAccess',
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock-agentcore:CreateEvent',
        'bedrock-agentcore:GetEvent',
        'bedrock-agentcore:ListEvents',
      ],
      resources: [memoryArn],
    }));

    // Add SSM permissions for Gateway URL lookup
    agentRole.addToPolicy(new iam.PolicyStatement({
      sid: 'SSMParameterAccess',
      effect: iam.Effect.ALLOW,
      actions: ['ssm:GetParameter', 'ssm:GetParameters'],
      resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter/${config.stack_name_base}/*`],
    }));

    // Add Gateway invoke permissions
    agentRole.addToPolicy(new iam.PolicyStatement({
      sid: 'GatewayAccess',
      effect: iam.Effect.ALLOW,
      actions: ['bedrock-agentcore:InvokeGateway'],
      resources: [gateway.attrGatewayArn],
    }));

    // Environment variables
    const envVars: { [key: string]: string } = {
      AWS_REGION: this.region,
      AWS_DEFAULT_REGION: this.region,
      MEMORY_ID: memory.getAtt('MemoryId').toString(),
      STACK_NAME: config.stack_name_base,
    };

    // Create Runtime
    const runtime = new agentcore.Runtime(this, 'Runtime', {
      runtimeName: `${config.stack_name_base.replace(/-/g, '_')}_TaxAgent`,
      agentRuntimeArtifact: agentRuntimeArtifact,
      executionRole: agentRole,
      networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingPublicNetwork(),
      protocolConfiguration: agentcore.ProtocolType.HTTP,
      environmentVariables: envVars,
      authorizerConfiguration: authorizerConfiguration,
      description: `Tax document collection agent runtime for ${config.stack_name_base}`,
    });

    return runtime;
  }

  private createEventBridgeAutomation(
    config: AppConfig,
    runtime: agentcore.Runtime,
    tables: {
      clientsTable: dynamodb.Table;
      documentsTable: dynamodb.Table;
      followupTable: dynamodb.Table;
      settingsTable: dynamodb.Table;
    }
  ): void {
    // Daily check Lambda (bypasses AgentCore for cost optimization)
    const dailyCheckLambda = new lambda.Function(this, 'DailyCheck', {
      functionName: `${config.stack_name_base}-daily-check`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromInline(`
# Placeholder for daily check Lambda
# Full implementation in scripts/automation/daily_check.py
def lambda_handler(event, context):
    print("Daily check triggered")
    return {"statusCode": 200, "body": "Daily check complete"}
`),
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      architecture: lambda.Architecture.ARM_64,
      environment: {
        RUNTIME_ARN: runtime.agentRuntimeArn,
        CLIENTS_TABLE: tables.clientsTable.tableName,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    tables.clientsTable.grantReadData(dailyCheckLambda);
    tables.documentsTable.grantReadData(dailyCheckLambda);
    tables.followupTable.grantReadWriteData(dailyCheckLambda);

    dailyCheckLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock-agentcore:InvokeRuntime'],
      resources: [runtime.agentRuntimeArn],
    }));

    // EventBridge rule for daily checks (9 AM weekdays)
    const dailyRule = new events.Rule(this, 'DailyCheckRule', {
      ruleName: `${config.stack_name_base}-daily-check`,
      description: 'Trigger daily document check at 9 AM weekdays',
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '9',
        weekDay: 'MON-FRI',
      }),
    });

    dailyRule.addTarget(new targets.LambdaFunction(dailyCheckLambda));
  }

  private createCloudWatchMonitoring(
    config: AppConfig,
    lambdaFunctions: {
      documentChecker: lambda.Function;
      emailSender: lambda.Function;
      statusTracker: lambda.Function;
      escalationManager: lambda.Function;
      requirementManager: lambda.Function;
    },
    tables: {
      clientsTable: dynamodb.Table;
      documentsTable: dynamodb.Table;
      followupTable: dynamodb.Table;
      settingsTable: dynamodb.Table;
    }
  ): void {
    // Cost Dashboard
    const dashboard = new cloudwatch.Dashboard(this, 'CostDashboard', {
      dashboardName: `${config.stack_name_base}-costs`,
    });

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Invocations',
        width: 12,
        left: [
          lambdaFunctions.documentChecker.metricInvocations({ statistic: 'Sum', period: cdk.Duration.hours(1) }),
          lambdaFunctions.emailSender.metricInvocations({ statistic: 'Sum', period: cdk.Duration.hours(1) }),
          lambdaFunctions.statusTracker.metricInvocations({ statistic: 'Sum', period: cdk.Duration.hours(1) }),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Errors',
        width: 12,
        left: [
          lambdaFunctions.documentChecker.metricErrors({ statistic: 'Sum', period: cdk.Duration.hours(1) }),
          lambdaFunctions.emailSender.metricErrors({ statistic: 'Sum', period: cdk.Duration.hours(1) }),
          lambdaFunctions.statusTracker.metricErrors({ statistic: 'Sum', period: cdk.Duration.hours(1) }),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'DynamoDB Consumed Capacity',
        width: 12,
        left: [
          tables.clientsTable.metricConsumedReadCapacityUnits({ statistic: 'Sum', period: cdk.Duration.hours(1) }),
          tables.clientsTable.metricConsumedWriteCapacityUnits({ statistic: 'Sum', period: cdk.Duration.hours(1) }),
        ],
      }),
    );

    // Cost Alarm
    const costAlarm = new cloudwatch.Alarm(this, 'DailyCostAlarm', {
      alarmName: `${config.stack_name_base}-daily-cost`,
      metric: new cloudwatch.Metric({
        namespace: 'AWS/Billing',
        metricName: 'EstimatedCharges',
        statistic: 'Maximum',
        period: cdk.Duration.hours(6),
        dimensionsMap: {
          Currency: 'USD',
        },
      }),
      threshold: 5,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
  }

  private createSSMParameters(
    config: AppConfig,
    machineClient: cognito.UserPoolClient
  ): void {
    new ssm.StringParameter(this, 'GatewayUrlParam', {
      parameterName: `/${config.stack_name_base}/gateway_url`,
      stringValue: this.gatewayUrl,
      description: 'AgentCore Gateway URL',
    });

    new ssm.StringParameter(this, 'MachineClientIdParam', {
      parameterName: `/${config.stack_name_base}/machine_client_id`,
      stringValue: machineClient.userPoolClientId,
      description: 'Cognito Machine Client ID',
    });

    new secretsmanager.Secret(this, 'MachineClientSecret', {
      secretName: `/${config.stack_name_base}/machine_client_secret`,
      secretStringValue: cdk.SecretValue.unsafePlainText(
        machineClient.userPoolClientSecret.unsafeUnwrap()
      ),
      description: 'Machine Client Secret for M2M authentication',
    });

    new ssm.StringParameter(this, 'RuntimeArnParam', {
      parameterName: `/${config.stack_name_base}/runtime-arn`,
      stringValue: this.runtimeArn,
      description: 'AgentCore Runtime ARN',
    });
  }

  private createOutputs(
    config: AppConfig,
    runtime: agentcore.Runtime,
    memory: cdk.CfnResource,
    gateway: bedrockagentcore.CfnGateway,
    clientBucket: s3.Bucket,
    escalationTopic: sns.Topic,
    uploadApi: apigateway.RestApi
  ): void {
    new cdk.CfnOutput(this, 'RuntimeArn', {
      value: runtime.agentRuntimeArn,
      description: 'AgentCore Runtime ARN',
      exportName: `${config.stack_name_base}-RuntimeArn`,
    });

    new cdk.CfnOutput(this, 'MemoryId', {
      value: memory.getAtt('MemoryId').toString(),
      description: 'AgentCore Memory ID',
    });

    new cdk.CfnOutput(this, 'MemoryArn', {
      value: memory.getAtt('MemoryArn').toString(),
      description: 'AgentCore Memory ARN',
      exportName: `${config.stack_name_base}-MemoryArn`,
    });

    new cdk.CfnOutput(this, 'GatewayUrl', {
      value: gateway.attrGatewayUrl,
      description: 'AgentCore Gateway URL',
      exportName: `${config.stack_name_base}-GatewayUrl`,
    });

    new cdk.CfnOutput(this, 'GatewayId', {
      value: gateway.attrGatewayIdentifier,
      description: 'AgentCore Gateway ID',
    });

    new cdk.CfnOutput(this, 'ClientBucket', {
      value: clientBucket.bucketName,
      description: 'S3 Bucket for client documents',
    });

    new cdk.CfnOutput(this, 'EscalationTopicArn', {
      value: escalationTopic.topicArn,
      description: 'SNS Topic for escalation notifications',
    });

    new cdk.CfnOutput(this, 'UploadApiUrl', {
      value: uploadApi.url,
      description: 'Upload API Gateway URL for client uploads',
      exportName: `${config.stack_name_base}-UploadApiUrl`,
    });
  }
}
