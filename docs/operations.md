# Operations, costs, reliability and limitations

## Local health and logs

- `docker compose ps` shows container health; `docker compose logs -f api` displays backend logs.
- `GET /api/health` checks process readiness only. It does not guarantee PostgreSQL, S3 or Secrets Manager availability.
- Uploaded originals and PostgreSQL use named Docker volumes. `docker compose down -v` deletes those volumes irreversibly.
- `python -m pytest -q` under `backend/` tests auth, valid imports, duplicate-file behavior, failed validation atomicity, search, reports and CSV-export escaping using isolated in-memory SQLite. Validate PostgreSQL-specific behavior in Docker before deployment.

## AWS deployment

The Terraform configuration in `infra/` requires AWS credentials, AWS CLI, Docker, Terraform, an existing OIDC provider, and an immutable ECR container image. See the [deployment guide](deployment.md). GitHub Actions runs backend tests and a frontend build; infrastructure deployment is a separate step.

The RDS instance is Single-AZ and the single NAT Gateway sits in one AZ. This configuration is designed for a single-region deployment, not high availability. Postgres DDL runs automatically at application startup: use migrations in a controlled release job for multi-instance deployment.

## Cost and teardown

**Review projected AWS charges before running `terraform apply`.** RDS charges while provisioned and a NAT Gateway can accrue hourly and traffic charges even with zero incoming API requests. Additional charges can accrue for storage, ECR, CloudWatch, Secrets Manager, data transfer, and API/Lambda usage. Exact charges depend on region and current pricing; use the AWS Pricing Calculator and AWS Budgets in your own account before deployment. The RDS configuration has `skip_final_snapshot=true` and one-day automated backup retention; adjust backups, availability, and deletion protection before production use.

To remove AWS resources after exporting or backing up data:

```bash
cd infra
terraform plan -destroy
# Review resources and data-loss impact before proceeding.
terraform destroy
```

**Destroy caveat:** The S3 bucket has `force_destroy=false` and versioning enabled. Terraform will not remove a nonempty bucket. Empty *all object versions and delete markers* deliberately before destroy, after checking retention needs. An ECR repository containing images may also require you to delete images deliberately. Review RDS snapshot settings before provisioning. Removing the stack can permanently delete application state.

## Correctness and scaling limitations

- Each upload is fully buffered in memory with a 2 MiB application limit. API Gateway and Lambda impose their own payload/request limits; large files need presigned S3 uploads and asynchronous processing.
- CSV ingestion upserts one record at a time; use PostgreSQL staging tables and batch upserts for substantial data volume.
- Local API-key authentication is intended for local development. The cloud configuration requires an external JWT issuer, and hosted frontend login is configured separately.
- Browser frontend is developed locally; `frontend/dist` can be hosted separately after you configure the correct API URL, HTTPS, CORS origin, and identity-provider login.
- Source-file upload precedes database commit. If the commit fails, a content-addressed S3 orphan can remain. Implement a reconciliation job or queue for stronger durability guarantees.
- A repeated exact file hash is treated as a no-op even if a different import subsequently updated the same SKU. For production, implement versioned batches and clear replace/append semantics.
- `AUTH_MODE=apigw_jwt` intentionally relies on the API Gateway JWT authorizer as the **only** public invocation route. Do not create a public Lambda URL or give untrusted principals direct Lambda invoke access; the app does not verify JWT signatures itself.
- Inventory value is not a general-ledger valuation and low-stock thresholds are site-specific inputs rather than demand forecasts.
