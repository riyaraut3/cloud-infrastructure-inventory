from io import BytesIO

HEADERS = {"X-API-Key": "test-api-key"}
DATA = (
    "sku,name,site,supplier,quantity,reorder_level,unit_cost\n"
    "FBR-01,Fiber cable,VA-1,Example Cables,4,5,12.50\n"
    "TRX-02,Transceiver,NY-2,Example Optics,10,2,90.00\n"
).encode()


def post(client, data=DATA):
    return client.post("/api/inventory/imports", headers=HEADERS, files={"file": ("inventory.csv", BytesIO(data), "text/csv")})


def test_auth_and_health(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/parts").status_code == 401
    assert client.get("/api/parts", headers={"X-API-Key": "bad"}).status_code == 401


def test_import_idempotency_search_and_reports(client):
    first = post(client)
    assert first.status_code == 201, first.text
    assert first.json()["created"] == 2
    assert post(client).json()["duplicate"] is True
    assert client.get("/api/parts", headers=HEADERS).json()["total"] == 2
    assert client.get("/api/parts?site=VA-1&low_stock=true", headers=HEADERS).json()["total"] == 1
    report = client.get("/api/reports/summary", headers=HEADERS).json()
    assert report["total_value"] == "950.00"
    assert report["low_stock_count"] == 1
    assert "FBR-01" in client.get("/api/reports/low-stock.csv", headers=HEADERS).text
    revised = DATA.replace(b"4,5,12.50", b"8,5,12.50")
    assert post(client, revised).json()["updated"] == 2
    assert client.get("/api/reports/summary", headers=HEADERS).json()["low_stock_count"] == 0


def test_bad_csv_is_atomic(client):
    invalid = DATA + b"BROKEN,Missing,VA-1,Supplier,-3,1,4.20\n"
    response = post(client, invalid)
    assert response.status_code == 422
    assert client.get("/api/parts", headers=HEADERS).json()["total"] == 0


def test_duplicate_and_max_file_size(client):
    duplicate = DATA + b"FBR-01,Duplicate,VA-1,X,1,1,1\n"
    assert post(client, duplicate).status_code == 422
    assert post(client, b"a" * (2 * 1024 * 1024 + 1)).status_code == 422


def test_csv_formula_sanitization(client):
    dirty = DATA.replace(b"Fiber cable", b"=HYPERLINK(\"\"https://example.com\"\")")
    assert post(client, dirty).status_code == 201
    exported = client.get("/api/reports/low-stock.csv", headers=HEADERS).text
    assert "'=HYPERLINK" in exported
