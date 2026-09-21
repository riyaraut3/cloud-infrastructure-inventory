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

For a recruiter-friendly project summary, link directly to the dedicated repository README and cite the project as *locally implemented with an AWS deployment blueprint* until you have actually deployed and tested it in your own account.
