# Five-minute interview demonstration

1. Show the README architecture. Explain why `(sku, site)` is the unique identity and why source CSV bytes are retained separately from queryable rows.
2. Run `docker compose up --build`, open `http://localhost:5173`, and enter your **local** API key from `.env`.
3. Upload `sample-data/inventory.csv`; show the parts table, aggregate units, site distribution, and low-stock alerts.
4. Upload the same CSV a second time. Explain why the SHA-256 duplicate check leaves inventory unchanged.
5. Edit one *synthetic* quantity and upload the changed CSV. Show that matching SKU/site is updated without duplicate rows.
6. Search for `TRX-`, filter to a site, enable **Low stock only**, and export the low-stock CSV.
7. Submit an invalid CSV with negative quantity to demonstrate a 422 response and no partial row changes. Show the pytest suite and explain the scope of automated tests.
8. Walk through Terraform files without implying they have been deployed. Highlight private RDS subnets, the Lambda IAM permissions, Secrets Manager, API Gateway JWT authorizer, CloudWatch logs, and the cost of the NAT Gateway. Explicitly distinguish local implementation from cloud provisioning.

**Resume entry to use after you have run and verified the project:** “Built a containerized inventory management application with FastAPI, PostgreSQL, React, and Docker, implementing validated, idempotent CSV ingestion, site-level inventory reporting, and low-stock alerts; authored an AWS Lambda/API Gateway/RDS/S3 deployment blueprint with JWT authorization and least-privilege IAM.”

**Only after you actually deploy and verify AWS:** Update the entry to distinguish deployed cloud components and include a genuine architecture screenshot, deployment URL, and measured results. Do not describe AWS deployment or AWS infrastructure metrics as completed until verified.
