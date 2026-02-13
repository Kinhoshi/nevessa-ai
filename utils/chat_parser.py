from google import genai
from google.genai import types

def process_chat_history(chat_history):
    messages = []
    summary = []
    lines = chat_history.split("\n")
    collecting_summary = False
    code_block = False
    code_lines = []
    if chat_history is not None:
        for line in lines:
            if not collecting_summary and line.startswith("```"): # making code blocks priority so it doesn't get mixed up with summary, which should only be at the top of chat.md
                code_block = not code_block
                code_lines.append(line)

            elif code_block:
                code_lines.append(line)

            if line.startswith("Summary:") and not code_block: # appending the generated summary and any lines after that don't include "Summary:" in the beginning until we find a line that starts with "User" or "Nevessa"
                collecting_summary = True
                summary.append(line)

            elif line.startswith("User:") or line.startswith("Nevessa:"): # essentially ends our summary/code block collection and starts the normal line appending
                if collecting_summary:
                    messages.append(types.Content(role="model", parts=[types.Part(text="\n".join(summary))]))
                    summary = []
                    collecting_summary = False
                    
                if code_block:
                    messages.append(types.Content(role="model", parts=[types.Part(text="\n".join(code_lines))]))
                    code_lines = []
                    code_block = False
                    
                if line.startswith("User:"):
                    messages.append(types.Content(role="user", parts=[types.Part(text=line.lstrip("User: "))]))
                elif line.startswith("Nevessa:"):
                    messages.append(types.Content(role="model", parts=[types.Part(text=line.lstrip("Nevessa: "))]))

            elif collecting_summary:
                summary.append(line)
            
        if collecting_summary:
            messages.append(types.Content(role="model", parts=[types.Part(text="\n".join(summary))]))

        if code_block:
            messages.append(types.Content(role="model", parts=[types.Part(text="\n".join(code_lines))]))

    return messages