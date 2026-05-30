# Demo Prompt

This file is reserved for future prompt templates.

## Usage

When you add real LLM calls, store your system prompts and few-shot examples
here as Markdown files.  Load them at runtime with:

```python
from pathlib import Path

PROMPT_DIR = Path(__file__).parent
system_prompt = (PROMPT_DIR / "demo.md").read_text()
```

## Placeholder

> You are a helpful assistant.  Answer clearly and concisely.
