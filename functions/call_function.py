import os
from functions.get_files_info import *
from functions.get_file_content import *
from functions.write_file import *
from functions.run_python_file import *
from google import genai
from google.genai import types

available_functions = types.Tool(function_declarations=[schema_get_files_info, schema_get_file_content, schema_write_file, schema_run_python_file])

def convert_schema_to_openai(gemini_schema):
    """Convert Gemini Schema to OpenAI JSON schema format"""
    schema_dict = {}
    
    # Map Gemini types to JSON schema types
    type_mapping = {
        types.Type.STRING: "string",
        types.Type.NUMBER: "number",
        types.Type.INTEGER: "integer",
        types.Type.BOOLEAN: "boolean",
        types.Type.ARRAY: "array",
        types.Type.OBJECT: "object",
    }
    
    # Get the type
    if hasattr(gemini_schema, 'type') and gemini_schema.type:
        schema_dict["type"] = type_mapping.get(gemini_schema.type, "string")
    
    # Add description
    if hasattr(gemini_schema, 'description') and gemini_schema.description:
        schema_dict["description"] = gemini_schema.description
    
    # Handle properties (for objects)
    if hasattr(gemini_schema, 'properties') and gemini_schema.properties:
        schema_dict["properties"] = {}
        for prop_name, prop_schema in gemini_schema.properties.items():
            schema_dict["properties"][prop_name] = convert_schema_to_openai(prop_schema)
    
    # Handle required fields
    if hasattr(gemini_schema, 'required') and gemini_schema.required:
        schema_dict["required"] = gemini_schema.required
    
    # Handle items (for arrays)
    if hasattr(gemini_schema, 'items') and gemini_schema.items:
        schema_dict["items"] = convert_schema_to_openai(gemini_schema.items)
    
    # Handle enum
    if hasattr(gemini_schema, 'enum') and gemini_schema.enum:
        schema_dict["enum"] = gemini_schema.enum
    
    return schema_dict

def convert_gemini_tools_to_openai(gemini_tool):
    """Convert Gemini Tool to OpenAI tools format"""
    openai_tools = []
    
    if hasattr(gemini_tool, 'function_declarations'):
        for func_decl in gemini_tool.function_declarations:
            tool_dict = {
                "type": "function",
                "function": {
                    "name": func_decl.name,
                    "description": func_decl.description or "",
                    "parameters": convert_schema_to_openai(func_decl.parameters) if func_decl.parameters else {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
            openai_tools.append(tool_dict)
    
    return openai_tools

def call_function(function_call, working_directory, verbose=False):
    if not os.path.isdir(working_directory):
        print(f'Error: "{working_directory}" is not a valid directory. Defaulting to Nevessa-AI root directory.')
        working_directory = os.path.abspath(".")

    if verbose:
        print(f"Calling function: {function_call.name}({function_call.args})")

    else: print(f" - Calling function: {function_call.name}")

    function_map = {
        "get_files_info": get_files_info,
        "get_file_content": get_file_content,
        "write_file": write_file,
        "run_python_file": run_python_file
    }

    function_name = function_call.name or ""

    if function_name not in function_map:
        return types.Content(
            role="tool",
            parts=[
                types.Part.from_function_response(
                    name=function_name,
                    response={"error": f"Unknown function: {function_name}"},
                )
            ],
        )

    args = dict(function_call.args) if function_call.args else {}
    args["working_directory"] = working_directory

    try:
        function_result = function_map[function_name](**args)
    except Exception as e:
        function_result = f"Error: {e}"

    return types.Content(
        role="tool",
        parts=[
            types.Part.from_function_response(
                name=function_name,
                response={"result": function_result},
            )
        ],
    )

def call_function_openai(function_call, working_directory, verbose=False):
    """Call function and return result for OpenAI tool calls"""
    if not os.path.isdir(working_directory):
        print(f'Error: "{working_directory}" is not a valid directory. Defaulting to Nevessa-AI root directory.')
        working_directory = os.path.abspath(".")

    if verbose:
        print(f"Calling function: {function_call.name}({function_call.arguments})")
    else:
        print(f" - Calling function: {function_call.name}")

    function_map = {
        "get_files_info": get_files_info,
        "get_file_content": get_file_content,
        "write_file": write_file,
        "run_python_file": run_python_file
    }

    function_name = function_call.name

    if function_name not in function_map:
        return f"Unknown function: {function_name}"

    import json
    args = json.loads(function_call.arguments) if function_call.arguments else {}
    args["working_directory"] = working_directory

    try:
        function_result = function_map[function_name](**args)
        return function_result
    except Exception as e:
        return f"Error: {e}"