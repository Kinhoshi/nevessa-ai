import os
from google import genai
from google.genai import types

def get_files_info(working_directory, directory="."):
    try:
        working_dir_path = os.path.abspath(working_directory)

        if not os.path.isdir(working_dir_path):
            return f'Error: "{working_directory}" does not exist or is not a valid directory'

        target_dir = os.path.normpath(os.path.join(working_dir_path, directory))
        valid_target_dir = os.path.commonpath([working_dir_path, target_dir]) == working_dir_path

        if not valid_target_dir:
            return f'Error: Cannot list "{directory}" as it is outside the permitted working directory'

        if not os.path.isdir(target_dir):
            return f'Error: "{directory}" is not a directory'

        listed_contents = os.listdir(target_dir)
        contents = []

        for item in listed_contents:
            contents.append(f"- {item}: file_size={os.path.getsize(os.path.join(target_dir, item))} bytes, is_dir={os.path.isdir(os.path.join(target_dir, item))}")
    
    
        if working_dir_path == target_dir:
            result = "Result for current directory:\n" + "\n".join(contents)
        else:
            result = f"Result for '{directory}' directory:\n" + "\n".join(contents)

        return result

    except Exception as e:
        return f"Error: {e}"


# SCHEMA

schema_get_files_info = types.FunctionDeclaration(
    name="get_files_info",
    description="Lists files in a specified directory relative to the working directory, providing file size and directory status",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "directory": types.Schema(
                type=types.Type.STRING,
                description="Directory path to list files from, relative to the working directory (default is the working directory itself)",
            ),
        },
    ),
)