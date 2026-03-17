# Agent Documentation

## Architecture Overview
Simple CLI agent that forwards questions to an LLM and returns structured JSON responses.

## LLM Provider
- **Provider**: Qwen Code API
- **Model**: qwen3-coder-plus
- **Configuration**: Environment variables in `.env.agent.secret`

## How to Run
```bash
uv run agent.py "Your question here"
