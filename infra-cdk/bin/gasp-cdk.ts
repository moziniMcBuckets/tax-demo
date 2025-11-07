#!/usr/bin/env node
import * as cdk from "aws-cdk-lib"
import { GaspCdkStack } from "../lib/gasp-cdk-stack"
import { ConfigManager } from "../lib/utils/config-manager"

// Load configuration using ConfigManager
const configManager = new ConfigManager("config.yaml")

// Initial props consist of configuration parameters
const props = configManager.getProps()

const app = new cdk.App()

const genaiidStack = new GaspCdkStack(app, props.stack_name_base, {
  config: props,
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION 
  },
})

app.synth()
