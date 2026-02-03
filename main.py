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
    args = parser.parse_args()
    user_prompt = args.user_prompt
    messages = [types.Content(role="user", parts=[types.Part(text=user_prompt)])]

    if api_key is None:
        raise RuntimeError("API key cannot be empty!")



    for _ in range(20):
        response = generate_content(client, messages, args.verbose)
        if response:
            print("Response:")
            print(response)
            break
    else:
        print("Error! Maximum iterations reached.")
        sys.exit(1)

def generate_content(client, messages, verbose):
    function_results = []

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
        print(f"User prompt: {messages[0].parts[0].text}")
        print(f"Prompt tokens: {prompt_tokens}")
        print(f"Response tokens: {response_tokens}")

    if query.function_calls is not None:
        for function in query.function_calls:
            function_call_result = call_function(function, verbose)
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
        
    
if __name__ == "__main__":
    main()
