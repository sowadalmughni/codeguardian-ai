# infra/__main__.py

import pulumi
import pulumi_aws as aws
import json

# --- Configuration ---
# Load Pulumi config values (set using `pulumi config set <key> <value>`)
config = pulumi.Config()
aws_region = config.get("aws_region") or aws.get_region().name
app_name = config.get("app_name") or "codeguardian"
stage = pulumi.get_stack()

# You would typically configure secrets like DB passwords or API keys via Pulumi secrets
# e.g., db_password = config.require_secret("db_password")

# --- Networking (Optional but Recommended) ---
# Create a VPC, subnets, security groups for better isolation
# For simplicity, this example uses the default VPC

# --- IAM Roles ---
# Role for Lambda/ECS task execution (adjust permissions as needed)
app_execution_role = aws.iam.Role(f"{app_name}-exec-role-{stage}",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": ["lambda.amazonaws.com", "ecs-tasks.amazonaws.com"]
            }
        }]
    }),
    # Attach necessary policies (e.g., CloudWatch Logs, SQS access, Secrets Manager access)
    managed_policy_arns=[
        aws.iam.ManagedPolicy.AWS_LAMBDA_BASIC_EXECUTION_ROLE,
        # Add policies for SQS, Secrets Manager, potentially RDS access
    ]
)

# --- Secrets Manager ---
# Placeholder for storing secrets like API keys, DB credentials
app_secrets = aws.secretsmanager.Secret(f"{app_name}-secrets-{stage}",
    name=f"{app_name}/{stage}/secrets",
    description="Stores secrets for the CodeGuardian application.",
    # Define initial secret values (placeholders)
    secret_string=json.dumps({
        "GITHUB_APP_ID": "YOUR_GITHUB_APP_ID",
        "GITHUB_CLIENT_ID": "YOUR_GITHUB_CLIENT_ID",
        "GITHUB_CLIENT_SECRET": "YOUR_GITHUB_CLIENT_SECRET",
        "GITHUB_PRIVATE_KEY": "YOUR_GITHUB_PRIVATE_KEY_PEM_CONTENT",
        "GITHUB_WEBHOOK_SECRET": "YOUR_GITHUB_WEBHOOK_SECRET",
        "OPENAI_API_KEY": "YOUR_OPENAI_API_KEY",
        "DATABASE_URL": "placeholder_db_url", # Will be updated if RDS is created
        "REDIS_URL": "placeholder_redis_url" # Update if using Elasticache
    })
)

# --- SQS Queue ---
# Queue for decoupling webhook receiver from the AI analysis worker
analysis_queue = aws.sqs.Queue(f"{app_name}-analysis-queue-{stage}",
    name=f"{app_name}-analysis-queue-{stage}.fifo", # Use FIFO for ordering if needed
    fifo_queue=True,
    content_based_deduplication=True,
    # Configure visibility timeout, dead-letter queue etc. as needed
    visibility_timeout_seconds=300 # Adjust based on expected task duration
)

# --- Database (Placeholder - Aurora Serverless v2 Recommended) ---
# This is a simplified placeholder. A production setup would involve:
# - VPC, Subnet Groups, Security Groups
# - Parameter Groups
# - Actual Aurora Serverless v2 Cluster configuration
db_subnet_group = aws.rds.SubnetGroup(f"{app_name}-db-subnet-group-{stage}",
    # Replace with actual private subnet IDs
    subnet_ids=aws.ec2.get_subnet_ids(vpc_id=aws.ec2.get_vpc().id).ids 
)

db_security_group = aws.ec2.SecurityGroup(f"{app_name}-db-sg-{stage}",
    vpc_id=aws.ec2.get_vpc().id,
    description="Allow DB access",
    # Ingress rule allowing access from App tier (Lambda/ECS) security group
    # Egress rule allowing all outbound traffic (or restrict as needed)
)

# Placeholder - Replace with actual Aurora/RDS instance/cluster
db_instance_placeholder = aws.rds.Instance(f"{app_name}-db-placeholder-{stage}",
    instance_class="db.t3.micro", # Choose appropriate instance class
    allocated_storage=20,
    engine="postgres",
    engine_version="15", # Choose appropriate version
    name=f"{app_name}db{stage}",
    username="codeguardianadmin",
    password="replace_with_pulumi_secret", # Use Pulumi secrets
    db_subnet_group_name=db_subnet_group.name,
    vpc_security_group_ids=[db_security_group.id],
    skip_final_snapshot=True,
    publicly_accessible=False # Keep DB private
)

# --- API Gateway (HTTP API - Cheaper, Faster) ---
# API Gateway to expose the FastAPI backend
api = aws.apigatewayv2.Api(f"{app_name}-http-api-{stage}",
    name=f"{app_name}-http-api-{stage}",
    protocol_type="HTTP",
    description="HTTP API for CodeGuardian backend"
)

# --- Lambda Function (for Backend API) ---
# Package the FastAPI app (using Docker image is recommended for dependencies)
# Placeholder: Assumes a zip file deployment for simplicity
backend_lambda = aws.lambda_.Function(f"{app_name}-backend-lambda-{stage}",
    name=f"{app_name}-backend-lambda-{stage}",
    runtime="python3.11", # Match backend Python version
    handler="main.handler", # Assumes using Mangum or similar ASGI handler wrapper
    role=app_execution_role.arn,
    # code=pulumi.FileArchive("../backend"), # Path to backend code zip
    # Placeholder code:
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("../backend") # Adjust path as needed
    }),
    timeout=30,
    memory_size=512,
    environment={
        "variables": {
            "SECRETS_MANAGER_SECRET_NAME": app_secrets.name,
            "SQS_QUEUE_URL": analysis_queue.id, # Pass queue URL to backend
            "AWS_REGION": aws_region,
            # Add other necessary env vars
        }
    }
    # Add VPC config if Lambda needs to access private resources (like RDS)
)

# --- API Gateway Integration ---
# Integration between API Gateway and the Lambda function
integration = aws.apigatewayv2.Integration(f"{app_name}-lambda-integration-{stage}",
    api_id=api.id,
    integration_type="AWS_PROXY",
    integration_uri=backend_lambda.invoke_arn,
    payload_format_version="2.0"
)

# --- API Gateway Routes ---
# Route for the GitHub webhook
webhook_route = aws.apigatewayv2.Route(f"{app_name}-webhook-route-{stage}",
    api_id=api.id,
    route_key="POST /webhook/github",
    target=pulumi.Output.concat("integrations/", integration.id)
)

# Default route for other requests (e.g., /health, /auth)
default_route = aws.apigatewayv2.Route(f"{app_name}-default-route-{stage}",
    api_id=api.id,
    route_key="$default", # Catch-all route
    target=pulumi.Output.concat("integrations/", integration.id)
)

# --- API Gateway Deployment ---
# Stage for deploying the API
deployment = aws.apigatewayv2.Deployment(f"{app_name}-api-deployment-{stage}",
    api_id=api.id,
    # Pulumi automatically triggers a new deployment when routes/integrations change
    # Adding triggers explicitly ensures deployment on lambda changes etc.
    triggers={"redeployment": pulumi.Output.all(webhook_route.id, default_route.id, integration.id, backend_lambda.arn).apply(lambda args: json.dumps(args))},
    opts=pulumi.ResourceOptions(depends_on=[webhook_route, default_route])
)

api_stage = aws.apigatewayv2.Stage(f"{app_name}-api-stage-{stage}",
    api_id=api.id,
    name=stage, # e.g., 'dev', 'prod'
    deployment_id=deployment.id,
    auto_deploy=True
)

# Grant API Gateway permission to invoke the Lambda function
lambda_permission = aws.lambda_.Permission(f"{app_name}-api-lambda-permission-{stage}",
    action="lambda:InvokeFunction",
    function=backend_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=pulumi.Output.concat(api.execution_arn, "/*/*") # Allow any method on any resource path
)

# --- Worker (Placeholder - Lambda or ECS Fargate) ---
# Option 1: Lambda Worker (triggered by SQS)
worker_lambda = aws.lambda_.Function(f"{app_name}-worker-lambda-{stage}",
    name=f"{app_name}-worker-lambda-{stage}",
    runtime="python3.11", # Match worker Python version
    handler="tasks.celery_handler", # Needs a handler suitable for SQS events
    role=app_execution_role.arn,
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("../worker") # Adjust path as needed
    }),
    timeout=300, # Longer timeout for analysis tasks
    memory_size=1024, # More memory might be needed for analysis
    environment={
        "variables": {
            "SECRETS_MANAGER_SECRET_NAME": app_secrets.name,
            "GITHUB_API_BASE_URL": "https://api.github.com",
            "LLM_MODEL_NAME": "gpt-4o",
            "AWS_REGION": aws_region,
        }
    }
    # Add VPC config if worker needs to access private resources
)

# SQS Event Source Mapping to trigger the worker Lambda
sqs_event_mapping = aws.lambda_.EventSourceMapping(f"{app_name}-sqs-mapping-{stage}",
    event_source_arn=analysis_queue.arn,
    function_name=worker_lambda.name,
    batch_size=1 # Process one message at a time
)

# Option 2: ECS Fargate Worker (more complex setup, better for long-running tasks)
# Requires: ECS Cluster, Task Definition, Service, potentially Application Load Balancer
# This setup is omitted for brevity but might be preferable for production.

# --- Frontend (Placeholder - S3 + CloudFront) ---
# Bucket to host static website files
frontend_bucket = aws.s3.BucketV2(f"{app_name}-frontend-bucket-{stage}",
    bucket=f"{app_name}-frontend-{stage}-{pulumi.get_stack()}", # Globally unique name
    # acl="public-read" # Deprecated, use BucketPolicy and BucketPublicAccessBlock
)

# Allow public read access to the bucket contents
frontend_bucket_public_access_block = aws.s3.BucketPublicAccessBlock(f"{app_name}-frontend-bucket-pab-{stage}",
    bucket=frontend_bucket.id,
    block_public_acls=False,
    block_public_policy=False,
    ignore_public_acls=False,
    restrict_public_buckets=False
)

frontend_bucket_policy = aws.s3.BucketPolicy(f"{app_name}-frontend-bucket-policy-{stage}",
    bucket=frontend_bucket.id,
    policy=frontend_bucket.arn.apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": [f"{arn}/*"]
        }]
    })),
    opts=pulumi.ResourceOptions(depends_on=[frontend_bucket_public_access_block])
)

# Configure the bucket for website hosting
frontend_website = aws.s3.BucketWebsiteConfigurationV2(f"{app_name}-frontend-website-{stage}",
    bucket=frontend_bucket.id,
    index_document=aws.s3.BucketWebsiteConfigurationV2IndexDocumentArgs(suffix="index.html"),
    error_document=aws.s3.BucketWebsiteConfigurationV2ErrorDocumentArgs(key="index.html") # Optional: SPA redirect
)

# TODO: Add CloudFront distribution in front of S3 for caching and HTTPS

# --- Outputs ---
pulumi.export("api_endpoint", api_stage.invoke_url)
pulumi.export("frontend_bucket_name", frontend_bucket.bucket)
pulumi.export("frontend_bucket_website_endpoint", frontend_website.website_endpoint)
pulumi.export("analysis_queue_url", analysis_queue.id)
pulumi.export("secrets_arn", app_secrets.arn)
# Add other relevant outputs (e.g., DB endpoint, CloudFront domain)

