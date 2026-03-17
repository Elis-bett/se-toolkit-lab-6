import subprocess
import json
import sys
import os
import re

def test_framework_question():
    """Test that agent reads source code to find framework."""
    result = subprocess.run(
        [sys.executable, "agent.py", "What Python web framework does this project's backend use?"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Invalid JSON: {result.stdout}")
        assert False, "Output is not valid JSON"
    
    # Check required fields
    assert "answer" in output
    assert "tool_calls" in output
    
    # Check that read_file was called
    found_read_file = False
    for tool_call in output["tool_calls"]:
        if tool_call["tool"] == "read_file":
            found_read_file = True
            path = tool_call["args"]["path"]
            print(f"  Found read_file with path: {path}")
            # Should read a Python file
            assert path.endswith(".py"), f"Should read Python file: {path}"
    
    assert found_read_file, "Expected read_file to be called"
    
    # Answer should mention FastAPI
    assert "FastAPI" in output["answer"], f"Expected FastAPI in answer, got: {output['answer']}"
    
    print("✓ Test 1 passed: Framework question")

def test_items_count_question():
    """Test that agent queries API for item count."""
    result = subprocess.run(
        [sys.executable, "agent.py", "How many items are in the database?"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Invalid JSON: {result.stdout}")
        assert False, "Output is not valid JSON"
    
    # Check that query_api was called
    found_query_api = False
    for tool_call in output["tool_calls"]:
        if tool_call["tool"] == "query_api":
            found_query_api = True
            args = tool_call["args"]
            print(f"  Found query_api with args: {args}")
            assert args["method"] == "GET", f"Expected GET method, got: {args['method']}"
            assert "/items/" in args["path"], f"Expected /items/ path, got: {args['path']}"
    
    assert found_query_api, "Expected query_api to be called"
    
    # Answer should contain a number
    answer = output["answer"].lower()
    assert any(char.isdigit() for char in answer), f"Expected a number in answer, got: {output['answer']}"
    
    print("✓ Test 2 passed: Items count question")

def test_status_code_question():
    """Test that agent queries API for status code without auth."""
    result = subprocess.run(
        [sys.executable, "agent.py", "What HTTP status code does the API return when you request /items/ without an authentication header?"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Invalid JSON: {result.stdout}")
        assert False, "Output is not valid JSON"
    
    # Check that query_api was called
    found_query_api = False
    for tool_call in output["tool_calls"]:
        if tool_call["tool"] == "query_api":
            found_query_api = True
            args = tool_call["args"]
            print(f"  Found query_api with args: {args}")
            assert args["method"] == "GET", f"Expected GET method, got: {args['method']}"
            assert "/items/" in args["path"], f"Expected /items/ path, got: {args['path']}"
            
            # Check the result contains status code info
            try:
                result_data = json.loads(tool_call["result"])
                status_code = result_data.get("status_code")
                print(f"  API returned status code: {status_code}")
            except:
                print(f"  Could not parse result: {tool_call['result'][:100]}")
    
    assert found_query_api, "Expected query_api to be called"
    
    # Answer should contain a status code (any 3-digit number)
    answer = output["answer"]
    print(f"Answer contains: {answer[:200]}...")
    
    # Look for any 3-digit status code (200, 401, 403, etc.)
    status_codes = re.findall(r'\b\d{3}\b', answer)
    assert len(status_codes) > 0, f"Expected a 3-digit status code in answer, got: {answer}"
    
    print(f"✓ Found status code(s): {status_codes}")
    print("✓ Test 3 passed: Status code question")

def test_error_diagnosis_question():
    """Test that agent can diagnose API error by reading source code."""
    result = subprocess.run(
        [sys.executable, "agent.py", "Query /analytics/completion-rate for lab-99. What error do you get, and what is the bug in the source code?"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Invalid JSON: {result.stdout}")
        assert False, "Output is not valid JSON"
    
    # Check that both tools were called
    found_query_api = False
    found_read_file = False
    
    for tool_call in output["tool_calls"]:
        if tool_call["tool"] == "query_api":
            found_query_api = True
            print(f"  Found query_api: {tool_call['args']}")
        elif tool_call["tool"] == "read_file":
            found_read_file = True
            print(f"  Found read_file: {tool_call['args']}")
    
    assert found_query_api, "Expected query_api to be called"
    assert found_read_file, "Expected read_file to be called"
    
    # Answer should mention division by zero or ZeroDivisionError
    answer = output["answer"].lower()
    assert "zero" in answer or "division" in answer or "zerodivision" in answer, \
        f"Expected error about division by zero, got: {output['answer']}"
    
    print("✓ Test 4 passed: Error diagnosis question")

def test_mixed_tools_question():
    """Test that agent can use multiple tools in sequence."""
    result = subprocess.run(
        [sys.executable, "agent.py", "First, how many items are in the database? Then, what framework does the backend use?"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Invalid JSON: {result.stdout}")
        assert False, "Output is not valid JSON"
    
    # Check that multiple tools were called
    tools_used = set()
    for tool_call in output["tool_calls"]:
        tools_used.add(tool_call["tool"])
    
    print(f"  Tools used: {tools_used}")
    
    assert "query_api" in tools_used, "Expected query_api to be called"
    assert "read_file" in tools_used or "list_files" in tools_used, "Expected file tools to be called"
    assert len(tools_used) >= 2, f"Expected at least 2 different tools, got: {tools_used}"
    
    # Answer should contain both pieces of information
    answer = output["answer"].lower()
    assert any(char.isdigit() for char in answer), "Expected a number (item count) in answer"
    assert "fastapi" in answer, "Expected FastAPI in answer"
    
    print("✓ Test 5 passed: Mixed tools question")

if __name__ == "__main__":
    print("=" * 50)
    print("Running Task 3 tests...")
    print("=" * 50)
    
    tests = [
        test_framework_question,
        test_items_count_question,
        test_status_code_question,
        test_error_diagnosis_question,
        test_mixed_tools_question
    ]
    
    passed = 0
    for test in tests:
        try:
            print(f"\n▶ Running {test.__name__}...")
            test()
            passed += 1
            print(f"  ✓ {test.__name__} passed")
        except AssertionError as e:
            print(f"  ✗ {test.__name__} failed: {e}")
        except Exception as e:
            print(f"  ✗ {test.__name__} error: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print("=" * 50)
    
    if passed == len(tests):
        print("\n✓ All Task 3 tests passed!")
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
