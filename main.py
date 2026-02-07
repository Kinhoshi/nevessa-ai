import os
import sys
import argparse
from dotenv import load_dotenv
from google import genai
from google.genai import types
from config import AI_SYSTEM_PROMPT
from functions.call_function import *

def main():
    print("Hello from nevessa-ai!")
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    parser = argparse.ArgumentParser(description="Nevessa Chatbot")
    parser.add_argument("user_prompt", type=str, help='Please enter a message in quotation marks ("") to send a prompt to Nevessa.')
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--new_chat", action="store_true", help="Start a new chat by clearing the chat history. This will erase Nevessa's memory")
    parser.add_argument("--working_directory", type=str, help="Set the working directory for file operations")
    parser.add_argument("--summarize_history", action="store_true", help="Manually summarizes the chat history to cut chat.log down in size and length")
    args = parser.parse_args()
    user_prompt = args.user_prompt
    new_chat = args.new_chat
    working_directory_arg = args.working_directory
    working_directory = None
    messages = []

    try:
        working_dir_config = open("working_dir_config.ini", "r").read()
        if working_directory_arg is not None:
            working_dir_path = os.path.abspath(working_directory_arg)
            if not os.path.isdir(working_dir_path):
                print(f'Error: "{working_directory_arg}" does not exist or is not a valid directory. Defaulting to Nevessa-AI root directory.')
                working_directory_arg = "."
            if working_dir_config != working_dir_path:
                config_file = open("working_dir_config.ini", "w")
                config_file.write(working_dir_path)
                config_file.close()
    except FileNotFoundError:
        print("Error: 'working_dir_config.ini' not found, creating file now.")
    try:
        working_dir_config_contents = open("working_dir_config.ini", "r").read()
        if os.path.isdir(working_dir_config_contents):
            working_directory = working_dir_config_contents
        else:
            print(f'Error: "{working_dir_config_contents}" does not contain a valid directory. Please pass a valid directory through, using "--working_directory [path]"')
    except FileNotFoundError:
        print("Error: 'working_dir_config.ini' not found. Please create the file and pass a valid directory through, using '--working_directory [path]'")

    if new_chat:
        open("chat.log", "w").close()
        print("Chat history cleared. Starting a new chat.")
    
    chat_history = open("chat.log", "r").read()
    if chat_history is not None:
        for lines in chat_history.split("\n"):
                if lines.startswith("Summary:"):
                    messages.append(types.Content(role="model", parts=[types.Part(text=lines)]))
                elif lines.startswith("User"):
                    messages.append(types.Content(role="user", parts=[types.Part(text=lines.lstrip("User: "))]))
                elif lines.startswith("Nevessa:"):
                    messages.append(types.Content(role="model", parts=[types.Part(text=lines.lstrip("Nevessa: "))]))
        
        if args.summarize_history or len(chat_history.split("\n")) >= 100:
            summary = summarize_history(client, chat_history)
            print(f"Summary: {summary}")
            chat_log = open("chat.log", "w")
            chat_log.write(f"Summary: {summary}\n")
            messages = [types.Content(role="model", parts=[types.Part(text=summary)])]

    messages.append(types.Content(role="user", parts=[types.Part(text=user_prompt)]))

    if api_key is None:
        raise RuntimeError("API key cannot be empty!")

    chat_log = open("chat.log", "a")
    chat_log.write(f"User: {user_prompt}\n")

    for _ in range(20):
        response = generate_content(client, messages, args.verbose, working_directory)
        if response:
            response_list = response.split("\n")
            for line in response_list:
                if line.strip() != "":
                    chat_log.write(f"Nevessa: {line}\n")
            print("Response:") 
            print(response)
            break
    else:
        print("Error! Maximum iterations reached.")
        sys.exit(1)

def generate_content(client, messages, verbose, working_directory):
    function_results = []

    if working_directory is None:
        print("No valid working directory set. Defaulting to Nevessa-AI root directory")
        working_directory = os.path.abspath(".")

    query = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(tools=[available_functions], system_instruction=AI_SYSTEM_PROMPT)
        )
    if query.usage_metadata is None:
        raise RuntimeError("Error! Please try again and ensure your API key is correctly entered.")

    if query.candidates:
        for candidate in query.candidates:
            messages.append(candidate.content)

    prompt_tokens = query.usage_metadata.prompt_token_count
    response_tokens = query.usage_metadata.candidates_token_count

    if verbose:
        print(f"User prompt: {messages[-2].parts[-1].text}")
        print(f"Prompt tokens: {prompt_tokens}")
        print(f"Response tokens: {response_tokens}")

    if query.function_calls is not None:
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
        if query.function_calls:
            messages.append(types.Content(role="user", parts=function_results))

    if not query.function_calls:
        return query.text

def summarize_history(client, content):
    if content is not None:
        summary_query = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Content(role="user", parts=[types.Part(text=content)])],
            config=types.GenerateContentConfig(system_instruction="""Summarize the above conversation in a concise manner, focusing on key points and important details. 
            The summary should be brief, but clear enough that an outside party knows it's a conversation between two parties.""")
        )
        if summary_query.usage_metadata is None:
            raise RuntimeError("Error! Please try again and ensure your API key is correctly entered.")

        if summary_query.candidates:
            if summary_query.text is not None:
                response = summary_query.text
                summary = response.split("\n")
                for i in range(len(summary) - 1, -1, -1):
                    if summary[i].strip() == "":
                        summary.pop(i)
                return "\n".join(summary)
                
    return "Nothing to summarize."
        
    
if __name__ == "__main__":
    main()
