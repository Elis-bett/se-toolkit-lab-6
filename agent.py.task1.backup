#!/usr/bin/env python3
"""
Agent that calls LLM with a question and returns structured JSON response.
"""

import json
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.agent.secret')

def main():
    """Main function to handle question and return LLM response."""
    # Get question from command line argument
    if len(sys.argv) < 2:
        print("Error: Question argument required", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Get configuration
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')
    
    if not all([api_key, api_base, model]):
        print("Error: Missing required environment variables", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Provide concise answers."},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # Make the API call with timeout
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=55
        )
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        answer = result['choices'][0]['message']['content']
        
        # Format output as JSON
        output = {
            "answer": answer.strip(),
            "tool_calls": []
        }
        
        # Print only JSON to stdout
        print(json.dumps(output, ensure_ascii=False))
        
    except requests.exceptions.Timeout:
        print(json.dumps({
            "answer": "Error: Request timed out",
            "tool_calls": []
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "answer": f"Error: {str(e)}",
            "tool_calls": []
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()

