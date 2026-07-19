import os
import json
import re
from openai import OpenAI
from pydantic import ValidationError
from dotenv import load_dotenv
from .schemas import ExtractionSchema

load_dotenv()

import requests

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = os.getenv("NIM_MODEL", "meta/llama-3.1-70b-instruct")

or_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    max_retries=1,
    timeout=20.0
)
OR_MODEL_NAME = "llama-3.3-70b-versatile"

def agent_1_extract(signal_text: str) -> ExtractionSchema:
    prompt = f"""Extract the following information from the text into JSON. 
Text: {signal_text}

JSON format:
{{
  "corridor": "string (extract the geographic chokepoint or 'unknown')",
  "commodity": "string (default to 'crude_oil')",
  "economy": "string (default to 'IN')",
  "named_refinery": "string (extract or default to 'Jamnagar')",
  "volume_lost_mbd": float (extract from text or default to 10.0. MUST be <= 21.0),
  "duration_days": int (extract from text or default to 30),
  "confidence": float (0.0 to 1.0)
}}
"""
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
            "Accept": "application/json",
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "top_p": 0.95,
            "max_tokens": 8192,
            "stream": False
        }
        response = requests.post(NVIDIA_API_URL, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        clean_json = re.sub(r'```json\n|```', '', content).strip()
        data = json.loads(clean_json)
        return ExtractionSchema(**data)
    except Exception as e:
        print(f"Agent 1 NVIDIA Extraction failed: {e}. Falling back to OpenRouter...")
        try:
            response = or_client.chat.completions.create(
                model=OR_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            content = response.choices[0].message.content
            clean_json = re.sub(r'```json\n|```', '', content).strip()
            data = json.loads(clean_json)
            return ExtractionSchema(**data)
        except Exception as e2:
            print(f"Agent 1 Groq Fallback failed: {e2}. Using default schema.")
            return ExtractionSchema(
                corridor="hormuz",
                commodity="crude_oil",
                economy="IN",
                named_refinery="Jamnagar",
                volume_lost_mbd=15.0,
                duration_days=30,
                confidence=0.9
            )

def agent_5_synthesize(math_state: dict, variance: bool) -> str:
    prompt = f"""You are a senior geopolitical risk analyst specializing in maritime energy chokepoints. You are provided with a verified mathematical state payload from a pure Python analytics engine. Your task is to write a comprehensive, dense strategic intelligence briefing.
Given this mathematical state: {json.dumps(math_state)}

CRITICAL INSTRUCTIONS:
1. Never reference code logic, variance flags, system templates, or internal variables (e.g., do *not* write 'The variance flag is false' or 'Based on the schema'). Speak with institutional authority.
2. Do not merely state the numbers; explain their structural *implications*.
   * Example: If the engine outputs a landed cost premium of $84.20 via Saudi Aramco, explain the maritime security premium associated with transiting past alternative high-risk littoral zones.
   * Example: If the SPR optimizer recommends Strategy 2 (Phased Substitution), detail the downstream crude rationing protocols the Ministry of Petroleum must enforce to shield domestic manufacturing.
3. Enforce deep macroeconomic context regarding the specific named refinery's crude distillation layout (e.g., why its fluid catalytic cracking units cannot easily digest the alternative light sweet crude substitute without immediate yield degradation). Use the refinery name from the state.
4. HOVER-TO-ARGUE: Wrap ENTIRE factual sentences in [CLAIM id="X" source="Y"] tags. DO NOT wrap just numbers. 
   - BAD: The spot price is [CLAIM id="1" source="EIA"]$78.50[/CLAIM].
   - GOOD: [CLAIM id="1" source="EIA"]The current spot price for WTI crude oil is $78.50.[/CLAIM]
5. Keep it high-impact and strategic. No markdown blocks, just the raw text.
"""
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
            "Accept": "application/json",
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 8192,
            "stream": False
        }
        response = requests.post(NVIDIA_API_URL, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Agent 5 NVIDIA Synthesis failed: {e}. Falling back to Groq...")
        try:
            response = or_client.chat.completions.create(
                model=OR_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e2:
            print(f"Agent 5 Groq Synthesis failed: {e2}")
            return "Synthesis failed. [CLAIM id='err' source='SYS']System offline.[/CLAIM]"
