# Nmap plugin
# Does a basic network scan on a target
# TODO: add support for custom nmap flags

import subprocess

TIMEOUT = 120

def nmap_scan(args):
    target = args.get("target", "")
    if not target:
        return "Error: target is required"

    # just a basic scan for now
    cmd = f"nmap {target}"

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT)
        output = result.stdout[-3000:]
        if result.returncode == 0:
            return f"nmap SUCCESS:\n{output}"
        else:
            return f"nmap FAILED:\n{result.stderr[-2000:]}"
    except subprocess.TimeoutExpired:
        return f"Error: nmap timed out after {TIMEOUT}s"
    except Exception as e:
        return f"Error: {e}"

def register():
    return {
        "name": "nmap_scan",
        "description": "Run nmap on a target IP or hostname to find open ports and services.",
        "func": nmap_scan,
        "args": [
            {"name": "target", "description": "IP address or hostname to scan"},
        ],
    }
