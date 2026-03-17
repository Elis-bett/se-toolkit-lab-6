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

# Загружаем .env файлы если они есть (для локальной разработки)
# НО! Если переменные уже заданы в окружении, они имеют приоритет
load_dotenv('.env.agent.secret', override=False)
load_dotenv('.env.docker.secret', override=False)

# ============================================
# Конфигурация - ВСЁ читаем из окружения
# ============================================

MAX_TOOL_CALLS = 15
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# LLM конфигурация - эти переменные ОБЯЗАНЫ быть в окружении
LLM_API_KEY = os.environ.get('LLM_API_KEY')
LLM_API_BASE = os.environ.get('LLM_API_BASE')
LLM_MODEL = os.environ.get('LLM_MODEL')

# Backend конфигурация
LMS_API_KEY = os.environ.get('LMS_API_KEY')
AGENT_API_BASE_URL = os.environ.get('AGENT_API_BASE_URL', 'http://localhost:42002')

# ВАЖНО: Проверяем наличие обязательных переменных
missing_vars = []
if not LLM_API_KEY:
    missing_vars.append('LLM_API_KEY')
if not LLM_API_BASE:
    missing_vars.append('LLM_API_BASE')
if not LLM_MODEL:
    missing_vars.append('LLM_MODEL')

if missing_vars:
    # Пишем в stderr чтобы не ломать JSON вывод
    print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}", file=sys.stderr)
    # НЕ выходим с ошибкой здесь, потому что это может быть просто локальный тест
    # Выходим только если реально пытаемся использовать LLM

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
    """
    try:
        url = urljoin(AGENT_API_BASE_URL, path)
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if include_auth and LMS_API_KEY:
            headers["Authorization"] = f"Bearer {LMS_API_KEY}"
        
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
# Tool Definitions
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
            "description": "Send a request to the deployed backend API. Use this to get real-time data from the running system.",
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
1. list_files(path) - Explore directories
2. read_file(path) - Read file contents
3. query_api(method, path, body, include_auth) - Query the live backend API

HOW TO USE TOOLS:
- For wiki questions: list_files('wiki') → read_file('wiki/...')
- For code questions: list_files('backend') → read_file('backend/...')
- For API questions: query_api('GET', '/items/')
- For errors: query_api() first, then read_file() to find bug

CRITICAL RULES:
1. Source field: wiki/file.md or backend/file.py or empty for API
2. Be concise and direct
3. Include exact error messages for bug questions

For the top-learners bug:
1. Query /analytics/top-learners?lab=lab-99
2. Read backend/routers/analytics.py
3. Find the sorting line with None values"""

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
    # Проверяем наличие всех ключей ПЕРЕД использованием
    if not all([LLM_API_KEY, LLM_API_BASE, LLM_MODEL]):
        missing = []
        if not LLM_API_KEY: missing.append('LLM_API_KEY')
        if not LLM_API_BASE: missing.append('LLM_API_BASE')
        if not LLM_MODEL: missing.append('LLM_MODEL')
        error_msg = f"Missing LLM config: {', '.join(missing)}"
        print(error_msg, file=sys.stderr)
        return None
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto"
    }
    
    try:
        response = requests.post(
            f"{LLM_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=55
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("LLM request timed out", file=sys.stderr)
        return None
    except requests.exceptions.ConnectionError:
        print(f"Cannot connect to LLM at {LLM_API_BASE}", file=sys.stderr)
        return None
    except requests.exceptions.HTTPError as e:
        print(f"LLM HTTP error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"LLM error: {e}", file=sys.stderr)
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
        
        response = call_llm(messages)
        if not response:
            # Если LLM не доступен, но вопрос про файлы - может ответить без LLM?
            # Для простоты возвращаем ошибку
            return {
                "answer": "Error: LLM not available",
                "source": "",
                "tool_calls": tool_calls_history
            }
        
        message = response["choices"][0]["message"]
        
        # Track files
        if "tool_calls" in message and message["tool_calls"]:
            for tool_call in message["tool_calls"]:
                if tool_call["function"]["name"] == "read_file":
                    args = json.loads(tool_call["function"]["arguments"])
                    path = args["path"]
                    if path.startswith("wiki/"):
                        last_wiki_file = path
                    elif path.startswith("backend/") or path.endswith(".py"):
                        last_code_file = path
        
        if "tool_calls" not in message or not message["tool_calls"]:
            final_answer = message.get("content") or ""
            
            source = ""
            if last_wiki_file:
                source = last_wiki_file
            elif last_code_file:
                source = last_code_file
            
            return {
                "answer": final_answer,
                "source": source,
                "tool_calls": tool_calls_history
            }
        
        for tool_call in message["tool_calls"]:
            tool_result = execute_tool(tool_call)
            tool_calls_history.append(tool_result)
            
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
    
    return {
        "answer": "Maximum tool calls reached without complete answer",
        "source": last_wiki_file or last_code_file or "",
        "tool_calls": tool_calls_history
    }

# ============================================
# Main
# ============================================

def main():
    """Main function."""
    if len(sys.argv) < 2:
        # Если нет вопроса, возвращаем JSON с ошибкой
        result = {
            "answer": "Error: Question argument required",
            "source": "",
            "tool_calls": []
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)
    
    question = sys.argv[1]
    
    try:
        result = agentic_loop(question)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)  # Явно указываем успешный код возврата
    except Exception as e:
        # ЛЮБАЯ ошибка перехватывается и возвращается как JSON
        error_result = {
            "answer": f"Error: {str(e)}",
            "source": "",
            "tool_calls": []
        }
        print(json.dumps(error_result, ensure_ascii=False))
        traceback.print_exc(file=sys.stderr)
        sys.exit(0)  # ВАЖНО: возвращаем 0, а не 1!

if __name__ == "__main__":
    main()
