from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()
import os
from pathlib import Path
import anthropic
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = Path(__file__).with_name("command_generator_prompt.md").read_text(encoding="utf-8")

# Current Claude models — default to the most capable. See platform.claude.com for the full list.
MODELS = [
    "claude-opus-4-7",    # most capable
    "claude-sonnet-4-6",  # best speed/intelligence balance
    "claude-haiku-4-5",   # fastest, cheapest
]


def nl_to_command(user_input: str, system_prompt: str = SYSTEM_PROMPT, model: str = MODELS[1]):
    """Convert natural language to a shell command.

    Returns (command, raw_response) so the UI can show debug details.
    """
    response = client.messages.create(
        model=model,
        max_tokens=512,
        # system prompt as a top-level parameter, with prompt caching on the prefix.
        # (Caching only kicks in once the prefix exceeds the model's minimum — ~4096
        # tokens for Opus/Haiku — so a short prompt like this won't actually cache yet.)
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_input}],
    )
    command = next((b.text for b in response.content if b.type == "text"), "")
    return command, response


def generate(user_input: str, system_prompt: str, model: str):
    """UI wrapper: never raises — surfaces errors in the output instead."""
    if not user_input.strip():
        return "", "Enter a request first."
    try:
        command, response = nl_to_command(user_input, system_prompt, model)
        debug = response.to_json()
        return command, debug
    except Exception as exc:  # show the failure in the UI instead of crashing
        return f"⚠️ {type(exc).__name__}: {exc}", ""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="clai — NL → shell command") as demo:
        gr.Markdown("# clai\nNatural language → shell command. Tweak the model and prompt to test.")

        with gr.Row():
            with gr.Column(scale=2):
                user_input = gr.Textbox(
                    label="Request",
                    placeholder="list all files modified in the last 7 days",
                    lines=2,
                )
                model = gr.Dropdown(MODELS, value=MODELS[1], label="Model")
                run_btn = gr.Button("Generate command", variant="primary")
                command_out = gr.Textbox(label="Generated command", lines=2)

            with gr.Column(scale=1):
                system_prompt = gr.Textbox(
                    label="System prompt (editable)",
                    value=SYSTEM_PROMPT,
                    lines=10,
                )

        with gr.Accordion("Raw API response (debug)", open=False):
            debug_out = gr.Code(label="response", language="json")

        run_btn.click(
            generate,
            inputs=[user_input, system_prompt, model],
            outputs=[command_out, debug_out],
        )
        user_input.submit(
            generate,
            inputs=[user_input, system_prompt, model],
            outputs=[command_out, debug_out],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch()
