import os
import sys
import argparse
from dotenv import load_dotenv
from google import genai
from google.genai import types
from config import AI_SYSTEM_PROMPT
from functions.call_function import *
from utils.chat_parser import process_chat_history

def main():
    print("Hello from nevessa-ai!")
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    parser = argparse.ArgumentParser(description="Nevessa Chatbot")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--new-chat", action="store_true", help="Start a new chat by clearing the chat history. This will erase Nevessa's memory")
    parser.add_argument("--working-dir", type=str, help="Set the working directory for file operations")
    parser.add_argument("--summarize", action="store_true", help="Manually summarizes the chat history to cut chat.md down in size and length")
    args = parser.parse_args()
    new_chat = args.new_chat
    working_directory_arg = args.working_dir
    working_directory = None

    if new_chat: # command line argument that erases the history, effectively giving you a new chat
        open("chat.md", "w").close()
        print("Chat history cleared. Starting a new chat.")

    if api_key is None:
        raise RuntimeError("API key cannot be empty!")

    while True: # endless loop for constant chatting!

        try:
            user_prompt = input("You: ")
        except KeyboardInterrupt: # treating keyboardinterrupt as a quit combo
            print("\nExiting chat. Goodbye!")
            sys.exit()
    
        try: # working dir path for function calls, don't want to give it free reign!
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

        try: # open our chat history to send to Gemini for persistent memory
            chat_history = open("chat.md", "r").read()
            should_summarize = args.summarize or len(chat_history.split("\n")) >= 250
            if should_summarize:
                summary = summarize_history(client, chat_history)
                print(f"Summary: {summary}")
                with open("chat.md", "w") as chat_log:
                    chat_log.write(f"Summary: {summary}\n\n")
                chat_history = open("chat.md", "r").read()

            messages = process_chat_history(chat_history)
            if not messages:
                messages = []
                
        except FileNotFoundError: # creates a blank chat.md if not found
            print('Error: "chat.md" not found, creating a blank log now.')
            with open("chat.md", "x"):
                pass

        messages.append(types.Content(role="user", parts=[types.Part(text=user_prompt)])) # making sure our prompt is the last thing appended, until the response

        chat_log = open("chat.md", "a")
        chat_log.write(f"User: {user_prompt}\n\n") # store our prompt and append it to chat.md for presistent memory

        for _ in range(20): # for loop to help prevent Nevessa from endlessly making function calls
            response = generate_content(client, messages, args.verbose, working_directory) # inital response generation using our prompt and arguments
            if response:
                response_list = response.split("\n") # logic for storing Nevessa's response with code blocks and also stripping blank lines if code_block is false
                code_block = False
                for line in response_list:
                    if line.startswith("```"):
                            code_block = not code_block
                            chat_log.write(line + "\n")
                            continue
                    if code_block:
                        chat_log.write(line + "\n")
                        continue
                    if line.strip() != "":
                        chat_log.write(f"Nevessa: {line}\n\n")
                if code_block:
                    chat_log.write("```\n")
                    code_block = False
                print(f"Nevessa: {response}")
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
                summary = [line for line in response.split("\n") if line.strip()]
                return "\n".join(summary)
                
    return "Nothing to summarize."
        
    
if __name__ == "__main__":
    main()
