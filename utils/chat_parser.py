import json
from google.genai import types

MAX_TURNS = 10  # adjust as desired


def load_chat_state():
    try:
        with open("chat.json", "r") as f:
            content = f.read()
            if not content:
                return {
                    "summary": "",
                    "recent_turns": []
                }
            return json.loads(content)
    except FileNotFoundError:
        return {
            "summary": "",
            "recent_turns": []
        }


def save_chat_state(state):
    with open("chat.json", "w") as f:
        json.dump(state, f, indent=2)


def build_messages_from_state(state, current_user_prompt, image_part):
    messages = []

    # Inject persistent memory as background context
    if state["summary"]:
        messages.append(
            types.Content(
                role="user",
                parts=[types.Part(
                    text=f"Persistent memory from previous conversations:\n{state['summary']}"
                )]
            )
        )

    # Only use recent turns (sliding window)
    recent_turns = state["recent_turns"][-MAX_TURNS:]

    for turn in recent_turns:
        messages.append(
            types.Content(
                role=turn["role"],
                parts=[types.Part(text=turn["content"])]
            )
        )

    # Current user message must be last
    parts = [types.Part(text=current_user_prompt)]

    if image_part is not None:
        parts.append(image_part)

    messages.append(
        types.Content(
            role="user",
            parts=parts
        )
    )

    return messages