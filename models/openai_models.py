"""
OpenAI-compatible Pydantic models for request/response schemas.
"""

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    """A content block for multi-modal messages."""
    type: str = Field(..., description="The type of content (text, image_url)")
    text: Optional[str] = Field(None, description="Text content")
    image_url: Optional[Dict[str, Any]] = Field(None, description="Image URL object")


class ChatMessage(BaseModel):
    """A chat message in the conversation."""
    role: str = Field(..., description="The role of the message author (user, assistant, system)")
    content: Union[str, List[ContentBlock]] = Field(..., description="The content of the message - can be string or array of content blocks")
    name: Optional[str] = Field(None, description="The name of the author of this message")
    function_call: Optional[Dict[str, Any]] = Field(None, description="Function call information")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls information")


class FunctionDefinition(BaseModel):
    """Function definition for function calling."""
    name: str = Field(..., description="Function name")
    description: Optional[str] = Field(None, description="Function description")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Function parameters schema")


class ToolDefinition(BaseModel):
    """Tool definition for tool calling."""
    type: str = Field(..., description="Tool type (e.g., 'function')")
    function: Optional[FunctionDefinition] = Field(None, description="Function definition")


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions."""
    model: str = Field(..., description="ID of the model to use")
    messages: List[ChatMessage] = Field(..., description="List of messages in the conversation")
    stream: Optional[bool] = Field(False, description="Whether to stream back partial progress")
    temperature: Optional[float] = Field(1.0, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum number of tokens to generate")
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="Presence penalty")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    user: Optional[str] = Field(None, description="Unique identifier for the end-user")
    functions: Optional[List[FunctionDefinition]] = Field(None, description="Available functions (deprecated)")
    function_call: Optional[Union[str, Dict[str, str]]] = Field(None, description="Function call control (deprecated)")
    tools: Optional[List[ToolDefinition]] = Field(None, description="Available tools")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(None, description="Tool choice control")
    stream_options: Optional[Dict[str, Any]] = Field(None, description="Streaming options")


class ChatCompletionMessage(BaseModel):
    """A message in a chat completion response."""
    role: str = Field(..., description="The role of the message author")
    content: Optional[str] = Field(None, description="The content of the message")
    name: Optional[str] = Field(None, description="The name of the author of this message")
    function_call: Optional[Dict[str, Any]] = Field(None, description="Function call information")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls information")


class ChatCompletionChoice(BaseModel):
    """A choice in a chat completion response."""
    index: int = Field(..., description="The index of the choice")
    message: ChatCompletionMessage = Field(..., description="The message content")
    finish_reason: Optional[str] = Field(None, description="Reason the model stopped generating")


class ChatCompletionUsage(BaseModel):
    """Usage statistics for a chat completion."""
    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(..., description="Number of tokens in the completion")
    total_tokens: int = Field(..., description="Total number of tokens used")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completions."""
    id: str = Field(..., description="Unique identifier for the completion")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used for the completion")
    choices: List[ChatCompletionChoice] = Field(..., description="List of completion choices")
    usage: ChatCompletionUsage = Field(..., description="Usage statistics")


class ChatCompletionStreamDelta(BaseModel):
    """Delta object for streaming chat completions."""
    role: Optional[str] = Field(None, description="The role of the message author")
    content: Optional[str] = Field(None, description="The content of the message")


class ChatCompletionStreamChoice(BaseModel):
    """A choice in a streaming chat completion response."""
    index: int = Field(..., description="The index of the choice")
    delta: ChatCompletionStreamDelta = Field(..., description="The delta content")
    finish_reason: Optional[str] = Field(None, description="Reason the model stopped generating")


class ChatCompletionStreamResponse(BaseModel):
    """Response model for streaming chat completions."""
    id: str = Field(..., description="Unique identifier for the completion")
    object: str = Field("chat.completion.chunk", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used for the completion")
    choices: List[ChatCompletionStreamChoice] = Field(..., description="List of completion choices")


class ModelInfo(BaseModel):
    """Information about a model."""
    id: str = Field(..., description="Model identifier")
    object: str = Field("model", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    owned_by: str = Field(..., description="Organization that owns the model")


class ModelsResponse(BaseModel):
    """Response model for listing models."""
    object: str = Field("list", description="Object type")
    data: List[ModelInfo] = Field(..., description="List of available models")


class ErrorDetail(BaseModel):
    """Error detail information."""
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    param: Optional[str] = Field(None, description="Parameter that caused the error")
    code: str = Field(..., description="Error code")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: ErrorDetail = Field(..., description="Error details")


class UserContext(BaseModel):
    """User context from authentication."""
    user_id: str = Field(..., description="User identifier")
    api_key_id: str = Field(..., description="API key identifier")
    permissions: List[str] = Field(default_factory=list, description="User permissions")