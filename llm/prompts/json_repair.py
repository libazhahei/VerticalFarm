JSON_FIX_TEMPLATE = """
## Role
You are a JSON repair tool.

## Task
Your task is to parse the content below, fix any JSON formatting issues, and return only valid JSON.

## JSON Schema
{json_schema}

## Input
{error_json}

## Output
Provide the corrected JSON only.
"""
