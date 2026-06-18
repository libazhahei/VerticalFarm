import json
import time
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from llm.prompts.json_repair import JSON_FIX_TEMPLATE


def repair_json_with_model(error_json: str, schema: dict, model: BaseChatModel, max_attempts: int = 3) -> str:
    json_schema = json.dumps(schema, ensure_ascii=False, indent=2)
    prompt = PromptTemplate.from_template(JSON_FIX_TEMPLATE)
    parser = JsonOutputParser()
    attempts = 0
    content = error_json
    while attempts < max_attempts:
        try:
            chain = prompt | model | parser
            fixed = chain.invoke({"error_json": content, "json_schema": json_schema})
            if isinstance(fixed, dict):
                return json.dumps(fixed, ensure_ascii=False)
            return json.dumps(json.loads(str(fixed)), ensure_ascii=False)
        except Exception:
            attempts += 1
            time.sleep(0.5 * attempts)
    raise ValueError("Unable to repair JSON after multiple attempts")


def parse_json_with_fallback(raw_response: Any, expect_type: Any, repair_model: BaseChatModel) -> Any:
    parser = JsonOutputParser()
    try:
        parsed = parser.invoke(raw_response)
        return expect_type.model_validate(parsed)
    except Exception:
        raw_text = getattr(raw_response, "content", raw_response)
        if not isinstance(raw_text, str):
            raw_text = str(raw_text)
        fixed_text = repair_json_with_model(raw_text, expect_type.model_json_schema(), repair_model)
        return expect_type.model_validate(json.loads(fixed_text))


def fix_and_validate_json(
    json_str: BaseMessage | Any,
    expect_type: Any,
    repair_model: BaseChatModel,
    max_attempts: int = 3,
) -> str:
    prompt = PromptTemplate.from_template(JSON_FIX_TEMPLATE)
    parser = JsonOutputParser()
    chain = prompt | repair_model | parser
    attempts = 0
    content = json_str.content if hasattr(json_str, "content") else str(json_str)
    while attempts < max_attempts:
        try:
            fixed_json = chain.invoke(
                input={
                    "error_json": content,
                    "json_schema": json.dumps(expect_type.model_json_schema(), ensure_ascii=False, indent=2),
                }
            )
            return expect_type.model_validate(fixed_json).model_dump_json()
        except Exception:
            attempts += 1
            content = fixed_json if "fixed_json" in locals() else content
    return "{}"
