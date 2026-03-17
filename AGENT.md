# System Agent Documentation

## Overview
This agent is a CLI tool that answers questions about a software project by combining three capabilities:
1. Reading wiki documentation
2. Reading source code files
3. Querying the live backend API

The agent uses an **agentic loop** with tool-calling to dynamically decide which tools to use based on the question.

## Architecture

### Agentic Loop
1. Send user question + tool definitions to LLM
2. If LLM requests tools → execute them, append results, repeat
3. If LLM gives text answer → that's final, output JSON
4. Maximum 10 tool calls per question (prevents infinite loops)

### Tools

#### 1. `list_files(path)`
- **Purpose**: Explore what files are available in a directory
- **Parameters**: `path` - relative directory path (e.g., 'wiki', 'backend')
- **Returns**: Newline-separated list of files
- **Security**: Prevents directory traversal (blocks `..`)

#### 2. `read_file(path)`
- **Purpose**: Read contents of wiki documentation or source code files
- **Parameters**: `path` - relative file path (e.g., 'wiki/git-workflow.md')
- **Returns**: File contents or error message
- **Security**: Prevents directory traversal, only reads within project

#### 3. `query_api(method, path, body, include_auth)`
- **Purpose**: Query the live backend API for real-time data
- **Parameters**:
  - `method`: HTTP method (GET, POST, PUT, DELETE)
  - `path`: API endpoint (e.g., '/items/', '/analytics/completion-rate?lab=lab-99')
  - `body`: Optional JSON body for POST/PUT
  - `include_auth`: Whether to include auth header (default: True)
- **Returns**: JSON with `status_code`, `body`, and `auth_used`
- **Authentication**: Uses `LMS_API_KEY` from environment when `include_auth=True`

## How the Agent Chooses Tools

| Question Type | Example | Tool Strategy |
|--------------|---------|---------------|
| Wiki documentation | "How to protect a branch?" | `list_files('wiki')` → `read_file('wiki/git-workflow.md')` |
| Source code | "What framework does the backend use?" | `list_files('backend')` → `read_file('backend/main.py')` |
| API data | "How many items are in the database?" | `query_api('GET', '/items/')` |
| Authentication | "What status code without auth?" | `query_api('GET', '/items/', include_auth=False)` |
| Error diagnosis | "Why does completion-rate crash?" | `query_api(...)` → `read_file('backend/analytics.py')` |

## Output Format

```json
{
  "answer": "The answer to the question",
  "source": "wiki/git-workflow.md",  // Empty string for API-only questions
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\npython-style.md"
    },
    {
      "tool": "read_file", 
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git Workflow\n\n## Resolving merge conflicts..."
    }
  ]
}
