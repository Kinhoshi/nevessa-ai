import os
import sys
import argparse
import mimetypes
import base64
from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI
from config import AI_SYSTEM_PROMPT, GEMINI_MODEL, OPENAI_MODEL, DEFAULT_MODEL, GEMINI_MODEL_NAME, OPENAI_MODEL_NAME
from functions.call_function import call_function, call_function_openai, available_functions
from functions.call_function import convert_gemini_tools_to_openai
from utils.chat_parser import load_chat_state, save_chat_state, build_messages_from_state

def get_client(model_type):
    """Initialize and return the appropriate client based on model type"""
    if model_type == GEMINI_MODEL:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key is None:
            raise RuntimeError("GEMINI_API_KEY not found in environment variables!")
        return genai.Client(api_key=api_key), GEMINI_MODEL
    elif model_type == OPENAI_MODEL:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key is None:
            raise RuntimeError("OPENAI_API_KEY not found in environment variables!")
        return OpenAI(api_key=api_key), OPENAI_MODEL
    else:
        raise ValueError(f"Unsupported model type: {model_type}")

def main():
    print("Hello from nevessa-ai!")
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Nevessa Chatbot")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--model", choices=[GEMINI_MODEL, OPENAI_MODEL], default=DEFAULT_MODEL, help=f"Choose AI model (default: {DEFAULT_MODEL})")
    parser.add_argument("--new-chat", action="store_true", help="Start a new chat by clearing the chat history. This will erase Nevessa's memory")
    parser.add_argument("--working-dir", type=str, help="Set the working directory for file operations")
    parser.add_argument("--summarize", action="store_true", help="Manually summarizes chat.md to cut down in file size and length.")
    args = parser.parse_args()
    
    client, model_name = get_client(args.model)
    print(f"Using model: {model_name}")
    
    new_chat = args.new_chat
    working_directory_arg = args.working_dir
    working_directory = None

    if new_chat: # command line argument that erases the history, effectively giving you a new chat
        open("chat.json", "w").close()
        open("chat.md", "w").close()
        print("Chat history cleared. Starting a new chat.")

    while True: # endless loop for constant chatting!
        if args.summarize:
            try:
                chat_content = []
                chat_md = open("chat.md", "r").read()
                chat_md_content = chat_md.split("\n\n")
                for lines in chat_md_content:
                    if lines != "":
                        chat_content.append(lines)
                summary = summarize_history(client, args.model, " ".join(chat_content))
                with open("chat.md", "w") as f:
                    f.write(summary)

            except FileNotFoundError:
                print('Error: "chat.md" not found! Try again after chatting with Nevessa.')
                sys.exit(1)

        try:
            user_prompt = input("You: ")
            image_part = None
            final_text = user_prompt

            if user_prompt.startswith("/image"):
                remainder = user_prompt[len("/image"):].strip()
                parts = remainder.split(" ", 1)
                image_path = parts[0]
                remaining_prompt = parts[1] if len(parts) > 1 else "Describe this image."
                # make sure we use just the descriptive text for the model
                final_text = remaining_prompt
                image_abs_path = os.path.abspath(image_path)
                if not os.path.isfile(image_abs_path):
                    print(f'Error: File not found or not a normal file. "{image_abs_path}"')
                    continue
                mime_type, _ = mimetypes.guess_file_type(image_abs_path)
                if not mime_type or not mime_type.startswith("image/"):
                    print(f'Error: File is not a supported image type. "{image_abs_path}"')
                    continue
                with open(image_abs_path, "rb") as im:
                    image_bytes = im.read()
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                )

                
        except KeyboardInterrupt: # treating keyboardinterrupt as a quit combo
            print("\nExiting chat. Goodbye!")
            sys.exit()
    
        try: # working dir path for function calls, don't want to give it free rein!
            working_dir_config = open("working_dir_config.ini", "r").read()
            if working_directory_arg is not None:
                working_dir_path = os.path.abspath(working_directory_arg)
                if not os.path.isdir(working_dir_path):
                    print(f'Error: "{working_directory_arg}" does not exist or is not a valid directory. Defaulting to Nevessa-AI root directory.')
                    working_dir_path = os.path.abspath(".")
                if working_dir_config != working_dir_path:
                    config_file = open("working_dir_config.ini", "w")
                    config_file.write(working_dir_path)
                    config_file.close()
        except FileNotFoundError:
            print("Error: 'working_dir_config.ini' not found, creating file now.")
            open("working_dir_config.ini", "x").close()

        try: # making working dir persist between sessions so you don't have to use the command line arg every execution
            working_dir_config_contents = open("working_dir_config.ini", "r").read()
            if os.path.isdir(working_dir_config_contents):
                working_directory = working_dir_config_contents
            else:
                print(f'Error: "{working_dir_config_contents}" does not contain a valid directory. Please pass a valid directory through, using "--working-dir [path]"')
        except FileNotFoundError:
            print("Error: 'working_dir_config.ini' not found. Please create the file and pass a valid directory through, using '--working-dir [path]'")

        state = load_chat_state()

        if len(state["recent_turns"]) > 20:
            chat_md = []
            chat_md_content = open("chat.md", "r").read()
            if chat_md_content is not None:
                for lines in chat_md_content.split("\n\n"):
                    if lines != "":
                        chat_md.append(lines)
                summarize_chat_md = summarize_history(client, args.model, " ".join(chat_md))
                with open("chat.md", "w") as f:
                    f.write(summarize_chat_md + "\n\n")

            combined_text = ""
            for turn in state["recent_turns"]:
                combined_text += f"{turn['role'].capitalize()}: {turn['content']}\n\n"

            summary = summarize_history(client, args.model, combined_text)

            state["summary"] = summary

            # Clear short-term buffer
            state["recent_turns"] = []

            save_chat_state(state)

        messages = build_messages_from_state(state, final_text, image_part)
        for _ in range(20): # for loop to help prevent Nevessa from endlessly making function calls
            response = generate_content(client, args.model, messages, args.verbose, working_directory) # inital response generation using our prompt and arguments
            if response:
                # Update JSON state
                state["recent_turns"].append({
                    "role": "user",
                    "content": final_text
                })

                state["recent_turns"].append({
                    "role": "model",
                    "content": response
                })

                save_chat_state(state)
                chat_log = open("chat.md", "a")
                chat_log.write(f"## User\n{user_prompt}\n\n")
                chat_log.write(f"## Nevessa\n{response}\n\n")
                print(f"Nevessa: {response}")
                break
        else:
            print("Error! Maximum iterations reached.")
            sys.exit(1)

def generate_content(client, model_type, messages, verbose, working_directory):
    function_results = []

    if working_directory is None:
        print("No valid working directory set. Defaulting to Nevessa-AI root directory")
        working_directory = os.path.abspath(".")

    if model_type == GEMINI_MODEL:
        return generate_content_gemini(client, messages, verbose, working_directory)
    elif model_type == OPENAI_MODEL:
        return generate_content_openai(client, messages, verbose, working_directory, available_functions)

def generate_content_gemini(client, messages, verbose, working_directory):
    """Generate content using Gemini API"""
    while True:
        query = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=messages,
            config=types.GenerateContentConfig(tools=[available_functions], system_instruction=AI_SYSTEM_PROMPT)
        )
        if query.usage_metadata is None:
            raise RuntimeError("Error! Please try again and ensure your API key is correctly entered.")

        if query.candidates:
            candidate = query.candidates[0]
            if candidate.content:
                messages.append(candidate.content)

        if query.function_calls:
            function_results = []
            for function in query.function_calls:
                function_call_result = call_function(function, working_directory, verbose)
                if (
                    not function_call_result.parts
                    or not function_call_result.parts[0].function_response
                    or not function_call_result.parts[0].function_response.response
                ):
                    raise RuntimeError(f"Error: empty function response from {function.name}")

                function_results.append(function_call_result.parts[0])

                if verbose:
                    print(f"-> {function_call_result.parts[0].function_response.response['result']}")
            if function_results:
                messages.append(types.Content(role="user", parts=function_results))
        else:
            # No more function calls, return the text
            return query.text



def convert_image_part_to_openai_message(image_part, role="user"):
    """Convert a Gemini ``types.Part`` containing image data into an
    OpenAI-style chat message.

    The helper handles both inline bytes (``inline_data``) and URI-based
    parts (``file_data``).  It returns a dict suitable for appending to the
    ``messages`` list that is passed directly to ``client.chat.completions.create``.
    If the part has no image data, ``None`` is returned.
    """
    if image_part is None:
        return None

    # inline bytes were created with ``Part.from_bytes``
    blob = getattr(image_part, "inline_data", None)
    if blob and getattr(blob, "mime_type", None) and getattr(blob, "data", None):
        b64 = base64.b64encode(blob.data).decode("utf-8")
        uri = f"data:{blob.mime_type};base64,{b64}"
        # markdown image syntax is understood by OpenAI models
        return {"role": role, "content": f"![image]({uri})"}

    # file-URI based images (rare in our code, but supported by the type)
    filedata = getattr(image_part, "file_data", None)
    if filedata and getattr(filedata, "file_uri", None):
        uri = filedata.file_uri
        return {"role": role, "content": f"![image]({uri})"}

    return None


def generate_content_openai(client, messages, verbose, working_directory, available_functions):
    """Generate content using OpenAI API"""
    # Convert Gemini-style messages to OpenAI format if needed
    openai_messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}]
    
    for msg in messages:
        if isinstance(msg, types.Content):
            # Convert from Gemini Content object
            role = msg.role if msg.role in ["user", "assistant"] else "user"
            text_parts = []
            image_messages = []
            for part in msg.parts:
                if hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
                else:
                    # any non-text part might be an image; try converting
                    img_msg = convert_image_part_to_openai_message(part, role=role)
                    if img_msg:
                        image_messages.append(img_msg)
            # append the text portion first (if present)
            if text_parts:
                openai_messages.append({"role": role, "content": "\n".join(text_parts)})
            # then any image-specific messages
            for im in image_messages:
                openai_messages.append(im)
        else:
            # Already in dict format
            openai_messages.append(msg)

    openai_tools = convert_gemini_tools_to_openai(available_functions)

    while True:
        # Make the request
        response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=openai_messages,
            tools=openai_tools if openai_tools else None
        )

        if verbose:
            print(f"Prompt tokens: {response.usage.prompt_tokens}")
            print(f"Response tokens: {response.usage.completion_tokens}")

        # Append the assistant's message
        openai_messages.append({
            "role": "assistant",
            "content": response.choices[0].message.content,
            "tool_calls": response.choices[0].message.tool_calls
        })

        # If there are tool calls, execute them
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                tool_result = call_function_openai(tool_call.function, working_directory, verbose)
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
        else:
            # No more tool calls, return the content
            return response.choices[0].message.content

def summarize_history(client, model_type, content):
    """Summarize chat history using the specified model"""
    if content is not None:
        if model_type == GEMINI_MODEL:
            return summarize_history_gemini(client, content)
        elif model_type == OPENAI_MODEL:
            return summarize_history_openai(client, content)
    return "Nothing to summarize."

def summarize_history_gemini(client, content):
    """Summarize using Gemini API"""
    summary_query = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=[types.Content(role="user", parts=[types.Part(text=content)])],
        config=types.GenerateContentConfig(system_instruction="""
        Summarize this conversation as long-term memory notes for a friendly AI assistant.
        Focus on:
        - User goals
        - Ongoing projects
        - Preferences
        - Important context
        Keep concise.
        A reminder: Lines beginning with "Nevessa" or "model" are responses from the AI, lines beginning with "User" or "user" are user prompts, please remember that in your summaries.
        Another reminder: Anything within the prompt is to be summarized and your response should just be a short summary of it, please don't respond as if it's a live prompt.
        """)
    )
    if summary_query.usage_metadata is None:
        raise RuntimeError("Error! Please try again and ensure your API key is correctly entered.")

    if summary_query.candidates:
        if summary_query.text is not None:
            response = summary_query.text
            summary = [line for line in response.split("\n") if line.strip()]
            return "\n".join("  " + line for line in summary)
            
    return "Nothing to summarize."

def summarize_history_openai(client, content):
    """Summarize using OpenAI API"""
    summary_query = client.chat.completions.create(
        model=OPENAI_MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": """Summarize this conversation as long-term memory notes for a friendly AI assistant.
Focus on:
- User goals
- Ongoing projects
- Preferences
- Important context
Keep concise.
A reminder: Lines beginning with "Nevessa" or "model" are responses from the AI, lines beginning with "User" or "user" are user prompts, please remember that in your summaries.
Another reminder: Anything within the prompt is to be summarized and your response should just be a short summary of it, please don't respond as if it's a live prompt.
"""
            },
            {
                "role": "user",
                "content": content
            }
        ]
    )
    
    if summary_query.choices:
        response = summary_query.choices[0].message.content
        if response:
            summary = [line for line in response.split("\n") if line.strip()]
            return "\n".join("  " + line for line in summary)
    
    return "Nothing to summarize."
        
    
if __name__ == "__main__":
    main()
