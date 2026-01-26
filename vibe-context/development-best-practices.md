# Development Best Practices

**IF YOU ARE AN AI ASSISTANT YOU MUST FOLLOW THESE RULES**

1. Plan out complex changes before implementing anything. This plan should include searching and researching documentation in this code base for relevant guidance. Save the plan to a temporary markdown file in the repository and get human approval before beginning.
2. This repository comes equipped with a `Makefile`. Running `make all` will run linting and unit tests. In order for code to be successfully pushed through the built-in CI/CD pipeline, it will have to pass these tests. So, be sure to run linting, formatting, etc periodically to make sure the code is properly formatted and is free of linting errors.
3. **Infrastructure as Code (IaC) Requirement:** All backend infrastructure changes MUST be implemented through AWS CDK in `infra-cdk/lib/*.ts` files. Never use AWS CLI commands to create, modify, or configure AWS resources. This includes:
   - Lambda functions and their configurations
   - DynamoDB tables and indexes
   - S3 buckets and policies
   - IAM roles and permissions
   - API Gateway endpoints
   - Cognito user pools
   - Any other AWS resources
   
   The only exceptions are:
   - Temporary debugging (viewing logs, checking resource status)
   - One-time data operations (seeding test data, querying tables)
   - Emergency hotfixes (must be followed by CDK implementation)

Remember: Always prioritize code quality, security, and maintainability in your development practices.

**ALWAYS FOLLOW THESE RULES WHEN YOU WORK IN THIS PROJECT**