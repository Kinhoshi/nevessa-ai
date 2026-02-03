import os
from google import genai
from google.genai import types

def write_file(working_directory, file_path, content):
    try:
        working_dir_path = os.path.abspath(working_directory)

        if not os.path.isdir(working_dir_path):
            return f'Error: "{working_directory}" does not exist or is not a valid directory'
        
        target_dir = os.path.normpath(os.path.join(working_dir_path, file_path))
        valid_target_dir = os.path.commonpath([working_dir_path, target_dir]) == working_dir_path

        if not valid_target_dir:
            return f'Error: Cannot write to "{file_path}" as it is outside the permitted working directory'
        
        if os.path.isdir(target_dir):
            return f'Error: Cannot write to "{file_path}" as it is a directory'

        os.makedirs(os.path.dirname(target_dir), exist_ok=True)

        file = open(target_dir, "w")
        file.write(content)

        return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'

    except Exception as e:
        return f"Error: {e}"


# SCHEMA

schema_write_file = types.FunctionDeclaration(
    name="write_file",
    description="Creates a file with the specified name and content, relative to the working directory",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="Path to create (if non-existent) and file to create itself, relative to the working directory (default is the working directory itself)",
            ),
            "content": types.Schema(
                type=types.Type.STRING,
                description="The specified content to be written to the earlier specified file"
            )
        },
        required=["file_path", "content"],
        property_ordering=["file_path", "content"]
    ),
)