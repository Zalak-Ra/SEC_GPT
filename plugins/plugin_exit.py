# Exit plugin
# just exits the program when the agent is done

import sys

def exit_program(args):
    reason = args.get("reason", "Task complete")
    print(f"\nAgent is done: {reason}")
    sys.exit(0)

def register():
    return {
        "name": "exit_program",
        "description": "Exit the program after all tasks are complete.",
        "func": exit_program,
        "args": [
            {"name": "reason", "description": "Why the agent is exiting", "optional": True},
        ],
    }
