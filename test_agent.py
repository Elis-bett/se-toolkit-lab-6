import subprocess
import json
import sys

def test_agent_basic_question():
    """Test that agent returns valid JSON with answer and tool_calls."""
    # Run the agent
    result = subprocess.run(
        [sys.executable, "agent.py", "What does REST stand for?"],
        capture_output=True,
        text=True
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    # Parse JSON from stdout
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Invalid JSON output: {result.stdout}", file=sys.stderr)
        assert False, "Output is not valid JSON"
    
    # Check required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"
    assert len(output["tool_calls"]) == 0, "'tool_calls' should be empty for task 1"
    
    # Verify answer is not empty
    assert len(output["answer"].strip()) > 0, "'answer' should not be empty"
    
    print("✓ Test passed: Agent returns valid JSON with required fields")

if __name__ == "__main__":
    test_agent_basic_question()
