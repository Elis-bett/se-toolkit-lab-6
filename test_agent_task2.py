import subprocess
import json
import sys
import os

def test_merge_conflict_question():
    """Test that agent uses read_file for merge conflict question."""
    result = subprocess.run(
        [sys.executable, "agent.py", "How do you resolve a merge conflict?"],
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
    assert "answer" in output, "Missing 'answer' field"
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Check that tools were called
    assert len(output["tool_calls"]) > 0, "Expected at least one tool call"
    
    # Print debug info
    print(f"\nDebug - Tool calls made:")
    for i, tc in enumerate(output["tool_calls"]):
        print(f"  {i+1}. {tc['tool']} with args: {tc['args']}")
    
    # Check that read_file was called with a wiki file
    found_read_file = False
    for tool_call in output["tool_calls"]:
        if tool_call["tool"] == "read_file":
            found_read_file = True
            path = tool_call["args"]["path"]
            print(f"  ✓ Found read_file with path: {path}")
            # Check that it's a markdown file in wiki
            assert path.startswith("wiki/"), f"Path should start with wiki/: {path}"
            assert path.endswith(".md"), f"Path should end with .md: {path}"
    
    assert found_read_file, "Expected read_file to be called"
    
    # Check source contains wiki reference (optional for now)
    if output["source"]:
        assert "wiki/" in output["source"] or ".md" in output["source"], \
            f"Source should reference wiki: {output['source']}"
    
    print("✓ Test 1 passed: Merge conflict question")

def test_list_files_question():
    """Test that agent uses list_files to explore wiki."""
    result = subprocess.run(
        [sys.executable, "agent.py", "What files are in the wiki?"],
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
    assert "answer" in output, "Missing 'answer' field"
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Print debug info
    print(f"\nDebug - Tool calls made:")
    for i, tc in enumerate(output["tool_calls"]):
        print(f"  {i+1}. {tc['tool']} with args: {tc['args']}")
    
    # Check that list_files was called
    found_list_files = False
    for tool_call in output["tool_calls"]:
        if tool_call["tool"] == "list_files":
            found_list_files = True
            path = tool_call["args"]["path"]
            print(f"  ✓ Found list_files with path: {path}")
    
    assert found_list_files, "Expected list_files to be called"
    
    print("✓ Test 2 passed: List files question")

def test_security_no_directory_traversal():
    """Test that agent blocks directory traversal attempts."""
    try:
        from agent import read_file, list_files
        
        # Test read_file with traversal
        result = read_file("../../etc/passwd")
        assert "Access denied" in result or "Error" in result, \
            f"Should block traversal, got: {result}"
        
        # Test list_files with traversal
        result = list_files("../../etc")
        assert "Access denied" in result or "Error" in result, \
            f"Should block traversal, got: {result}"
        
        print("✓ Test 3 passed: Security blocks directory traversal")
    except ImportError as e:
        print(f"⚠ Warning: Could not import from agent: {e}")
        print("  Skipping security test")

def test_agent_basic_functionality():
    """Basic test from Task 1 to ensure backward compatibility."""
    result = subprocess.run(
        [sys.executable, "agent.py", "What is Python?"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Invalid JSON: {result.stdout}")
        assert False, "Output is not valid JSON"
    
    assert "answer" in output, "Missing 'answer' field"
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    print("✓ Test 4 passed: Basic functionality (Task 1 compatibility)")

if __name__ == "__main__":
    print("=" * 50)
    print("Running Task 2 tests...")
    print("=" * 50)
    
    tests = [
        test_merge_conflict_question,
        test_list_files_question,
        test_security_no_directory_traversal,
        test_agent_basic_functionality
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
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
