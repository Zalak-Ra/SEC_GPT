# HTTP request plugin
# makes GET or POST requests to URLs

import requests

def http_request(args):
    url = args.get("url", "")
    method = args.get("http_method", "GET").upper()

    try:
        if method == "GET":
            resp = requests.get(url, timeout=30)
        elif method == "POST":
            resp = requests.post(url, data=args.get("params"), timeout=30)
        else:
            return f"Error: unsupported method {method}"

        # dont return the whole page, it might be huge
        body = resp.text[:4000]
        return f"HTTP {method} {url} -> {resp.status_code}\n{body}"
    except Exception as e:
        return f"Error: {e}"

def register():
    return {
        "name": "http_request",
        "description": "Make an HTTP GET or POST request to a URL and return the response.",
        "func": http_request,
        "args": [
            {"name": "http_method", "description": "HTTP method: GET or POST"},
            {"name": "url", "description": "The URL to request"},
            {"name": "params", "description": "Optional query params or POST body", "optional": True},
        ],
    }
