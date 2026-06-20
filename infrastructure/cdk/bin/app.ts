#!/usr/bin/env node
import 'source-map-support/register'
import * as cdk from 'aws-cdk-lib'
import { NocStack } from '../lib/noc-stack'

const app = new cdk.App()
new NocStack(app, 'NocStack', {
  env: {
    account: process.env.AWS_ACCOUNT_ID || process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.AWS_REGION || 'me-south-1',
  },
  tags: {
    Project: 'NOC-Agentic-AI',
    Environment: 'production',
    Owner: 'FDE-Team',
  },
})
