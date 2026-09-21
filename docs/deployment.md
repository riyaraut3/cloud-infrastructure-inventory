# AWS deployment guide — requires your AWS account and OIDC provider

> This repo does **not** auto-deploy or claim a running AWS environment. The cloud deployment incurs charges (notably RDS and NAT Gateway) and requires explicit action in your own account. Read [operations](operations.md) and [security](security.md) before running these commands.

## Prerequisites

AWS CLI v2 configured for the desired AWS account, Terraform 1.6+, Docker with `linux/amd64` support, a region supporting the requested services, and an **existing** OIDC issuer (such as a Cognito user pool and app client). Your identity needs permissions for all Terraform-created resources. Configure an AWS Budget before provisioning. No existing OIDC provider is created by Terraform.

## 1. Create the ECR repository only

```bash
cd infra
terraform init
terraform plan -target=aws_ecr_repository.api
terraform apply -target=aws_ecr_repository.api
terraform output -raw ecr_repository_url
```

Targeted apply is used **only as a bootstrap** for the container registry. Review the full plan before proceeding; do not mistake a successful ECR bootstrap for a working deployment.

## 2. Build and push the Lambda image

From the project root:

```bash
export AWS_REGION=us-east-1
export ECR_URL=$(cd infra && terraform output -raw ecr_repository_url)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker build --platform linux/amd64 -f backend/Dockerfile.lambda -t "$ECR_URL:demo-v1" backend
docker push "$ECR_URL:demo-v1"
aws ecr describe-images --repository-name "$(basename "$ECR_URL")" --image-ids imageTag=demo-v1 --region "$AWS_REGION" --query 'imageDetails[0].imageDigest' --output text
```

Set `lambda_image_uri` in `infra/terraform.tfvars` to the *immutable digest URI* `<ECR_URL>@sha256:<the returned digest>`. The example repository uses immutable tags. If your machine is ARM-based (Apple Silicon), keep `--platform linux/amd64` to match Terraform Lambda architecture `x86_64`.

## 3. Configure JWT protection and deploy

Copy `infra/terraform.tfvars.example` to `infra/terraform.tfvars` (excluded by `.gitignore`; verify this if committing settings). Set the digest image URI, issuer URL, application audience/client ID, region, and a precise `allowed_origin`. The existing OIDC provider must issue an access/ID token accepted by API Gateway's JWT authorizer. You must provision and control your own identity provider and valid users.

```bash
cd infra
terraform plan -out=deploy.tfplan
terraform apply deploy.tfplan
terraform output api_endpoint
```

This provisions a VPC, public/private subnets, NAT Gateway, private RDS Postgres with an RDS-managed secret, private S3 bucket, ECR repo, Lambda container function, JWT-protected API Gateway HTTP API, IAM policies, and CloudWatch logs. Note: database `create_all` is invoked by the application lifecycle on the first successful request. Use migrations for production. The API Gateway endpoint will return 401 for absent/invalid JWTs, including `/api/health`.

## 4. Call the API and connect the UI

```bash
export API_URL=$(cd infra && terraform output -raw api_endpoint)
export JWT='paste-a-valid-short-lived-token-from-your-existing-identity-provider'
curl -H "Authorization: Bearer ${JWT}" "$API_URL/api/health"
curl -H "Authorization: Bearer ${JWT}" -F "file=@sample-data/inventory.csv" "$API_URL/api/inventory/imports"
```

For browser development, set `VITE_API_BASE_URL` to the output API endpoint and `VITE_AUTH_MODE=bearer`, then run the frontend. The UI accepts a manually obtained JWT in memory. **This is not a finished production web sign-in experience**; to offer public users an actual hosted application, implement Cognito authorization-code-with-PKCE sign-in, serve the compiled frontend over HTTPS (for example, CloudFront + S3), and update `allowed_origin` to match the hosted domain.

## 5. Confirm, document, and remove

Check the S3 source object, RDS rows, API Gateway authorization behavior, Lambda and API Gateway CloudWatch logs, and AWS billing. Record only screenshots of your own test data, not credentials or proprietary work records. Follow [teardown steps](operations.md) to avoid ongoing charges.
