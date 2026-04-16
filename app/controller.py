import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, ValidationError, field_validator
from pydantic_core import from_json

from model import ProviderPriority


def load_system_prompt() -> str:
    with open("./system_prompt.txt", "r", encoding="utf-8") as f:
        return f.read()


BASE_URL = "http://localhost:3001"
@retry(
    stop=stop_after_attempt(3),  # 3 intentos max
    wait=wait_exponential(multiplier=1, min=1, max=10),  # 1s, 2s, 4s backoff
    retry=retry_if_exception_type((requests.RequestException,)),  # Solo errores de red
)
def extract(user_input:str, system_prompt:str) -> tuple[str,str,str]: 
    ENDPOINT = f"{BASE_URL}/v1/ai/extract"

    headers = {
        "X-API-Key": "test-dev-2026"
    }

    messages = [ 
        {"role":"system","content":system_prompt},
        {"role":"user","content":user_input},
          ]

    try:
        response = requests.post(ENDPOINT,
                    headers=headers,
                    json={"messages": messages},
                    timeout=(3.0, 10.0), # 3 seconds for connection and 10 por read.
                    )

        response.raise_for_status()

        if response.status_code == 200:
            data = response.json()
            # El mensaje de la respuesta está en choices[0].message.content
            content = data['choices'][0]['message']['content']
            print(f"EXTRACTED CONTENT:\n\n{content}")
            extracted_message = parse_llm_response(content)
            return (extracted_message.message, extracted_message.to, extracted_message.type)
    except Exception as e:
        print(f"CONTROLLER ERROR:{e}")
        raise e


@retry(
    stop=stop_after_attempt(3),  # 3 intentos max
    wait=wait_exponential(multiplier=1, min=1, max=10),  # 1s, 2s, 4s backoff
    retry=retry_if_exception_type((requests.RequestException,)),  # Solo errores de red
)
def notify(message:str,to:str,type:str, priority : ProviderPriority = "normal", trace_id: str = None):

    ENDPOINT = f"{BASE_URL}/v1/notify"

    headers = {
        "X-API-Key": "test-dev-2026"
    }

    params = {
        "priority" : str(priority),
        "trace_id" : trace_id # if it's None, requests lib will ignore it. 
    }

    notification = {
        "message":message,
        "type":type,
        "to":to
    }

    response = requests.post(ENDPOINT,
                  headers=headers,
                  params=params,
                  json=notification,
                  timeout=(3.0, 10.0), # 3 seconds for connection and 10 por read.
                  )

    response.raise_for_status()
    
    print(f"CONTROLLER STATUS CODE:{response.status_code}")
    print(f"CONTROLLER TEXT:{response.text}")

    return response

# region CleanUp Response


PHONE_RE = re.compile(r"\+?\d[\d\s\-\(\)]{6,}\d")
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}\b")

class ExtractedMessage(BaseModel):
    to: str
    message: str
    type: Literal["email", "sms"]

    @field_validator("to")
    @classmethod
    def validate_to(cls, v, info):
        msg_type = info.data.get("type")
        if msg_type == "email":
            if not EMAIL_RE.fullmatch(v):
                raise ValueError("Invalid email")
        elif msg_type == "sms":
            normalized = normalize_phone(v)
            if not normalized:
                raise ValueError("Invalid phone")
            return normalized
        return v

def normalize_phone(value: str) -> Optional[str]:
    value = value.strip()
    has_plus = value.startswith("+")
    digits = re.sub(r"\D", "", value)
    if len(digits) < 8 or len(digits) > 15:
        return None
    return f"+{digits}" if has_plus else digits

def strip_markdown_fences(text: str) -> str:
    text = text.strip().replace("\ufeff", "")
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def extract_json_block(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text

def repair_json(text: str) -> str:
    text = strip_markdown_fences(text)
    text = extract_json_block(text)
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)", r'\1"\2"\3', text)
    if "'" in text and '"' not in text:
        text = text.replace("'", '"')
    return text

def fallback_extract(raw: str) -> dict:
    lowered = raw.lower()

    email = EMAIL_RE.search(raw)
    phone = PHONE_RE.search(raw)

    inferred_type = None
    to = None

    if email:
        inferred_type = "email"
        to = email.group(0)
    elif phone:
        inferred_type = "sms"
        to = normalize_phone(phone.group(0))

    message = None
    m = re.search(r'"message"\s*:\s*"((?:\\.|[^"])*)"', raw, flags=re.S)
    if m:
        message = bytes(m.group(1), "utf-8").decode("unicode_escape")

    if not message:
        message = raw.strip()

    return {
        "to": to or "",
        "message": message.strip(),
        "type": inferred_type or ("sms" if "sms" in lowered else "email" if "email" in lowered else "")
    }

def parse_llm_response(raw: str) -> ExtractedMessage:
    cleaned = repair_json(raw)

    try:
        data = json.loads(cleaned)
        return ExtractedMessage.model_validate(data)
    except Exception:
        pass

    try:
        partial = from_json(cleaned, allow_partial=True)
        if isinstance(partial, dict):
            return ExtractedMessage.model_validate(partial)
    except Exception:
        pass

    data = fallback_extract(raw)
    return ExtractedMessage.model_validate(data)

# endregion