import os
from config import *
from google import genai
from google.genai import types

def get_file_content(working_directory, file_path):
    MAX_CHARS = FILE_MAX_CHARS
    try:
        working_dir_path = os.path.abspath(working_directory)

        if not os.path.isdir(working_dir_path):
            return f'Error: "{working_directory}" does not exist or is not a valid directory'
        
        target_dir = os.path.normpath(os.path.join(working_dir_path, file_path))
        valid_target_dir = os.path.commonpath([working_dir_path, target_dir]) == working_dir_path

        if not valid_target_dir:
            return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'

        if not os.path.isfile(target_dir):
            return f'Error: File not found or is not a regular file: "{file_path}"'

        file = open(target_dir, "r")
        content = file.read(MAX_CHARS)

        if file.read(1):
            content += f' [...File "{file_path}" truncated at {MAX_CHARS} characters]'

        return f'Result for "{file_path}":\n' + content

    except Exception as e:
        return f"Error: {e}"


# SCHEMA

schema_get_file_content = types.FunctionDeclaration(
    name="get_file_content",
    description="Returns the contents of the specified file, relative to the working directory",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="Path and name of the file to read, relative to the working directory (default is the working directory itself)",
            ),
        },
        required=["file_path"]
    ),
)