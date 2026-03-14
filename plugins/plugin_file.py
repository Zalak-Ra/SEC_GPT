# File operations plugin
# Read and write files in the workspace folder
# Hack: we restrict to workspace/ so the agent cant mess with system files

import os

WORKSPACE = "workspace"

def file_ops(args):
    operation = args.get("operation", "read")
    filename = args.get("filename", "")
    data = args.get("data", "")

    # basic path safety - just make sure theres no .. in the path
    # TODO: this probably isnt bulletproof but good enough for demo
    filename = filename.replace("..", "").replace("/", os.sep)
    filepath = os.path.join(WORKSPACE, filename)

    os.makedirs(WORKSPACE, exist_ok=True)

    if operation == "read":
        if not os.path.isfile(filepath):
            return f"Error: file not found - {filepath}"
        try:
            with open(filepath, "r") as f:
                content = f.read()
            return f"File contents ({len(content)} chars):\n{content[:4000]}"
        except Exception as e:
            return f"Error reading file: {e}"

    elif operation == "write":
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                f.write(data)
            return f"Wrote {len(data)} chars to {filepath}"
        except Exception as e:
            return f"Error writing file: {e}"
    else:
        return f"Error: unknown operation '{operation}', use 'read' or 'write'"

def register():
    return {
        "name": "file_ops",
        "description": "Read or write files in the workspace directory. Use operation='read' or operation='write'.",
        "func": file_ops,
        "args": [
            {"name": "operation", "description": "'read' or 'write'"},
            {"name": "filename", "description": "Filename relative to workspace (e.g. report.txt)"},
            {"name": "data", "description": "Data to write (only for write operation)", "optional": True},
        ],
    }
