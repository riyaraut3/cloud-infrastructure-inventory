# Application walkthrough and verification

## Local environment

1. Create `.env` from `.env.example`, choose a local API key, then run `docker compose up --build`.
2. Open `http://localhost:5173` and enter the API key.
3. Upload `sample-data/inventory.csv` to populate the parts table, site distribution, inventory value, and reorder alerts.
4. Upload the same CSV again to confirm that duplicate-file detection prevents repeated changes.
5. Change a sample quantity and import the revised CSV. The matching SKU/site record is updated.
6. Search for `TRX-`, filter by site, select **Low stock only**, and export the low-stock report.
7. Upload an invalid CSV with a negative quantity to confirm that the API rejects the file without partial changes.

## Automated checks

```bash
cd backend && python -m pip install -r requirements-dev.txt && python -m pytest -q
cd ../frontend && npm install && npm run build
```

See the [API reference](api.md), [architecture](architecture.md), and [AWS deployment guide](deployment.md) for additional details.
