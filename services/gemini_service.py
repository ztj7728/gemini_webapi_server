"""
Gemini Service
==============

Service layer for integrating with gemini_webapi to handle chat completions.
Translates OpenAI requests to Gemini format and handles both streaming and non-streaming responses.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import AsyncGenerator, Optional

from dotenv import load_dotenv
from gemini_webapi import GeminiClient

from models.openai_models import ChatCompletionRequest, ChatMessage

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class GeminiResponse:
    """Wrapper for Gemini response to match expected interface."""
    
    def __init__(self, text: str, tool_calls=None):
        self.text = text
        self.tool_calls = tool_calls or []


class GeminiService:
    """Service for handling Gemini API interactions."""
    
    def __init__(self):
        self.client: Optional[GeminiClient] = None
        self.proxy = os.getenv("PROXY")  # Read proxy from .env file
        self.secure_1psid = os.getenv("SECURE_1PSID")
        self.secure_1psidts = os.getenv("SECURE_1PSIDTS")
        self.env_path = Path(".env")
        self.monitor_task: Optional[asyncio.Task] = None
        
        if not self.secure_1psid or not self.secure_1psidts:
            raise RuntimeError(
                "Missing SECURE_1PSID or SECURE_1PSIDTS in environment variables. "
                "Please run get_certificate.py first to obtain credentials."
            )
    
    def _update_env_file(self, key: str, value: str) -> None:
        """Insert or replace key=value in the .env file (UTF-8)."""
        lines = []
        updated = False
        if self.env_path.exists():
            with self.env_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        lines.append(f"{key}={value}\n")
                        updated = True
                    else:
                        lines.append(line)
        if not updated:
            lines.append(f"{key}={value}\n")
        self.env_path.write_text("".join(lines), encoding="utf-8")
    
    def _partner_cookie(self, jar: dict[str, str]) -> Optional[str]:
        """Extract partner cookie from cookie jar."""
        for name in ("__Secure-1PSIDTS", "__Secure-1PSIDCC", "Secure_1PSIDTS", "Secure_1PSIDCC"):
            if name in jar:
                return jar[name]
        return None
    
    async def _monitor_cookies(self) -> None:
        """Monitor cookies and update .env file when they change."""
        if not self.client:
            return
        
        last = self._partner_cookie(self.client.cookies)
        logger.info("Starting cookie monitoring for auto-refresh...")
        
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                if not self.client:
                    break
                
                current = self._partner_cookie(self.client.cookies)
                if current and current != last:
                    last = current
                    # Update environment variable
                    os.environ["SECURE_1PSIDTS"] = current
                    # Update .env file
                    self._update_env_file("SECURE_1PSIDTS", current)
                    logger.info(f"[auto-save] Updated .env with new PSIDTS/CC: {current[:32]}...")
                    
            except asyncio.CancelledError:
                logger.info("Cookie monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Error in cookie monitoring: {str(e)}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def initialize(self):
        """Initialize the Gemini client."""
        try:
            logger.info("Initializing Gemini client...")
            logger.info(f"Using PSID: {self.secure_1psid[:20]}...")
            logger.info(f"Using PSIDTS: {self.secure_1psidts[:20]}...")
            
            # Handle proxy configuration
            proxy_config = None
            if self.proxy and self.proxy.lower() not in ["none", "null", ""]:
                proxy_config = self.proxy
            
            logger.info(f"Using proxy: {proxy_config}")
            
            # Initialize GeminiClient with proxy (version 1.13.0 supports proxy again)
            self.client = GeminiClient(
                self.secure_1psid,
                self.secure_1psidts,
                proxy=proxy_config
            )
            
            # Initialize with auto-refresh enabled (same as working code)
            await self.client.init(
                timeout=30,
                auto_close=False,
                close_delay=300,
                auto_refresh=True
            )
            
            logger.info("Gemini client initialized successfully")
            
            # Test the connection (this often triggers the first refresh)
            logger.info("Testing connection with simple query...")
            test_response = await self.client.generate_content("Hello")
            logger.info(f"Gemini connection test successful: {test_response.text[:50]}...")
            
            # Check if cookies were refreshed during initialization and update .env
            current_cookie = self._partner_cookie(self.client.cookies)
            if current_cookie and current_cookie != self.secure_1psidts:
                # Update environment variable
                os.environ["SECURE_1PSIDTS"] = current_cookie
                # Update .env file
                self._update_env_file("SECURE_1PSIDTS", current_cookie)
                logger.info(f"[auto-save] Updated .env with refreshed PSIDTS from initialization: {current_cookie[:32]}...")
            
            # Start cookie monitoring task
            self.monitor_task = asyncio.create_task(self._monitor_cookies())
            logger.info("Started cookie monitoring task for auto-refresh")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Provide helpful error messages
            if "SECURE_1PSIDTS" in str(e):
                logger.error("Credentials appear to be expired. Please run 'python get_certificate.py' to refresh them.")
            elif "Permission denied" in str(e):
                logger.error("Browser cookie access denied. This is normal - the service will use the .env credentials.")
            
            raise RuntimeError(f"Gemini client initialization failed: {str(e)}")
    
    async def cleanup(self):
        """Cleanup the Gemini client."""
        # Stop cookie monitoring task
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("Cookie monitoring task stopped")
        
        # Close Gemini client
        if self.client:
            try:
                await self.client.close()
                logger.info("Gemini client closed successfully")
            except Exception as e:
                logger.error(f"Error closing Gemini client: {str(e)}")
    
    def _extract_text_content(self, content) -> str:
        """Extract text content from either string or content blocks format."""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Handle array of content blocks (OpenAI vision format)
            text_parts = []
            for block in content:
                if hasattr(block, 'type') and hasattr(block, 'text'):
                    # Pydantic model
                    if block.type == "text" and block.text:
                        text_parts.append(block.text)
                elif isinstance(block, dict):
                    # Raw dict
                    if block.get("type") == "text" and block.get("text"):
                        text_parts.append(block["text"])
                    # Handle image_url blocks by describing them
                    elif block.get("type") == "image_url":
                        text_parts.append("[Image content - not supported in text mode]")
            return " ".join(text_parts)
        else:
            return str(content)

    def _convert_messages_to_prompt(self, messages: list[ChatMessage]) -> str:
        """Convert OpenAI messages format to a single prompt for Gemini."""
        prompt_parts = []
        
        for message in messages:
            role = message.role
            content = self._extract_text_content(message.content)
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Add a final prompt for the assistant to respond
        if not prompt_parts or not prompt_parts[-1].startswith("User:"):
            prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)
    
    def _convert_messages_with_functions_to_prompt(self, messages: list[ChatMessage], functions=None, tools=None) -> str:
        """Convert OpenAI messages with function/tool definitions to a single prompt for Gemini."""
        prompt_parts = []
        
        # Add system instruction for tool usage
        tool_instruction = """You are an AI assistant with access to tools. When the user asks you to perform actions that require tools, you MUST use the appropriate tools instead of just describing what to do.

IMPORTANT: When you need to use a tool, respond with the tool call in this exact format:
<tool_call>
<tool_name>function_name</tool_name>
<parameters>
{
  "parameter1": "value1",
  "parameter2": "value2"
}
</parameters>
</tool_call>

Do NOT just describe what you would do - actually use the tools when appropriate."""
        
        prompt_parts.append(f"System: {tool_instruction}")
        
        # Add function/tool definitions to the system context
        if functions:
            prompt_parts.append("\nAvailable Functions:")
            for func in functions:
                func_desc = f"- {func.name}"
                if hasattr(func, 'description') and func.description:
                    func_desc += f": {func.description}"
                if hasattr(func, 'parameters') and func.parameters:
                    import json
                    func_desc += f"\n  Parameters: {json.dumps(func.parameters, indent=2)}"
                prompt_parts.append(func_desc)
            prompt_parts.append("")
        
        if tools:
            prompt_parts.append("\nAvailable Tools:")
            for tool in tools:
                if hasattr(tool, 'function') and tool.function:
                    func = tool.function
                    tool_desc = f"- {func.name}"
                    if hasattr(func, 'description') and func.description:
                        tool_desc += f": {func.description}"
                    if hasattr(func, 'parameters') and func.parameters:
                        import json
                        tool_desc += f"\n  Parameters: {json.dumps(func.parameters, indent=2)}"
                    prompt_parts.append(tool_desc)
            prompt_parts.append("")
        
        # Add regular messages
        for message in messages:
            role = message.role
            content = self._extract_text_content(message.content)
            
            if role == "system":
                # Skip system messages if we already added tool instruction
                if "tool" not in content.lower():
                    prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Add a final prompt for the assistant to respond with tool usage
        prompt_parts.append("Assistant: I'll help you with that. Let me use the appropriate tools to complete your request.")
        
        return "\n\n".join(prompt_parts)
    
    def _parse_tool_calls(self, text: str) -> tuple[str, list]:
        """Parse tool calls from Gemini response text."""
        import re
        import json
        import uuid
        
        tool_calls = []
        remaining_text = text
        
        # Look for tool call patterns
        tool_call_pattern = r'<tool_call>\s*<tool_name>(.*?)</tool_name>\s*<parameters>(.*?)</parameters>\s*</tool_call>'
        matches = re.findall(tool_call_pattern, text, re.DOTALL)
        
        if matches:
            logger.info(f"Found {len(matches)} tool calls in response")
            
            for tool_name, parameters_str in matches:
                try:
                    # Parse parameters JSON
                    parameters = json.loads(parameters_str.strip())
                    
                    # Create OpenAI-compatible tool call
                    tool_call = {
                        "id": f"call_{uuid.uuid4().hex[:24]}",
                        "type": "function",
                        "function": {
                            "name": tool_name.strip(),
                            "arguments": json.dumps(parameters)
                        }
                    }
                    tool_calls.append(tool_call)
                    
                    logger.debug(f"Parsed tool call: {tool_name} with parameters: {parameters}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool call parameters: {e}")
                    logger.error(f"Parameters string: {parameters_str}")
            
            # Remove tool call markup from text
            remaining_text = re.sub(tool_call_pattern, '', text, flags=re.DOTALL)
            remaining_text = remaining_text.strip()
            
            # If no text remains after removing tool calls, add a default message
            if not remaining_text:
                remaining_text = "I'll use the appropriate tools to help you with that."
        
        return remaining_text, tool_calls
    
    def _extract_model_preference(self, model: str) -> str:
        """Extract model preference from OpenAI model name."""
        # Map OpenAI model names to actual Gemini model names
        model_mapping = {
            # OpenAI models -> map to default Gemini model
            "gpt-4": "gemini-2.0-flash",
            "gpt-4-turbo": "gemini-2.0-flash",
            "gpt-3.5-turbo": "gemini-2.0-flash",
            
            # Gemini models -> use actual model names
            "gemini-2.0-flash": "gemini-2.0-flash",
            "gemini-2.0-flash-thinking": "gemini-2.0-flash-thinking",
            "gemini-2.5-flash": "gemini-2.5-flash",
            "gemini-2.5-pro": "gemini-2.5-pro",
            "unspecified": "unspecified"
        }
        
        return model_mapping.get(model, "gemini-2.0-flash")  # Default to gemini-2.0-flash
    
    def _validate_model(self, model: str) -> bool:
        """Validate if the model is supported."""
        supported_models = {
            "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo",
            "gemini-2.0-flash", "gemini-2.0-flash-thinking",
            "gemini-2.5-flash", "gemini-2.5-pro", "unspecified"
        }
        return model in supported_models
    
    async def generate_completion(self, request: ChatCompletionRequest) -> GeminiResponse:
        """Generate a non-streaming completion using Gemini."""
        if not self.client:
            raise RuntimeError("Gemini client not initialized")
        
        try:
            # Log request details for debugging
            logger.info(f"Processing completion request - Model: {request.model}")
            logger.debug(f"Request messages count: {len(request.messages)}")
            for i, msg in enumerate(request.messages):
                content_type = "string" if isinstance(msg.content, str) else "array"
                logger.debug(f"Message {i}: role={msg.role}, content_type={content_type}")
            
            # Validate model
            if not self._validate_model(request.model):
                raise ValueError(f"Unsupported model: {request.model}")
            
            # Convert OpenAI model to Gemini model
            gemini_model = self._extract_model_preference(request.model)
            logger.debug(f"Using Gemini model: {gemini_model} (requested: {request.model})")
            
            # Handle function calls if present
            if request.functions or request.tools:
                logger.info("Function/tool calls detected - adding to prompt context")
                prompt = self._convert_messages_with_functions_to_prompt(request.messages, request.functions, request.tools)
            else:
                # Convert OpenAI messages to Gemini prompt
                prompt = self._convert_messages_to_prompt(request.messages)
            
            logger.debug(f"Sending prompt to Gemini: {prompt[:200]}...")
            
            # Generate response using Gemini with specified model
            response = await self.client.generate_content(prompt, model=gemini_model)
            
            logger.debug(f"Received response from Gemini: {response.text[:100]}...")
            
            return GeminiResponse(response.text)
            
        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            raise
    
    async def generate_streaming_completion(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        """Generate a streaming completion using Gemini."""
        if not self.client:
            raise RuntimeError("Gemini client not initialized")
        
        try:
            # Log request details for debugging
            logger.info(f"Processing streaming completion request - Model: {request.model}")
            logger.debug(f"Request messages count: {len(request.messages)}")
            for i, msg in enumerate(request.messages):
                content_type = "string" if isinstance(msg.content, str) else "array"
                logger.debug(f"Message {i}: role={msg.role}, content_type={content_type}")
            
            # Validate model
            if not self._validate_model(request.model):
                raise ValueError(f"Unsupported model: {request.model}")
            
            # Convert OpenAI model to Gemini model
            gemini_model = self._extract_model_preference(request.model)
            logger.debug(f"Using Gemini model: {gemini_model} (requested: {request.model})")
            
            # Handle function calls if present
            if request.functions or request.tools:
                logger.info("Function/tool calls detected in streaming - adding to prompt context")
                prompt = self._convert_messages_with_functions_to_prompt(request.messages, request.functions, request.tools)
            else:
                # Convert OpenAI messages to Gemini prompt
                prompt = self._convert_messages_to_prompt(request.messages)
            
            logger.debug(f"Sending streaming prompt to Gemini: {prompt[:200]}...")
            
            # For now, we'll simulate streaming by generating the full response
            # and then yielding it in chunks. In the future, this could be enhanced
            # to use actual streaming if gemini_webapi supports it.
            response = await self.client.generate_content(prompt, model=gemini_model)
            
            # Split response into chunks for streaming
            text = response.text
            chunk_size = 15  # Slightly larger chunks to reduce boundary issues
            
            logger.debug(f"Streaming response text length: {len(text)}")
            logger.debug(f"Response text preview: {text[:100]}...")
            
            chunk_count = 0
            last_position = 0
            
            # Use a more intelligent chunking approach
            while last_position < len(text):
                # Calculate chunk end position
                chunk_end = min(last_position + chunk_size, len(text))
                chunk = text[last_position:chunk_end]
                
                # Skip empty chunks
                if not chunk:
                    break
                
                chunk_count += 1
                logger.debug(f"Yielding chunk {chunk_count}: '{chunk}'")
                yield chunk
                
                # Move to next position (no overlap)
                last_position = chunk_end
                
                # Small delay to simulate streaming
                await asyncio.sleep(0.05)
            
            logger.debug(f"Completed streaming {chunk_count} chunks")
                
        except Exception as e:
            logger.error(f"Error generating streaming completion: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            raise
    
    async def health_check(self) -> bool:
        """Check if the Gemini service is healthy."""
        if not self.client:
            return False
        
        try:
            # Simple health check by sending a minimal request
            response = await self.client.generate_content("Hi")
            return bool(response and response.text)
        except Exception as e:
            logger.error(f"Gemini health check failed: {str(e)}")
            return False