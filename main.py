from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()
import os
import platform
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

BASE_PROMPT = Path(__file__).with_name("command_generator_prompt.md").read_text(encoding="utf-8")

# Free-tier Gemini models. Flash is plenty for NL → shell command.
MODELS = [
    "gemini-2.5-flash",       # fast, generous free tier
    "gemini-2.5-flash-lite",  # cheapest/fastest
    "gemini-2.5-pro",         # most capable, lower free-tier limits
]

# Per-shell label and few-shot examples appended to the base prompt at request time.
SHELLS = {
    "cmd": {
        "label": "Windows CMD (cmd.exe)",
        "examples": (
            "- what is my public IP → curl ifconfig.me/ip\n"
            "- list files → dir\n"
            "- find python files containing TODO → findstr /s /m TODO *.py\n"
            "- show running processes → tasklist\n"
            "- show network configuration → ipconfig /all\n"
            "- compress the Logs folder into logs.zip → tar -a -c -f logs.zip Logs\n"
            "- download https://example.com/file.zip → curl https://example.com/file.zip -o file.zip"
        ),
    },
    "powershell": {
        "label": "Windows PowerShell",
        "examples": (
            "- what is my public IP → Invoke-RestMethod ifconfig.me/ip\n"
            "- list files → Get-ChildItem\n"
            "- find python files containing TODO → Get-ChildItem -Recurse -Filter *.py | Select-String TODO\n"
            "- show running processes → Get-Process\n"
            "- show network configuration → Get-NetIPConfiguration\n"
            "- compress the Logs folder into logs.zip → Compress-Archive -Path Logs -DestinationPath logs.zip\n"
            "- download https://example.com/file.zip → Invoke-WebRequest https://example.com/file.zip -OutFile file.zip"
        ),
    },
    "bash": {
        "label": "Linux / macOS Bash",
        "examples": (
            "- what is my public IP → curl ifconfig.me/ip\n"
            "- list files → ls -la\n"
            "- find python files containing TODO → grep -rn TODO --include=*.py\n"
            "- show running processes → ps aux\n"
            "- show network configuration → ip addr\n"
            "- compress the Logs folder into logs.zip → zip -r logs.zip Logs\n"
            "- download https://example.com/file.zip → curl https://example.com/file.zip -o file.zip"
        ),
    },
}


def detect_shell() -> str:
    """Default shell based on the OS this app is running on."""
    return "cmd" if platform.system() == "Windows" else "bash"


def build_system_instruction(base: str, shell_key: str) -> str:
    shell = SHELLS[shell_key]
    return (
        f"{base}\n\n"
        f"## Target shell\n\n{shell['label']}\n\n"
        f"## Examples\n\n{shell['examples']}\n"
    )


def nl_to_command(
    user_input: str,
    system_prompt: str = BASE_PROMPT,
    model: str = MODELS[0],
    shell_key: str = "cmd",
):
    """Convert natural language to a shell command.

    Stateless model fallback: tries the chosen model first, then the rest of
    MODELS in order if it returns a transient 503 (overloaded). Each request
    always starts from the user's choice — the previous request's outcome is
    not remembered.

    Returns (command, raw_response) so the UI can show debug details.
    """
    system_instruction = build_system_instruction(system_prompt, shell_key)
    chain = [model] + [m for m in MODELS if m != model]
    last_exc = None
    for candidate in chain:
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=user_input,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=1024,
                    thinking_config=types.ThinkingConfig(thinking_budget=512),
                ),
            )
            return (response.text or "").strip(), response
        except errors.ServerError as exc:  # 503 / overloaded → try next model
            last_exc = exc
    raise last_exc  # every model in the chain was unavailable


def generate(user_input: str, system_prompt: str, model: str, shell_key: str):
    """UI wrapper: never raises — surfaces errors in the output instead."""
    if not user_input.strip():
        return "", "Enter a request first."
    try:
        command, response = nl_to_command(user_input, system_prompt, model, shell_key)
        debug = response.model_dump_json(indent=2, exclude_none=True)
        return command, debug
    except Exception as exc:  # show the failure in the UI instead of crashing
        return f"⚠️ {type(exc).__name__}: {exc}", ""


def build_ui() -> gr.Blocks:
    shell_choices = [(v["label"], k) for k, v in SHELLS.items()]

    with gr.Blocks(title="clai — NL → shell command") as demo:
        gr.Markdown("# clai\nNatural language → shell command. Tweak the model and prompt to test.")

        with gr.Row():
            with gr.Column(scale=2):
                user_input = gr.Textbox(
                    label="Request",
                    placeholder="list all files modified in the last 7 days",
                    lines=2,
                )
                with gr.Row():
                    model = gr.Dropdown(MODELS, value=MODELS[0], label="Model")
                    shell = gr.Dropdown(shell_choices, value=detect_shell(), label="Target shell")
                run_btn = gr.Button("Generate command", variant="primary")
                command_out = gr.Code(label="Generated command", language="shell")

            with gr.Column(scale=1):
                system_prompt = gr.Textbox(
                    label="Base prompt (editable — shell + examples are appended automatically)",
                    value=BASE_PROMPT,
                    lines=10,
                )

        with gr.Accordion("Raw API response (debug)", open=False):
            debug_out = gr.Code(label="response", language="json")

        run_btn.click(
            generate,
            inputs=[user_input, system_prompt, model, shell],
            outputs=[command_out, debug_out],
        )
        user_input.submit(
            generate,
            inputs=[user_input, system_prompt, model, shell],
            outputs=[command_out, debug_out],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch()
