# API contract

Local authentication: send `X-API-Key: <your .env API_KEY>` for all `/api` endpoints except the health check. AWS authentication: send `Authorization: Bearer <JWT>`; API Gateway authorizes before Lambda invocation. Local Swagger UI runs at `http://localhost:8000/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Basic application health, no DB readiness check |
| POST | `/api/inventory/imports` | Upload a multipart `file` containing a CSV |
| GET | `/api/parts` | Inventory search, site and low-stock filters, pagination |
| GET | `/api/reports/summary` | Aggregate metrics and breakdown per site |
| GET | `/api/reports/low-stock.csv` | Export all parts with quantity ≤ reorder level |

## CSV specification

Exactly seven case-sensitive columns in the following order:

```csv
sku,name,site,supplier,quantity,reorder_level,unit_cost
FBR-01,Fiber cable,VA-01,Example Cables,4,5,12.50
```

UTF-8 or UTF-8 with BOM; nonempty; at most 2 MiB or 5,000 data rows. No blank required text field. Maximum lengths are 80 (SKU), 200 (name), 100 (site), 150 (supplier). Quantity/reorder level are nonnegative integers. Cost is a finite nonnegative decimal with at most two decimal places, and ≤ 9,999,999,999.99. Duplicate SKU/site pairs within the same file fail validation. Original filenames are truncated to 200 characters in metadata and are never used as storage keys.

The importer only supports `.csv` file names. A malformed file returns 422. Storage failure returns 503. Conflicting concurrent uploads can return 409. Existing byte-identical files return 201 with `duplicate: true` and no inventory change; an HTTP 201 is kept for a consistent request contract in this demo.

Example import response:

```json
{"id": 1, "rows": 10, "created": 10, "updated": 0, "duplicate": false}
```

### `GET /api/parts`

Parameters: `q` (optional SKU substring, max 100 chars), `site` (optional exact site), `low_stock` (Boolean, default false), `limit` (1–200, default 50), `offset` (nonnegative, default 0).

Response shape: `{ "total": 10, "limit": 50, "offset": 0, "items": [...] }`. Rows include SKU, name, site, supplier, quantity, reorder level, unit cost, inventory value, low-stock status and timestamp. All money values are decimal strings to preserve precision.

### `GET /api/reports/summary`

Response shape: `{ "total_skus": 10, "total_units": 496, "low_stock_count": 4, "total_value": "12345.67", "by_site": [{ "site": "VA-01", "sku_count": 3, "units": 139, "low_stock_count": 1, "value": "1234.56" }] }`. Values shown here illustrate the schema; run the sample data to obtain the actual totals.

### Error and safety semantics

Authentication failures return 401 locally; AWS JWT failures are rejected by API Gateway before invoking the application. Quantity equal to reorder level counts as low stock. Search input is SQL-parameterized; wildcard characters `%` and `_` are treated literally. CSV report text beginning with common spreadsheet formula prefixes is escaped. All import data is fictional and lacks supplier contract details or real site identifiers.
