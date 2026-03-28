"""
SecGPT - Autonomous AI Security Testing Agent
CS450 Final Year Project

Main file that handles everything - the AI agent loop, plugin loading,
memory management, etc. I know this file is kind of long but it works lol

Authors: [Your Name]
Date: 2026
"""

import os
import sys
import json
import time
import importlib
import subprocess
import yaml
import tiktoken
from openai import OpenAI

API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = os.getenv("MODEL", "gpt-4o")
MAX_TOKENS = 4096
COMMAND_TIMEOUT = 120  # seconds before we kill a subprocess
TOKEN_LIMIT = 8000  # when to summarize old messages
WORKSPACE = "workspace"  # where the agent reads/writes files

# load from yaml config if env var not set
if not API_KEY:
    try:
        with open("config/config.yaml", "r") as f:
            cfg = yaml.safe_load(f)
            API_KEY = cfg.get("openai_key", "") or cfg.get("openai_api_key", "")
    except:
        pass

if not API_KEY:
    print("[ERROR] No API key found! Set OPENAI_API_KEY env variable or put it in config/config.yaml")
    sys.exit(1)

# make dirs if they dont exist
os.makedirs("logs", exist_ok=True)
os.makedirs("workspace", exist_ok=True)
os.makedirs("config", exist_ok=True)

client = OpenAI(api_key=API_KEY)

# try to get the right tokenizer, fall back to default
try:
    enc = tiktoken.encoding_for_model(MODEL)
except:
    enc = tiktoken.get_encoding("cl100k_base")

# scans the plugins folder for any file starting with "plugin_"
# each plugin just needs a register() function that returns a dict

plugins = {}

def load_plugins():
    global plugins
    plugin_dir = "plugins"
    if not os.path.isdir(plugin_dir):
        print("[WARN] No plugins directory found")
        return

    for fname in sorted(os.listdir(plugin_dir)):
        if not fname.startswith("plugin_") or not fname.endswith(".py"):
            continue
        modname = fname[:-3]
        try:
            mod = importlib.import_module(f"plugins.{modname}")
            if hasattr(mod, "register"):
                info = mod.register()
                plugins[info["name"]] = info
                print(f"[INFO] Loaded plugin: {info['name']}")
        except Exception as e:
            print(f"[ERROR] Failed to load {modname}: {e}")

    print(f"[INFO] Total plugins: {len(plugins)}")


def get_openai_tools():
    """Convert our plugin definitions to OpenAI function calling format"""
    tools = []
    for name, p in plugins.items():
        # build the parameters schema from the plugin's args list
        properties = {}
        required = []
        for arg in p.get("args", []):
            properties[arg["name"]] = {
                "type": "string",
                "description": arg.get("description", ""),
            }
            if not arg.get("optional", False):
                required.append(arg["name"])

        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": p["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return tools


def run_plugin(name, args):
    """Call a plugin function by name"""
    if name not in plugins:
        return f"Error: unknown plugin '{name}'"
    try:
        result = plugins[name]["func"](args)
        return result
    except SystemExit:
        raise  # let exit propagate
    except Exception as e:
        return f"Error running {name}: {e}"

# when it gets too long (otherwise we blow the context window)

system_prompt = ""
messages = []


def count_tokens(text):
    if not text:
        return 0
    return len(enc.encode(text))


def total_tokens():
    total = count_tokens(system_prompt)
    for msg in messages:
        total += count_tokens(msg.get("content") or "")
        # also count tool call args
        for tc in msg.get("tool_calls", []):
            total += count_tokens(tc.get("function", {}).get("arguments", ""))
    return total


def summarize_if_needed():
    """If we're over the token limit, ask GPT to summarize the old stuff"""
    tokens = total_tokens()
    if tokens <= TOKEN_LIMIT:
        return

    print(f"[INFO] Token count ({tokens}) over limit ({TOKEN_LIMIT}), summarizing...")

    # keep the last 6 messages, summarize everything before that
    keep = min(6, len(messages))
    old = messages[:len(messages) - keep]
    recent = messages[len(messages) - keep:]

    if not old:
        return

    # dump old messages into text for the summarizer
    dump = ""
    for msg in old:
        role = msg.get("role", "?")
        content = msg.get("content") or ""
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            content += f"\n[tool: {fn.get('name')} args={fn.get('arguments')}]"
        dump += f"[{role}] {content}\n"

    # ask GPT to summarize
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Summarize this conversation history into brief bullet points. Keep all important findings."},
                {"role": "user", "content": dump},
            ],
            max_tokens=1024,
        )
        summary = resp.choices[0].message.content or ""
    except Exception as e:
        print(f"[ERROR] Summarization failed: {e}")
        return

    # replace old messages with summary
    messages.clear()
    messages.append({"role": "user", "content": f"[Previous context summary]\n{summary}"})
    messages.extend(recent)
    print(f"[INFO] Compressed {len(old)} old messages into 1 summary")


# the agent generates a "character" for itself based on the user's goal

def load_character_template():
    with open("prompts/character.yaml", "r") as f:
        return yaml.safe_load(f)


def create_character():
    """Ask GPT to generate a character based on user's goal"""
    templates = load_character_template()

    goal = input("\nWhat do you want the agent to do?\n> ").strip()
    if not goal:
        print("No goal provided, exiting")
        sys.exit(1)

    # build list of available tools for the character prompt
    tools_text = "\n".join(f"- {p['name']}: {p['description']}" for p in plugins.values())
    sys_msg = templates["system"].replace("{{Commands}}", tools_text)
    usr_msg = templates["user"].replace("{{user_prompt}}", goal)

    print("Generating agent character...")
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": usr_msg},
            ],
            max_tokens=MAX_TOKENS,
        )
        text = resp.choices[0].message.content or ""
    except Exception as e:
        print(f"[ERROR] Character generation failed: {e}")
        sys.exit(1)

    # parse name/description/goals from the response
    import re
    name_m = re.search(r"Name\s*:\s*(.*)", text, re.IGNORECASE)
    desc_m = re.search(r"Description\s*:\s*(.*?)(?:\n|Goals)", text, re.IGNORECASE | re.DOTALL)
    goals = re.findall(r"(?<=\n)-\s*(.*)", text)

    char_info = {
        "name": name_m.group(1).strip() if name_m else "SecurityGPT",
        "description": desc_m.group(1).strip() if desc_m else "A security testing agent",
        "goals": goals or [],
        "user_goal": goal,
    }

    # save for next time so user doesnt have to redo this
    os.makedirs("config", exist_ok=True)
    with open("config/character.yaml", "w") as f:
        yaml.dump(char_info, f)

    print(f"\nCharacter: {char_info['name']}")
    print(f"  {char_info['description']}")
    for g in char_info["goals"]:
        print(f"  - {g}")

    return char_info


def load_saved_character():
    """Try to load a previously created character"""
    try:
        with open("config/character.yaml", "r") as f:
            data = yaml.safe_load(f)
        if data and data.get("name"):
            return data
    except:
        pass
    return None


def build_system_prompt(char_info):
    """Assemble the system prompt from character info + yaml files"""
    parts = []
    parts.append(f"You are {char_info['name']}, {char_info['description']}")
    parts.append("Your decisions must always be made independently without seeking user assistance.\n")

    # add goals
    goals_str = "\n".join(f"- {g}" for g in char_info.get("goals", []))
    parts.append(f"Goals:\n{goals_str}\n")

    # load the yaml prompt sections
    section_files = {
        "Constraints": "constraints",
        "Resources": "resources",
        "Performance Evaluation": "performance_evaluation",
    }
    for section_name, filename in section_files.items():
        try:
            with open(f"prompts/{filename}.yaml", "r") as f:
                data = yaml.safe_load(f)
            if isinstance(data, list):
                items = "\n".join(str(x) for x in data)
                parts.append(f"{section_name}:\n{items}\n")
        except:
            pass  # not a big deal if a prompt file is missing

    prompt = "\n".join(parts)
    prompt += "\nAlways respond by calling exactly one tool. Never respond with plain text.\n"
    return prompt

USER_PROMPT = (
    "Determine the single best next action to take toward completing your goals. "
    "Call exactly one tool. Do NOT respond with plain text."
)


def agent_loop():
    """The main autonomous loop - call LLM, execute tool, feed back result, repeat"""
    global messages

    tools = get_openai_tools()
    iteration = 0

    while True:
        iteration += 1
        print(f"\n{'='*50}")
        print(f"[INFO] Iteration {iteration}")
        print(f"{'='*50}")

        # build full message list with system prompt
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        # call gpt
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=full_messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=MAX_TOKENS,
            )
        except Exception as e:
            print(f"[ERROR] API call failed: {e}")
            time.sleep(5)  # wait a bit and retry
            continue

        choice = response.choices[0]
        msg = choice.message

        # if the model just sent text instead of a tool call
        if not msg.tool_calls:
            text = msg.content or "(no response)"
            print(f"[INFO] LLM said: {text[:200]}")
            messages.append({"role": "assistant", "content": text})
            # remind it to use tools
            messages.append({"role": "user", "content": USER_PROMPT})
            continue

        # process the tool call
        tc = msg.tool_calls[0]  # just handle one at a time
        func_name = tc.function.name
        try:
            func_args = json.loads(tc.function.arguments)
        except:
            func_args = {}

        print(f"[INFO] Tool call: {func_name}({func_args})")

        # record the assistant's tool call in history
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": func_name,
                    "arguments": json.dumps(func_args),
                },
            }],
        })

        # actually run the plugin
        try:
            result = run_plugin(func_name, func_args)
            print(f"[INFO] Result: {result[:300]}")
        except SystemExit:
            print("\nAgent finished. Goodbye!")
            return

        # add result to history
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "name": func_name,
            "content": result,
        })

        # check if we need to summarize
        summarize_if_needed()

def main():
    global system_prompt, messages

    print("  SecGPT - AI Security Testing Agent")

    # load plugins
    load_plugins()
    if not plugins:
        print("[ERROR] No plugins found! Check the plugins/ directory.")
        sys.exit(1)

    # character setup
    existing = load_saved_character()
    if existing:
        print(f"\nFound saved character: {existing['name']}")
        choice = input("Use this character? (Y/n): ").strip().lower()
        if choice != "n":
            char_info = existing
        else:
            char_info = create_character()
    else:
        char_info = create_character()

    # build system prompt
    system_prompt = build_system_prompt(char_info)

    # seed the conversation
    messages = [{"role": "user", "content": USER_PROMPT}]

    print("\nStarting agent loop... (Ctrl+C to stop)\n")
    try:
        agent_loop()
    except KeyboardInterrupt:
        print("\n\nStopped by user.")


if __name__ == "__main__":
    main()
