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
import traceback
import re

# Load environment variables
load_dotenv('.env.agent.secret')
load_dotenv('.env.docker.secret')  # For LMS_API_KEY

# Конфигурация
MAX_TOOL_CALLS = 15  # Увеличим для сложных вопросов
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# API конфигурация
LMS_API_KEY = os.getenv('LMS_API_KEY')
AGENT_API_BASE_URL = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')

# LLM конфигурация
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_BASE = os.getenv('LLM_API_BASE')
LLM_MODEL = os.getenv('LLM_MODEL')

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
            content = f.read()
            return content
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
        
        # Only add auth header if requested AND key exists
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

CRITICAL RULES FOR ERROR DIAGNOSIS QUESTIONS:

1. FIRST: Query the API to see the error
   - Use query_api with different parameters (lab=lab-1, lab-99, etc.)
   - Look at the exact error message and status code
   - If it's a 500 error, the response body will contain the error trace

2. THEN: Read the source code to find the bug
   - Read the relevant router file (e.g., backend/routers/analytics.py)
   - Look for the specific line that causes the error
   - Identify why it crashes (e.g., sorting None values, division by zero)

3. FORMAT YOUR ANSWER:
   - First line: What error occurs (exact error message)
   - Second line: Why it happens (the bug in the code)
   - Example: "Error: TypeError: '<' not supported between instances of 'NoneType' and 'int'"
   - "Bug: When avg_score is NULL in the database, the sort function fails because it can't compare None with integers."

4. FOR THE TOP-LEARNERS BUG:
   - Query /analytics/top-learners?lab=lab-99 to see the error
   - Read backend/routers/analytics.py to find the sorting code
   - Look for a line like: sorted(learners, key=lambda x: x['avg_score'], reverse=True)
   - The bug is that when avg_score is None, Python can't compare None with integers during sorting

CRITICAL RULES FOR YOUR RESPONSES:

1. SOURCE FIELD REQUIREMENTS (MANDATORY):
   - When answering from wiki: source MUST be "wiki/filename.md" (e.g., "wiki/git-workflow.md")
   - When answering from code: source MUST be "backend/filename.py" (e.g., "backend/main.py")
   - When answering from API only: source can be empty string ""

2. ANSWER FORMAT:
   - Be concise and direct
   - Include the actual information from the source
   - For API questions: include the status code and what it means
   - For error diagnosis: include the exact error and the bug location

Remember: Always use the tools to get real data, don't guess!"""

# ============================================
# Tool Execution
# ============================================

def execute_tool(tool_call):
    """Execute a tool and return the result."""
    tool_name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])
    
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
    api_key = LLM_API_KEY
    api_base = LLM_API_BASE
    model = LLM_MODEL
    
    if not all([api_key, api_base, model]):
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
    
    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=55
        )
        response.raise_for_status()
        return response.json()
    except Exception:
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
    
    while tool_calls_count < MAX_TOOL_CALLS:
        
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
                    elif path.startswith("backend/") or path.endswith(".py"):
                        last_code_file = path
        
        # Check if there are tool calls
        if "tool_calls" not in message or not message["tool_calls"]:
            final_answer = message.get("content") or ""
            
            # Determine source based on question type and tools used
            source = ""
            
            # Rule 1: If we read a wiki file, source should be that file
            if last_wiki_file:
                source = last_wiki_file
            
            # Rule 2: If we read code files but no wiki, source is code file
            elif last_code_file:
                source = last_code_file
            
            # Rule 3: If answer contains wiki reference, extract it
            elif "wiki/" in final_answer:
                lines = final_answer.split('\n')
                for line in lines:
                    if "wiki/" in line and ".md" in line:
                        match = re.search(r'(wiki/[\w/-]+\.md)', line)
                        if match:
                            source = match.group(1)
                            break
            
            return {
                "answer": final_answer,
                "source": source,
                "tool_calls": tool_calls_history
            }
        
        # Execute each tool call
        for tool_call in message["tool_calls"]:
            tool_result = execute_tool(tool_call)
            tool_calls_history.append(tool_result)
            
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
        print(json.dumps({
            "answer": f"Error: {str(e)}",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
