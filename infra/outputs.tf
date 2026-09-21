output "ecr_repository_url" { value = aws_ecr_repository.api.repository_url }
output "api_endpoint" { value = local.deploy_api ? aws_apigatewayv2_stage.default[0].invoke_url : "Configure lambda_image_uri, jwt_issuer and jwt_audience to deploy the API." }
output "s3_bucket" { value = aws_s3_bucket.uploads.id }
output "rds_endpoint" { value = aws_db_instance.postgres.endpoint }
output "estimated_cost_notice" { value = "This configuration provisions billable RDS and NAT Gateway resources. See docs/operations.md before applying." }
