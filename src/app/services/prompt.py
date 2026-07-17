def build_system_prompt() -> str:
    return (
        "You are a helpful AI assistant. "
        "Answer concisely, clearly, and in a friendly tone."
    )


def build_user_prompt(message: str, history: list[dict[str, str]] | None = None) -> str:
    prompt = []

    if history:
        for item in history[-6:]:
            prompt.append(
                f"{item['role'].capitalize()}: {item['content']}"
            )

    prompt.append(f"User: {message}")

    return "\n".join(prompt)