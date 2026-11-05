.\.venv\Scripts\python.exe -m pytest backend\tests\test_security.py backend\tests\test_rate_limit.py -q

$env:RUN_INTEGRATION_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest backend\tests\test_integration.py -q