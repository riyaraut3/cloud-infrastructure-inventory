# GitHub publishing and updates

The project is published at https://github.com/riyaraut3/cloud-infrastructure-inventory.

## Clone and update

```bash
git clone https://github.com/riyaraut3/cloud-infrastructure-inventory.git
cd cloud-infrastructure-inventory
# edit your files; run tests before pushing
git status
git add .
git commit -m "Improve InfraStock"
git push origin main
```

The included `.gitignore` excludes local secrets, Terraform state and generated build artifacts. **Before every push, run `git status` and check what you are publishing.** If you later deploy to AWS, do not check in your `.env`, `infra/terraform.tfvars`, JWTs, key files, billing identifiers or backend credentials.

For system design and setup details, see the [README](../README.md) and [AWS deployment guide](deployment.md).
