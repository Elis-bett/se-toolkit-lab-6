#!/usr/bin/env python3
"""
Documentation Agent with tools: read_file and list_files.
"""

import json
import os
import sys
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv('.env.agent.secret')

# Конфигурация
MAX_TOOL_CALLS = 10
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Определение инструментов
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this AFTER you know which file contains the answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file from project root (e.g., 'wiki/git-workflow.md')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this FIRST to explore what files are available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# Улучшенный системный промпт
SYSTEM_PROMPT = """You are a documentation assistant for a software project. Your task is to answer questions using the wiki documentation.

AVAILABLE TOOLS:
1. list_files(path) - Use this FIRST to see what files exist in a directory. Start with path='wiki'.
2. read_file(path) - Use this AFTER you know which file contains the answer. Read the file to find the specific information.

IMPORTANT: Always follow this process:
1. First, call list_files with path='wiki' to see what documentation files are available
2. Based on the question, identify which file might contain the answer
3. Call read_file with the specific file path (e.g., 'wiki/git-workflow.md')
4. Extract the answer from the file content
5. Provide the answer with source in format: wiki/filename.md#section-name

EXAMPLES:
- If asked about git workflows, you should: list_files('wiki') → then read_file('wiki/git-workflow.md')
- If asked about Python style, you should: list_files('wiki') → then read_file('wiki/python-style.md')

Remember: You MUST call read_file after list_files to get the actual content. The list_files only shows filenames, not the content."""

def read_file(path):
    """Read a file from the project directory."""
    try:
        # Security: prevent directory traversal
        full_path = os.path.normpath(os.path.join(PROJECT_ROOT, path))
        if not full_path.startswith(PROJECT_ROOT):
            return "Error: Access denied - cannot read files outside project directory"
        
        if not os.path.exists(full_path):
            return f"Error: File {path} does not exist"
        
        if not os.path.isfile(full_path):
            return f"Error: {path} is not a file"
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(path):
    """List files in a directory."""
    try:
        # Security: prevent directory traversal
        full_path = os.path.normpath(os.path.join(PROJECT_ROOT, path))
        if not full_path.startswith(PROJECT_ROOT):
            return "Error: Access denied - cannot list directories outside project root"
        
        if not os.path.exists(full_path):
            return f"Error: Directory {path} does not exist"
        
        if not os.path.isdir(full_path):
            return f"Error: {path} is not a directory"
        
        items = os.listdir(full_path)
        # Filter out hidden files and directories if needed
        items = [i for i in items if not i.startswith('.')]
        return "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def execute_tool(tool_call):
    """Execute a tool and return the result."""
    tool_name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])
    
    print(f"Executing tool: {tool_name} with args: {args}", file=sys.stderr)
    
    if tool_name == "read_file":
        result = read_file(args["path"])
    elif tool_name == "list_files":
        result = list_files(args["path"])
    else:
        result = f"Error: Unknown tool {tool_name}"
    
    return {
        "tool": tool_name,
        "args": args,
        "result": result
    }

def call_llm(messages):
    """Make a call to the LLM API."""
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto"
    }
    
    print(f"Calling LLM with {len(messages)} messages", file=sys.stderr)
    
    response = requests.post(
        f"{api_base}/chat/completions",
        headers=headers,
        json=payload,
        timeout=55
    )
    response.raise_for_status()
    return response.json()

def agentic_loop(question):
    """Main agentic loop with tool execution."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_calls_history = []
    tool_calls_count = 0
    
    print(f"Starting agentic loop for question: {question}", file=sys.stderr)
    
    while tool_calls_count < MAX_TOOL_CALLS:
        print(f"\n--- Iteration {tool_calls_count + 1} ---", file=sys.stderr)
        
        # Call LLM
        response = call_llm(messages)
        message = response["choices"][0]["message"]
        
        # Check if there are tool calls
        if "tool_calls" not in message or not message["tool_calls"]:
            print("No tool calls - this is the final answer", file=sys.stderr)
            # No tool calls - this is the final answer
            final_answer = message.get("content", "")
            
            # Try to extract source from answer
            source = ""
            lines = final_answer.split('\n')
            for line in lines:
                if "wiki/" in line and ".md" in line:
                    source = line.strip()
                    break
            
            return {
                "answer": final_answer,
                "source": source,
                "tool_calls": tool_calls_history
            }
        
        # Execute each tool call
        print(f"Tool calls requested: {len(message['tool_calls'])}", file=sys.stderr)
        for tool_call in message["tool_calls"]:
            tool_result = execute_tool(tool_call)
            tool_calls_history.append(tool_result)
            
            print(f"Tool result: {tool_result['result'][:100]}...", file=sys.stderr)
            
            # Add tool result to messages
            messages.append({
                "role": "assistant",
                "tool_calls": [tool_call]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps({"result": tool_result["result"]})
            })
            
            tool_calls_count += 1
            
            # After reading a file, check if we have the answer
            if tool_result["tool"] == "read_file":
                print("File read complete - checking if answer found", file=sys.stderr)
                # We could add logic here to determine if answer is sufficient
    
    # Max tool calls reached
    print(f"Max tool calls ({MAX_TOOL_CALLS}) reached", file=sys.stderr)
    return {
        "answer": "I exceeded the maximum number of tool calls without finding a complete answer.",
        "source": "",
        "tool_calls": tool_calls_history
    }

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "answer": "Error: Question argument required",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)
    
    question = sys.argv[1]
    
    try:
        result = agentic_loop(question)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(f"Error in main: {str(e)}", file=sys.stderr)
        print(json.dumps({
            "answer": f"Error: {str(e)}",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
