"""Strict CSV contract and import behavior shared by API and unit tests."""
import csv
from decimal import Decimal, InvalidOperation
from io import StringIO

COLUMNS = ("sku", "name", "site", "supplier", "quantity", "reorder_level", "unit_cost")
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5_000


class ImportValidationError(ValueError):
    pass


def parse_inventory(data: bytes) -> list[dict]:
    if not data or len(data) > MAX_BYTES:
        raise ImportValidationError("CSV must be nonempty and at most 2 MiB")
    try:
        content = data.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise ImportValidationError("CSV must use UTF-8 encoding") from exc
    reader = csv.DictReader(StringIO(content, newline=""), strict=True)
    if reader.fieldnames is None or tuple(reader.fieldnames) != COLUMNS:
        raise ImportValidationError(f"CSV headers must be exactly: {', '.join(COLUMNS)}")

    rows = []
    seen = set()
    try:
        for line, row in enumerate(reader, start=2):
            if line > MAX_ROWS + 1:
                raise ImportValidationError(f"Maximum {MAX_ROWS} rows per import")
            if None in row or any(v is None for v in row.values()):
                raise ImportValidationError(f"Row {line}: incorrect column count")
            clean = {key: str(value).strip() for key, value in row.items()}
            if any(not clean[key] for key in ("sku", "name", "site", "supplier")):
                raise ImportValidationError(f"Row {line}: text fields are required")
            if any(len(clean[key]) > size for key, size in (
                ("sku", 80), ("name", 200), ("site", 100), ("supplier", 150)
            )):
                raise ImportValidationError(f"Row {line}: text field exceeds length limit")
            identity = (clean["sku"], clean["site"])
            if identity in seen:
                raise ImportValidationError(f"Row {line}: duplicate SKU/site in upload")
            seen.add(identity)
            try:
                quantity = int(clean["quantity"])
                reorder_level = int(clean["reorder_level"])
                cost = Decimal(clean["unit_cost"])
            except (ValueError, InvalidOperation) as exc:
                raise ImportValidationError(f"Row {line}: invalid quantity, reorder level, or unit cost") from exc
            if quantity < 0 or reorder_level < 0 or not cost.is_finite() or cost < 0 or cost > 9999999999.99 or cost.as_tuple().exponent < -2:
                raise ImportValidationError(f"Row {line}: invalid numeric range or unit cost precision")
            rows.append({
                **{k: clean[k] for k in ("sku", "name", "site", "supplier")},
                "quantity": quantity,
                "reorder_level": reorder_level,
                "unit_cost": cost,
            })
    except csv.Error as exc:
        raise ImportValidationError("Malformed CSV") from exc
    if not rows:
        raise ImportValidationError("CSV requires at least one data row")
    return rows
