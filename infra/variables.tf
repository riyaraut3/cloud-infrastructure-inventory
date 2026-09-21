variable "aws_region" {
  type = string
  default = "us-east-1"
}
variable "project" {
  type = string
  default = "infrastock"
}
variable "environment" {
  type = string
  default = "dev"
}
variable "lambda_image_uri" {
  type = string
  description = "ECR URI with immutable SHA256 image digest, provided after the image is pushed."
  default = ""
}
variable "jwt_issuer" {
  type = string
  description = "HTTPS issuer of an existing OIDC provider (for example, Cognito user pool issuer)."
  default = ""
}
variable "jwt_audience" {
  type = string
  description = "Audience / application client ID accepted by API Gateway JWT authorizer."
  default = ""
}
variable "allowed_origin" {
  type = string
  description = "The exact browser origin allowed to call the cloud API (no wildcard)."
  default = "http://localhost:5173"
}
