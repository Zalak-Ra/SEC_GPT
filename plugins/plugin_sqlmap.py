# Sqlmap plugin
# Runs sqlmap against a URL to test for SQL injection
# NOTE: sqlmap must be installed on the system (pip install sqlmap)

import subprocess

TIMEOUT = 120  # seconds

def sqlmap_test(args):
    url = args.get("url", "")
    params = args.get("params", "")

    if not params:
        return "Error: params is required (e.g. id=1)"

    full_url = f"{url}?{params}"
    cmd = f'sqlmap -u "{full_url}" --batch'

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT)
        output = result.stdout[-3000:]  # truncate if too long
        if result.returncode == 0:
            return f"sqlmap SUCCESS:\n{output}"
        else:
            return f"sqlmap FAILED:\n{result.stderr[-2000:]}"
    except subprocess.TimeoutExpired:
        return f"Error: sqlmap timed out after {TIMEOUT}s"
    except Exception as e:
        return f"Error: {e}"

def register():
    return {
        "name": "sqlmap_test",
        "description": "Run sqlmap against a URL with parameters to test for SQL injection. params must be like 'id=1'.",
        "func": sqlmap_test,
        "args": [
            {"name": "url", "description": "Base URL to test"},
            {"name": "params", "description": "Query parameters like id=1&name=test"},
        ],
    }
