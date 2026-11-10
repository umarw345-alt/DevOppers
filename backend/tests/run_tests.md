Run from the `backend/` folder.

Unit, component and API tests (no database needed):

```powershell
uv run pytest
```

Integration tests against the running Docker stack (`docker compose up -d --build`):

```powershell
$env:RUN_INTEGRATION_TESTS = "1"
$env:AUTH_INTEGRATION_DATABASE_URL = "postgresql://<user>:<password>@127.0.0.1:5432/<db>"
uv run pytest tests/test_integration.py -q
```
