"""Anthropic Claude LLM client with tool-calling support."""

import os
import json
from dataclasses import dataclass, field
from typing import Optional

import anthropic
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
HAIKU_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

    def to_message(self) -> dict:
        """Convert to Anthropic message format for conversation history."""
        content = []
        if self.text:
            content.append({"type": "text", "text": self.text})
        for tc in self.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments,
            })
        return {"role": "assistant", "content": content}


class ClaudeLLM:
    """Thin wrapper around Anthropic SDK for the ReAct agent."""

    def __init__(self, api_key: str = None, model: str = None):
        self.client = anthropic.Anthropic(api_key=api_key or ANTHROPIC_API_KEY)
        self.model = model or MODEL

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        tool_choice: str = "auto",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send messages to Claude and return response with optional tool calls.

        Accepts OpenAI-style tool schemas and converts to Anthropic format.
        """
        # Extract system prompt from messages
        system_prompt = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg["role"] == "tool":
                # Convert tool result to Anthropic format
                chat_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg["tool_call_id"],
                        "content": msg["content"],
                    }],
                })
            else:
                chat_messages.append(msg)

        # Convert OpenAI-style tool schemas to Anthropic format
        anthropic_tools = None
        if tools:
            anthropic_tools = []
            for tool in tools:
                func = tool.get("function", tool)
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func["description"],
                    "input_schema": func["parameters"],
                })

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
            if tool_choice == "auto":
                kwargs["tool_choice"] = {"type": "auto"}
            elif tool_choice == "any":
                kwargs["tool_choice"] = {"type": "any"}

        # Anthropic SDK is sync — run in thread for async compat
        import asyncio
        response = await asyncio.to_thread(self.client.messages.create, **kwargs)

        # Parse response
        result = LLMResponse(
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        for block in response.content:
            if block.type == "text":
                result.text += block.text
            elif block.type == "tool_use":
                result.tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                ))

        return result
