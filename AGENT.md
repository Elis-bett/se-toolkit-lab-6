# Documentation Agent

## Architecture Overview
Agent with tool-calling capabilities that can navigate and read project documentation.

## Tools
1. **read_file(path)** - Reads a file from the project directory
   - Security: Prevents directory traversal attacks
   - Returns: File contents or error message

2. **list_files(path)** - Lists files in a directory
   - Security: Prevents directory traversal attacks
   - Returns: Newline-separated list of files

## Agentic Loop
1. Send question + tool definitions to LLM
2. If LLM requests tools → execute them, append results, repeat
3. If LLM gives text answer → that's final, output JSON
4. Maximum 10 tool calls per question

## System Prompt Strategy
The agent is instructed to:
- Use list_files first to explore the wiki
- Use read_file to read relevant files
- Provide source references in format wiki/file.md#section

## Output Format
```json
{
  "answer": "The answer to the question",
  "source": "wiki/filename.md#section",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/file.md"}, "result": "..."}
  ]
}
