# SecGPT - Autonomous AI Security Testing Agent

## What is this?

SecGPT is an AI agent that can do basic security testing on websites automatically. You give it a target URL and a goal (like "find SQL injection vulnerabilities"), and it figures out which tools to run, runs them, reads the results, and decides what to do next. It keeps going until it's done and writes a report.

It uses OpenAI's GPT-4o with function calling to make decisions, and has plugins for tools like nmap, sqlmap, and dirsearch.

Basically it's like AutoGPT but for cybersecurity stuff.

## How to run

**Prerequisites:**
- Python 3.10 or higher
- An OpenAI API key (you need GPT-4o access)
- nmap installed on your system (`apt install nmap` or download from nmap.org)
- sqlmap (`pip install sqlmap`)
- dirsearch (`pip install dirsearch`)

**Setup:**

```
git clone <this repo>
cd SecGPT
pip install -r requirements.txt
```

**Set your API key** (pick one):

```
# Option 1: environment variable
export OPENAI_API_KEY="sk-your-key-here"

# Option 2: config file
mkdir config
echo "openai_key: sk-your-key-here" > config/config.yaml
```

**Run it:**

```
python main.py
```

It will ask you to describe your goal, then it generates a "character" for the agent and starts the autonomous loop.

There's also a Dockerfile if you want to run it in Docker but honestly just running it directly is easier for testing.

## Project structure

```
SecGPT/
├── main.py              # Main file - agent loop, LLM calls, memory, everything
├── requirements.txt     # Dependencies
├── Dockerfile           # Optional containerization
├── plugins/
│   ├── plugin_http.py       # HTTP GET/POST requests
│   ├── plugin_sqlmap.py     # SQL injection testing
│   ├── plugin_nmap.py       # Port scanning
│   ├── plugin_dirsearch.py  # Directory bruteforcing
│   ├── plugin_file.py       # Read/write files
│   └── plugin_exit.py       # Exit the program
└── prompts/
    ├── character.yaml            # Template for character generation
    ├── constraints.yaml          # Agent constraints
    ├── resources.yaml            # Available resources
    └── performance_evaluation.yaml  # Self-evaluation rules
```

## How it works (for the report)

1. On startup, it loads all plugins from the `plugins/` folder
2. The user describes a security testing goal
3. GPT generates a "character" with specific goals (inspired by AutoGPT)
4. The agent enters an autonomous loop:
   - Sends conversation history + available tools to GPT-4o
   - GPT decides which tool to call (via function calling API)
   - The tool runs and returns results
   - Results get added to the conversation
   - If the conversation gets too long (>8000 tokens), old messages get summarized
   - Repeat until the agent calls `exit_program`

## Adding new plugins

Just create a new file in `plugins/` starting with `plugin_` and add a `register()` function that returns a dict with `name`, `description`, `func`, and `args`. Check any existing plugin for the format.

## Known bugs / limitations

- The memory summarization sometimes loses important details from earlier in the conversation
- If sqlmap or nmap hangs, you have to wait the full 120 second timeout
- The file plugin's path sanitization is pretty basic (just strips `..`) - don't use this on a production server
- Sometimes GPT responds with text instead of a tool call and the agent has to re-prompt it
- Token counting is approximate, sometimes we still go over the context limit

## References

- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) - main inspiration for the agent loop design
- [OpenAI Function Calling docs](https://platform.openai.com/docs/guides/function-calling)
- [sqlmap](https://sqlmap.org/)
- [nmap](https://nmap.org/)
