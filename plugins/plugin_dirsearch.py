# Dirsearch plugin
# Brute forces directories on a web server

import subprocess

TIMEOUT = 120

def dirsearch_scan(args):
    url = args.get("url", "")
    extensions = args.get("extensions", "php,asp,aspx,jsp,html")

    cmd = f"dirsearch -u {url} -e {extensions}"

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT)
        output = result.stdout[-3000:]
        if result.returncode == 0:
            return f"dirsearch SUCCESS:\n{output}"
        else:
            return f"dirsearch FAILED:\n{result.stderr[-2000:]}"
    except subprocess.TimeoutExpired:
        return f"Error: dirsearch timed out after {TIMEOUT}s"
    except Exception as e:
        return f"Error: {e}"

def register():
    return {
        "name": "dirsearch_scan",
        "description": "Run dirsearch against a URL to find hidden directories and files.",
        "func": dirsearch_scan,
        "args": [
            {"name": "url", "description": "Target URL to scan"},
            {"name": "extensions", "description": "File extensions to look for (default: php,asp,aspx,jsp,html)", "optional": True},
        ],
    }
