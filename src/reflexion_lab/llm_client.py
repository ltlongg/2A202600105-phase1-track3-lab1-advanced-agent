import os
import time
import json
import asyncio
from typing import Optional, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "token-not-needed")
VLLM_MODEL = os.getenv("VLLM_MODEL", "meta-llama/Llama-3-8B-Instruct")

client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY)

async def call_llm(system_prompt: str, user_prompt: str, response_format: Optional[str] = None) -> dict[str, Any]:
    """
    Hàm gọi vLLM bất đồng bộ và trả về response kèm token/latency thật.
    """
    start_time = time.time()
    
    extra_args = {}
    if response_format == "json":
        extra_args["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(
        model=VLLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        extra_body={
            "top_k": 5,
            "chat_template_kwargs": {"enable_thinking": False},
            },
        **extra_args
    )
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    return {
        "content": response.choices[0].message.content,
        "tokens": response.usage.total_tokens,
        "latency_ms": latency_ms
    }
