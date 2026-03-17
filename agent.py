#!/usr/bin/env python3
"""
System Agent with tools: read_file, list_files, and query_api.
"""

import json
import os
import sys
import requests
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urljoin

# Load environment variables
load_dotenv('.env.agent.secret')
load_dotenv('.env.docker.secret')  # For LMS_API_KEY

# Конфигурация
MAX_TOOL_CALLS = 10
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# API конфигурация
LMS_API_KEY = os.getenv('LMS_API_KEY')
AGENT_API_BASE_URL = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')

if not LMS_API_KEY:
    print("Warning: LMS_API_KEY not set in .env.docker.secret", file=sys.stderr)

# ============================================
# TASK 2: File Operations Tools
# ============================================

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

# ============================================
# TASK 3: API Query Tool
# ============================================

def query_api(method, path, body=None, include_auth=True):
    """
    Send a request to the backend API.
    If include_auth=False, don't include the authentication header.
    """
    try:
        # Construct full URL
        url = urljoin(AGENT_API_BASE_URL, path)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json"
        }
        
        # Only add auth header if requested
        if include_auth and LMS_API_KEY:
            headers["Authorization"] = f"Bearer {LMS_API_KEY}"
        
        # Prepare request
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            json_body = json.loads(body) if body else None
            response = requests.post(url, headers=headers, json=json_body, timeout=10)
        elif method.upper() == "PUT":
            json_body = json.loads(body) if body else None
            response = requests.put(url, headers=headers, json=json_body, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return json.dumps({"error": f"Unsupported method: {method}"})
        
        # Return result
        try:
            response_body = response.json()
        except:
            response_body = response.text
        
        return json.dumps({
            "status_code": response.status_code,
            "body": response_body,
            "auth_used": include_auth
        })
        
    except requests.exceptions.ConnectionError:
        return json.dumps({
            "status_code": 0,
            "body": f"Error: Cannot connect to API at {AGENT_API_BASE_URL}"
        })
    except Exception as e:
        return json.dumps({
            "status_code": 0,
            "body": f"Error: {str(e)}"
        })

# ============================================
# Tool Definitions for LLM
# ============================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read wiki documentation or source code files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file from project root (e.g., 'wiki/git-workflow.md' or 'backend/main.py')"
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
            "description": "List files and directories at a given path. Use this to explore what files are available in wiki or source code directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki' or 'backend')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Send a request to the deployed backend API. Use this to get real-time data from the running system. For questions about authentication, you can make requests with and without the auth header to compare.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "description": "HTTP method for the request"
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path (e.g., '/items/' or '/analytics/completion-rate?lab=lab-99')"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT requests"
                    },
                    "include_auth": {
                        "type": "boolean",
                        "description": "Whether to include the authentication header. Set to False to test unauthenticated access.",
                        "default": True
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

# ============================================
# System Prompt
# ============================================

SYSTEM_PROMPT = """You are a system assistant for a software project. You can answer questions using:
1. Wiki documentation - for how-to guides and explanations
2. Source code files - for implementation details
3. Live API - for real-time system data

AVAILABLE TOOLS:
1. list_files(path) - Explore directories (use with 'wiki' or 'backend')
2. read_file(path) - Read file contents (wiki docs or source code)
3. query_api(method, path, body, include_auth) - Query the live backend API

HOW TO CHOOSE THE RIGHT TOOL:
- For wiki questions (branch protection, SSH setup): use list_files('wiki') → read_file('wiki/*.md')
- For code questions (framework, routers): use list_files('backend') → read_file('backend/*.py')
- For API questions (item count, status codes): use query_api()
- For error diagnosis: query_api() first to see error, then read_file() to find bug

WHEN USING QUERY_API:
- For normal data queries, use include_auth=True (default)
- To test authentication, use include_auth=False to see what happens without a token
- Always check the status_code in the response
- The API base URL is already configured - just provide the path

CRITICAL RULES FOR YOUR RESPONSES:

1. SOURCE FIELD REQUIREMENTS (MANDATORY):
   - When answering from wiki: source MUST be "wiki/filename.md" (e.g., "wiki/git-workflow.md")
   - When answering from code: source MUST be "backend/filename.py" (e.g., "backend/main.py")
   - When answering from API only: source can be empty string ""

2. ANSWER FORMAT:
   - Be concise and direct
   - Include the actual information from the source
   - For API questions: include the status code and what it means

3. FOR AUTHENTICATION QUESTIONS:
   - Make two API calls: one with auth, one without
   - Compare the status codes
   - Report what happens in each case

EXAMPLES:
- Wiki question: "Steps to protect a branch? Source: wiki/git-workflow.md"
- Code question: "The project uses FastAPI. Source: backend/main.py"
- API question: "There are 42 items in the database. Status: 200 OK. Source: "
- Auth question: "Without auth: 401 Unauthorized, With auth: 200 OK. Source: "

Remember: Always use the tools to get real data, don't guess!"""

# ============================================
# Tool Execution
# ============================================

def execute_tool(tool_call):
    """Execute a tool and return the result."""
    tool_name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])
    
    print(f"Executing tool: {tool_name} with args: {args}", file=sys.stderr)
    
    if tool_name == "read_file":
        result = read_file(args["path"])
    elif tool_name == "list_files":
        result = list_files(args["path"])
    elif tool_name == "query_api":
        result = query_api(
            method=args["method"],
            path=args["path"],
            body=args.get("body"),
            include_auth=args.get("include_auth", True)
        )
    else:
        result = f"Error: Unknown tool {tool_name}"
    
    return {
        "tool": tool_name,
        "args": args,
        "result": result
    }

# ============================================
# LLM Interaction
# ============================================

def call_llm(messages):
    """Make a call to the LLM API."""
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')
    
    if not all([api_key, api_base, model]):
        print("Error: Missing LLM configuration", file=sys.stderr)
        return None
    
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
    
    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=55
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error calling LLM: {str(e)}", file=sys.stderr)
        return None

# ============================================
# Agentic Loop
# ============================================

def agentic_loop(question):
    """Main agentic loop with tool execution."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_calls_history = []
    tool_calls_count = 0
    last_wiki_file = None
    last_code_file = None
    
    print(f"Starting agentic loop for question: {question}", file=sys.stderr)
    
    while tool_calls_count < MAX_TOOL_CALLS:
        print(f"\n--- Iteration {tool_calls_count + 1} ---", file=sys.stderr)
        
        # Call LLM
        response = call_llm(messages)
        if not response:
            return {
                "answer": "Error: Failed to get response from LLM",
                "source": "",
                "tool_calls": tool_calls_history
            }
        
        message = response["choices"][0]["message"]
        
        # Track which files were read
        if "tool_calls" in message and message["tool_calls"]:
            for tool_call in message["tool_calls"]:
                if tool_call["function"]["name"] == "read_file":
                    args = json.loads(tool_call["function"]["arguments"])
                    path = args["path"]
                    if path.startswith("wiki/"):
                        last_wiki_file = path
                        print(f"  Tracked wiki file: {last_wiki_file}", file=sys.stderr)
                    elif path.startswith("backend/") or path.endswith(".py"):
                        last_code_file = path
                        print(f"  Tracked code file: {last_code_file}", file=sys.stderr)
        
        # Check if there are tool calls
        if "tool_calls" not in message or not message["tool_calls"]:
            print("No tool calls - this is the final answer", file=sys.stderr)
            final_answer = message.get("content") or ""
            
            # Determine source based on question type and tools used
            source = ""
            
            # Rule 1: If we read a wiki file, source should be that file
            if last_wiki_file:
                source = last_wiki_file
                print(f"  Source from wiki file: {source}", file=sys.stderr)
            
            # Rule 2: If we read code files but no wiki, source is code file
            elif last_code_file:
                source = last_code_file
                print(f"  Source from code file: {source}", file=sys.stderr)
            
            # Rule 3: If answer contains wiki reference, extract it
            elif "wiki/" in final_answer:
                lines = final_answer.split('\n')
                for line in lines:
                    if "wiki/" in line and ".md" in line:
                        # Extract just the filename, not the whole line
                        import re
                        match = re.search(r'(wiki/[\w/-]+\.md)', line)
                        if match:
                            source = match.group(1)
                            break
            
            # Rule 4: For API-only questions, source can be empty
            # (already empty by default)
            
            print(f"  Final source: '{source}'", file=sys.stderr)
            
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
            
            print(f"Tool result: {str(tool_result['result'])[:100]}...", file=sys.stderr)
            
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
    
    # Max tool calls reached
    print(f"Max tool calls ({MAX_TOOL_CALLS}) reached", file=sys.stderr)
    return {
        "answer": "I exceeded the maximum number of tool calls without finding a complete answer.",
        "source": last_wiki_file or last_code_file or "",
        "tool_calls": tool_calls_history
    }

# ============================================
# Main
# ============================================

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
