// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * RainCity Operations Squad Stack
 * 
 * Minimal stack for deploying Operations Squad:
 * - 3 agents (Lead Response, Scheduler, Invoice)
 * - 3 Lambda tools
 * - 4 DynamoDB tables
 * - AgentCore Gateway
 */

import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import * as path from 'path';

export class OperationsSquadStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const stackName = 'raincity-ops-squad';

    // DynamoDB Tables
    const leadsTable = new dynamodb.Table(this, 'LeadsTable', {
      tableName: `${stackName}-leads`,
      partitionKey: { name: 'lead_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    leadsTable.addGlobalSecondaryIndex({
      indexName: 'org_id-status-index',
      partitionKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      readCapacity: 1,
      writeCapacity: 1,
    });

    const appointmentsTable = new dynamodb.Table(this, 'AppointmentsTable', {
      tableName: `${stackName}-appointments`,
      partitionKey: { name: 'appointment_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const techniciansTable = new dynamodb.Table(this, 'TechniciansTable', {
      tableName: `${stackName}-technicians`,
      partitionKey: { name: 'technician_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    techniciansTable.addGlobalSecondaryIndex({
      indexName: 'org_id-status-index',
      partitionKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      readCapacity: 1,
      writeCapacity: 1,
    });

    const invoicesTable = new dynamodb.Table(this, 'InvoicesTable', {
      tableName: `${stackName}-invoices`,
      partitionKey: { name: 'invoice_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    invoicesTable.addGlobalSecondaryIndex({
      indexName: 'org_id-status-index',
      partitionKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      readCapacity: 1,
      writeCapacity: 1,
    });

    // Lambda Functions for Tools
    const leadResponseFn = new lambda.Function(this, 'LeadResponseFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'lead_response_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/lead_response')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      environment: {
        LEADS_TABLE: leadsTable.tableName,
        FROM_EMAIL: 'noreply@raincity.ai',
      },
    });

    const schedulerFn = new lambda.Function(this, 'SchedulerFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'scheduler_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/scheduler')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      environment: {
        LEADS_TABLE: leadsTable.tableName,
        APPOINTMENTS_TABLE: appointmentsTable.tableName,
        TECHNICIANS_TABLE: techniciansTable.tableName,
        FROM_EMAIL: 'noreply@raincity.ai',
      },
    });

    const invoiceFn = new lambda.Function(this, 'InvoiceFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'invoice_collection_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/invoice_collection')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      environment: {
        APPOINTMENTS_TABLE: appointmentsTable.tableName,
        INVOICES_TABLE: invoicesTable.tableName,
        FROM_EMAIL: 'noreply@raincity.ai',
      },
    });

    // Grant permissions
    leadsTable.grantReadWriteData(leadResponseFn);
    leadsTable.grantReadWriteData(schedulerFn);
    
    appointmentsTable.grantReadWriteData(schedulerFn);
    appointmentsTable.grantReadWriteData(invoiceFn);
    
    techniciansTable.grantReadData(schedulerFn);
    
    invoicesTable.grantReadWriteData(invoiceFn);

    // Grant SES permissions
    [leadResponseFn, schedulerFn, invoiceFn].forEach(fn => {
      fn.addToRolePolicy(new iam.PolicyStatement({
        actions: ['ses:SendEmail', 'ses:SendRawEmail'],
        resources: ['*'],
      }));
      fn.addToRolePolicy(new iam.PolicyStatement({
        actions: ['sns:Publish'],
        resources: ['*'],
      }));
    });

    // Outputs
    new cdk.CfnOutput(this, 'LeadsTableName', {
      value: leadsTable.tableName,
      description: 'Leads table name',
    });

    new cdk.CfnOutput(this, 'LeadResponseFunctionArn', {
      value: leadResponseFn.functionArn,
      description: 'Lead Response Lambda ARN',
    });

    new cdk.CfnOutput(this, 'SchedulerFunctionArn', {
      value: schedulerFn.functionArn,
      description: 'Scheduler Lambda ARN',
    });

    new cdk.CfnOutput(this, 'InvoiceFunctionArn', {
      value: invoiceFn.functionArn,
      description: 'Invoice Lambda ARN',
    });
  }
}
