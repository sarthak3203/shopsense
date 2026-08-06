"""
M2 — Single Agent With Tools.
Runs a standard tool-calling loop: send the query + tool schemas to the
model, execute whatever tools it asks for, feed results back, repeat
until the model gives a final answer (or we hit max_turns as a safety cap).
"""

import json
import os

from dotenv import load_dotenv
from litellm import completion

from src.tools import DISPATCH, TOOLS

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "groq/openai/gpt-oss-120b")

SYSTEM_PROMPT = (
    "You are the Order-Actions agent for an e-commerce support system. "
    "You have tools to look up orders, check shipping status, calculate "
    "refund eligibility, and execute refunds/replacements. "
    "Always look up or calculate before executing an action. "
    "If an order ID doesn't exist, say so clearly rather than guessing. "
    "Be concise and factual in your final answer."
)


def run_agent(user_query: str, max_turns: int = 5) -> dict:
    """
    Returns {"final_answer": str, "tool_calls_made": [ {name, args, result}, ... ]}
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    tool_trace = []

    for _ in range(max_turns):
        response = completion(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return {"final_answer": msg.content, "tool_calls_made": tool_trace}

        messages.append(msg.model_dump())

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = DISPATCH[name](args)

            tool_trace.append({"name": name, "args": args, "result": result})

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return {"final_answer": "Max tool-call turns reached without a final answer.",
            "tool_calls_made": tool_trace}