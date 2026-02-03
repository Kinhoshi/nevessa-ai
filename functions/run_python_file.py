import os
import subprocess
from google import genai
from google.genai import types

def run_python_file(working_directory, file_path, args=None):
    try:
        working_dir_path = os.path.abspath(working_directory)

        if not os.path.isdir(working_dir_path):
            return f'Error: "{working_directory}" does not exist or is not a valid directory'

        target_dir = os.path.normpath(os.path.join(working_dir_path, file_path))
        valid_target_dir = os.path.commonpath([working_dir_path, target_dir]) == working_dir_path

        if not valid_target_dir:
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'

        if not os.path.isfile(target_dir):
            return f'Error: "{file_path}" does not exist or is not a regular file'
        
        if not file_path.endswith(".py"):
            return f'Error: "{file_path}" is not a Python file'

        command = ["python", target_dir]

        if args is not None:
            command.extend(args)

        process = subprocess.run(command, cwd=working_dir_path, capture_output=True, text=True, timeout=30)

        result = ""

        if process.returncode != 0:
            result = f"Process exited with code: {process.returncode}"

        if process.stdout == None and process.stderr == None:
            result = "No output produced"
        
        result = f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}"

        return result
    except Exception as e:
        return f"Error: {e}"


# SCHEMA
schema_run_python_file = types.FunctionDeclaration(
    name="run_python_file",
    description="Executes the specified file via Python from the specified directory, relative to the working directory",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="Path and name of the specified Python script to execute, relative to the working directory (default is the working directory itself)",
            ),
            "args": types.Schema(
                type=types.Type.ARRAY,
                description="Optional arguments when executing the specified Python script",
                items=types.Schema(type=types.Type.STRING)
            )
        },
        required=["file_path"]
    ),
)
