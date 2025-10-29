# GenAIID AgentCore Starter Pack - Infrastructure

This directory contains the AWS CDK infrastructure code for deploying the GenAIID AgentCore Starter Pack.

## Prerequisites

- Node.js 18+
- AWS CLI configured with appropriate credentials
- AWS CDK CLI installed: `npm install -g aws-cdk`

## Getting Started

All of the following commands assuming you are in the top of the `infra-cdk/` directory
### Install Dependencies

```bash
npm install
```

### Build TypeScript

```bash
npm run build
```

### Bootstrap CDK (First Time Only)

```bash
npx cdk bootstrap
```

### Deploy

```bash
npx cdk deploy --all
```

## Useful Commands

* `npm run build`   - Compile TypeScript to JavaScript
* `npm run watch`   - Watch for changes and compile automatically
* `npm run test`    - Run Jest unit tests
* `npx cdk deploy --all` - Deploy all stacks to your AWS account/region
* `npx cdk diff`    - Compare deployed stack with current state
* `npx cdk synth`   - Emit the synthesized CloudFormation template
* `npx cdk destroy --all` - Remove all deployed resources

## Configuration

Edit `config.yaml` to customize your deployment:

```yaml
stack_name_base: "genaiid-agentcore-starter-pack"

frontend:
  domain_name: null  # Optional: Set to your custom domain
  certificate_arn: null  # Optional: Set to your ACM certificate ARN

backend:
  pattern: "strands-single-agent"  # Available patterns: strands-single-agent
```

## Project Structure

```
infra-cdk/
├── bin/
│   └── gasp-cdk.ts          # CDK app entry point
├── lib/
│   ├── gasp-cdk-stack.ts    # Main orchestrator stack
│   ├── backend-stack.ts     # Backend/AgentCore stack
│   ├── frontend-stack.ts    # Frontend/CloudFront stack
│   └── utils/               # Utility functions and constructs
├── test/
│   └── gasp-cdk.test.ts     # Unit tests
├── cdk.json                 # CDK configuration
├── config.yaml              # Application configuration
├── package.json
└── tsconfig.json
```

## Development Workflow

1. Make changes to TypeScript files in `lib/`
2. Run `npm run build` to compile
3. Run `npx cdk diff` to see what will change
4. Run `npx cdk deploy --all` to deploy changes

For faster iteration, use watch mode:
```bash
npm run watch
```

## Deployment Details

The CDK deployment creates:

1. **Backend Stack**: 
   - Cognito User Pool for authentication
   - ECR repository for agent container
   - CodeBuild project to build agent image
   - Bedrock AgentCore runtime
   - IAM roles and policies

2. **Frontend Stack**:
   - S3 bucket for static website hosting
   - CloudFront distribution with HTTPS
   - Origin Access Control (OAC) for security
   - Automatic frontend build and deployment

## Troubleshooting

### Build Errors

If you encounter TypeScript compilation errors:
```bash
npm run build
```

### Deployment Failures

Check CloudFormation events in the AWS Console for detailed error messages.

### Clean Build

If you need to start fresh:
```bash
rm -rf node_modules cdk.out
npm install
npm run build
```

## Testing

Run unit tests:
```bash
npm test
```

## Learn More

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [AWS CDK TypeScript Reference](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-construct-library.html)
- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/)
