> [!WARNING]
> THIS TOY AGENT SHOULDN'T BE USED AS-IS. I TAKE NO RESPONSIBILITY FOR ANYTHING SHOULD YOU DISREGARD THIS WARNING.
> THIS CHATBOT WASN'T MADE WITH SECURITY IN MIND AND WAS JUST USED AS A LEARNING EXERCISE.

# Nevessa AI

Nevessa is an AI-powered coding agent designed to help you with your programming tasks. It can list files, read their contents, execute Python scripts, and even write new files for you.

## Features

*   **File Management:** List and read files within your project directory.
*   **Code Execution:** Run Python scripts with optional arguments.
*   **File Creation/Modification:** Create new files or update existing ones.

## Console Flags

* **--verbose:** Output will include additional details, such as token count, results of function calls made by Nevessa, etc.
* **--new_chat:** --new_chat will overwrite the contents of "chat.log" (or create the file if non-existent) to a blank slate, effectively erasing Nevessa's memory of prior prompts and responses.
* **--summarize:** Summarize the contents of "chat.log" into (hopefully) fewer lines and thus less prompt tokens while maintaining memory.
* **--working_directory:** Text followed --working_directory will be set as your working directory for the functions Nevessa can call during your prompt. 

## How to Use
First, create a ".env" file in the root folder and supply it with your Google Gemini API key in the following format: "GEMINI_API_KEY=yourkeyhere"
Then interact with Nevessa by entering a prompt between two double quotes (" ") after the command to run main.py, e.g "python3 main.py "Hello, Nevessa. Can you list the files in the working directory?" --verbose"
and then Nevessa's response will be printed to the console.