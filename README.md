# clai

Natural language → shell command. A small Gradio web app that turns a plain-English
request into a single, ready-to-paste command for your target shell, powered by
Google Gemini.

Type something like *"list all files modified in the last 7 days"* and get back a
command you can copy straight into your terminal — no editing required.

## Features

- **NL → shell command** for three target shells: Windows CMD, Windows PowerShell,
  and Linux/macOS Bash. The default is chosen from the OS the app runs on.
- **Model fallback** — picks your chosen Gemini model first, then automatically
  retries the others if one is overloaded (503).
- **Safety-aware prompt** — keeps shells' built-in confirmation prompts, stays
  within the requested scope, and never adds force/quiet flags or unrequested
  destructive behavior.
- **Editable base prompt** and a **raw-response debug view** in the UI for quick
  experimentation.

## Requirements

- Python ≥ 3.13
- A Google Gemini API key
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Setup

1. Install dependencies:

   ```sh
   uv sync
   ```

2. Create a `.env` file in the project root with your Gemini API key:

   ```sh
   GEMINI_API_KEY=your_api_key_here
   ```

   Get a key from [Google AI Studio](https://aistudio.google.com/apikey).

## Usage

```sh
uv run main.py
```

This launches the Gradio app locally and prints a URL (e.g. http://127.0.0.1:7860).
Open it in your browser, then:

1. Enter your request in natural language.
2. Pick the **model** and **target shell**.
3. Click **Generate command** (or press Enter) and copy the result.

## Models

The free-tier Gemini models used, in fallback order:

| Model | Notes |
| --- | --- |
| `gemini-2.5-flash` | Fast, generous free tier (default) |
| `gemini-2.5-flash-lite` | Cheapest / fastest |
| `gemini-2.5-pro` | Most capable, lower free-tier limits |

## Project structure

| File | Purpose |
| --- | --- |
| `main.py` | App entry point, Gemini client, and Gradio UI |
| `command_generator_prompt.md` | Base system prompt defining behavior and safety rules |
| `pyproject.toml` | Project metadata and dependencies |
