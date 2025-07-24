from langchain_ollama import ChatOllama

def get_llm_response(prompt: str, code_only: bool = False) -> str:
    """
    Queries the local Ollama LLM and returns a structured, controlled response.
    
    Parameters:
    - prompt: user input string.
    - code_only: if True, return only raw code (no markdown or explanations).
    
    Returns:
    - str: LLM's output (cleaned).
    """
    try:
        # System instructions tailored for agent obedience
        if code_only:
            system_instruction = (
                "Respond with code only. No markdown, no triple backticks, no explanations. "
                "Only output raw code. Assume the user needs ready-to-run scripts."
            )
        else:
            system_instruction = (
                "You are Lucifer's Linux agent. Do NOT use tool names like `wifi_status()` — "
                "use tool names exactly like `wifi_status`. Do not use parentheses for tool calls.\n"
                "When answering, think step-by-step. Be precise and strict with tool syntax.\n"
                "When user asks for code, generate only what’s necessary. Avoid assumptions.\n"
                "Stay in character: you are a powerful assistant, not a chatbot. Keep answers professional."
            )

        # Initialize LLM with custom behavior
        llm = ChatOllama(
            model="llama3:8b",
            temperature=0.4,
            system=system_instruction
        )

        # Make the request
        response = llm.invoke(prompt.strip())

        return response.content.strip()

    except Exception as e:
        return f"❌ Failed to contact LLM: {e}"
