locals {
  prefix = "${var.project}-${var.environment}"
  deploy_api = var.lambda_image_uri != "" && var.jwt_issuer != "" && var.jwt_audience != ""
  tags = { Project = var.project, Environment = var.environment, ManagedBy = "Terraform" }
}

data "aws_availability_zones" "available" { state = "available" }
data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "api" {
  name                 = "${local.prefix}-api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.tags
}

resource "aws_vpc" "main" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = merge(local.tags, { Name = "${local.prefix}-vpc" })
}
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags = local.tags
}
resource "aws_subnet" "public" {
  count = 2
  vpc_id = aws_vpc.main.id
  cidr_block = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false
  tags = merge(local.tags, { Name = "${local.prefix}-public-${count.index + 1}" })
}
resource "aws_subnet" "private" {
  count = 2
  vpc_id = aws_vpc.main.id
  cidr_block = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = merge(local.tags, { Name = "${local.prefix}-private-${count.index + 1}" })
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  tags = local.tags
}
resource "aws_route" "public" {
  route_table_id = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id = aws_internet_gateway.main.id
}
resource "aws_route_table_association" "public" {
  count = 2
  subnet_id = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
resource "aws_eip" "nat" {
  domain = "vpc"
  tags = local.tags
  depends_on = [aws_internet_gateway.main]
}
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id = aws_subnet.public[0].id
  tags = local.tags
  depends_on = [aws_route_table_association.public]
}
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  tags = local.tags
}
resource "aws_route" "private" {
  route_table_id = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id = aws_nat_gateway.nat.id
}
resource "aws_route_table_association" "private" {
  count = 2
  subnet_id = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
resource "aws_security_group" "lambda" {
  name_prefix = "${local.prefix}-lambda-"
  description = "Lambda egress to RDS, S3 and Secrets Manager"
  vpc_id = aws_vpc.main.id
  egress {
    from_port = 0
  to_port = 0
  protocol = "-1"
  cidr_blocks = ["0.0.0.0/0"]
    description = "Outbound requests to AWS services over NAT and database"
  }
  tags = local.tags
}
resource "aws_security_group" "db" {
  name_prefix = "${local.prefix}-rds-"
  description = "PostgreSQL accepts only the application Lambda security group"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port = 5432
  to_port = 5432
  protocol = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description = "PostgreSQL from application only"
  }
  tags = local.tags
}
resource "aws_db_subnet_group" "main" {
  name = "${local.prefix}-db-subnets"
  subnet_ids = aws_subnet.private[*].id
  tags = local.tags
}
resource "aws_db_instance" "postgres" {
  identifier = "${local.prefix}-postgres"
  engine = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"
  allocated_storage = 20
  max_allocated_storage = 100
  storage_encrypted = true
  db_name = "inventory"
  username = "inventory_admin"
  manage_master_user_password = true
  db_subnet_group_name = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible = false
  backup_retention_period = 1
  deletion_protection = false
  skip_final_snapshot = true # DEMO ONLY: turn on snapshots/deletion protection for production.
  tags = local.tags
}
resource "aws_s3_bucket" "uploads" {
  bucket_prefix = "${local.prefix}-uploads-"
  force_destroy = false # Objects must be removed intentionally before destroy.
  tags = local.tags
}
resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    id = "expire-old-versions"
    status = "Enabled"
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}
resource "aws_iam_role" "lambda" {
  name = "${local.prefix}-lambda"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags = local.tags
}
resource "aws_iam_role_policy_attachment" "vpc" {
  role = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}
resource "aws_iam_role_policy" "api" {
  name = "${local.prefix}-resources"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:PutObject"], Resource = ["${aws_s3_bucket.uploads.arn}/imports/*"] },
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = [aws_db_instance.postgres.master_user_secret[0].secret_arn] }
    ]
  })
}
resource "aws_cloudwatch_log_group" "lambda" {
  count = local.deploy_api ? 1 : 0
  name = "/aws/lambda/${local.prefix}-api"
  retention_in_days = 14
  tags = local.tags
}
resource "aws_lambda_function" "api" {
  count = local.deploy_api ? 1 : 0
  function_name = "${local.prefix}-api"
  role = aws_iam_role.lambda.arn
  package_type = "Image"
  image_uri = var.lambda_image_uri
  architectures = ["x86_64"]
  memory_size = 512
  timeout = 30
  reserved_concurrent_executions = 5 # Keep database connection fan-out bounded for a demo.
  vpc_config {
    subnet_ids = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }
  environment {
    variables = {
      AUTH_MODE = "apigw_jwt"
      APP_DB_SECRET_ARN = aws_db_instance.postgres.master_user_secret[0].secret_arn
      APP_DB_HOST = aws_db_instance.postgres.address
      APP_DB_NAME = aws_db_instance.postgres.db_name
      S3_BUCKET = aws_s3_bucket.uploads.id
      CORS_ORIGINS = var.allowed_origin
    }
  }
  depends_on = [aws_iam_role_policy_attachment.vpc, aws_iam_role_policy.api, aws_cloudwatch_log_group.lambda]
  tags = local.tags
}
resource "aws_apigatewayv2_api" "http" {
  count = local.deploy_api ? 1 : 0
  name = "${local.prefix}-http-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = [var.allowed_origin]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["authorization", "content-type"]
    max_age = 300
  }
  tags = local.tags
}
resource "aws_apigatewayv2_authorizer" "jwt" {
  count = local.deploy_api ? 1 : 0
  api_id = aws_apigatewayv2_api.http[0].id
  authorizer_type = "JWT"
  name = "${local.prefix}-jwt"
  identity_sources = ["$request.header.Authorization"]
  jwt_configuration {
    audience = [var.jwt_audience]
    issuer = var.jwt_issuer
  }
}
resource "aws_apigatewayv2_integration" "lambda" {
  count = local.deploy_api ? 1 : 0
  api_id = aws_apigatewayv2_api.http[0].id
  integration_type = "AWS_PROXY"
  integration_uri = aws_lambda_function.api[0].invoke_arn
  payload_format_version = "2.0"
}
resource "aws_apigatewayv2_route" "proxy" {
  count = local.deploy_api ? 1 : 0
  api_id = aws_apigatewayv2_api.http[0].id
  route_key = "ANY /{proxy+}"
  target = "integrations/${aws_apigatewayv2_integration.lambda[0].id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.jwt[0].id
}
resource "aws_apigatewayv2_stage" "default" {
  count = local.deploy_api ? 1 : 0
  api_id = aws_apigatewayv2_api.http[0].id
  name = "$default"
  auto_deploy = true
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api[0].arn
    format = jsonencode({ requestId = "$context.requestId", status = "$context.status", routeKey = "$context.routeKey", responseLatency = "$context.responseLatency" })
  }
  tags = local.tags
}
resource "aws_cloudwatch_log_group" "api" {
  count = local.deploy_api ? 1 : 0
  name = "/aws/apigateway/${local.prefix}"
  retention_in_days = 14
  tags = local.tags
}
resource "aws_lambda_permission" "gateway" {
  count = local.deploy_api ? 1 : 0
  statement_id = "AllowAPIGatewayInvocation"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[0].function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_apigatewayv2_api.http[0].execution_arn}/*/*"
}
