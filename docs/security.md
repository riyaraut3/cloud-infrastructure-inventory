# Threat model and security considerations

**Data handling:** Sample files use fictional site, supplier, and inventory information. Do not upload proprietary infrastructure, purchasing records, personal data, or production credentials to a public repository.

| Threat | Current mitigation | Production follow-up |
|---|---|---|
| Unauthorized browser access | Local non-default `X-API-Key`; JWT authorizer on **all** AWS API routes | Add Cognito hosted PKCE login, group/role authorization, per-user tenant policies |
| Public storage | S3 public-access block, bucket SSE-S3, key derived from SHA-256 | Add audit trail, KMS key policy, retention, malware scan for broader file types |
| Database exposure | RDS `publicly_accessible=false`, inbound port 5432 only from Lambda SG | Use app-specific least-privilege DB credentials instead of RDS master user; add RDS Proxy |
| Credentials in source | `.env` and Terraform state ignored in Git; RDS-managed secret retrieved by Lambda | Encrypt/secure remote Terraform state, rotate secrets, use short-lived CI roles |
| SQL injection | SQLAlchemy expression parameters; escaped user-provided `LIKE` wildcards | SAST/DAST and query auditing |
| Oversized/malformed imports | 2 MiB and 5,000-row caps, strict headers/fields, atomic validation | Queue, async virus scan, streaming multipart guard at edge, quota and rate limit |
| Spreadsheet formula injection | Prefix likely formula values in CSV export with an apostrophe | Security-test downstream consumers |
| Public application costs/abuse | JWT protects cloud API; Lambda has reserved concurrency 5 | API Gateway throttling, AWS Budgets, account controls, WAF if appropriate |

**Do not reuse the local key in a public website.** Browser API keys are visible to anyone using the page; the AWS deployment uses a separate JWT auth boundary. The React UI keeps the entered credential in component memory only; it is still visible to browser extensions and developer tools. TLS is provided by the API Gateway HTTPS endpoint; the local Docker example is localhost HTTP.

The cloud template grants Lambda S3 `PutObject` limited to `imports/*`, and Secrets Manager `GetSecretValue` for the specific managed RDS secret. The AWS-managed VPC execution policy grants network-interface and basic log permissions. Production should tighten general egress and remove use of the RDS master account.

**Deployment considerations:** A public-facing application also requires identity-provider integration, per-user authorization, credential rotation, audit logging, browser security configuration, and production security review.
