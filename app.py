"""
OpenAI-Compatible API Server
============================

FastAPI server that provides OpenAI-compatible endpoints using gemini_webapi as the backend.
Implements /v1/chat/completions and /v1/models endpoints with proper authentication.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.openai_models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionStreamResponse,
    ModelsResponse,
    ErrorResponse
)
from services.gemini_service import GeminiService
from auth.auth_service import AuthService
from utils.logging_config import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging()

# Global services
gemini_service: Optional[GeminiService] = None
auth_service: Optional[AuthService] = None

# Security scheme
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global gemini_service, auth_service
    
    logger.info("Starting OpenAI-Compatible API Server...")
    
    # Initialize services
    auth_service = AuthService()
    gemini_service = GeminiService()
    
    # Initialize Gemini client
    await gemini_service.initialize()
    
    logger.info("Server startup complete")
    
    yield
    
    # Cleanup
    logger.info("Shutting down server...")
    if gemini_service:
        await gemini_service.cleanup()
    logger.info("Server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="OpenAI-Compatible API",
    description="OpenAI-compatible REST API powered by Google Gemini",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Authenticate user using Bearer token."""
    if not auth_service:
        raise HTTPException(status_code=503, detail="Authentication service not available")
    
    user_context = await auth_service.authenticate(credentials.credentials)
    if not user_context:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid API key provided",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_api_key"
                }
            }
        )
    return user_context


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "openai-compatible-api"
    }


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models(user=Depends(get_current_user)):
    """List available models."""
    return ModelsResponse(
        object="list",
        data=[
            {
                "id": "gemini-2.0-flash",
                "object": "model",
                "created": 1677610602,
                "owned_by": "google"
            },
            {
                "id": "gemini-2.0-flash-thinking",
                "object": "model",
                "created": 1677610602,
                "owned_by": "google"
            },
            {
                "id": "gemini-2.5-flash",
                "object": "model",
                "created": 1677610602,
                "owned_by": "google"
            },
            {
                "id": "gemini-2.5-pro",
                "object": "model",
                "created": 1677610602,
                "owned_by": "google"
            },
            {
                "id": "unspecified",
                "object": "model",
                "created": 1677610602,
                "owned_by": "google"
            }
        ]
    )


@app.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    user=Depends(get_current_user)
):
    """Create a chat completion, optionally streaming."""
    if not gemini_service:
        raise HTTPException(status_code=503, detail="Gemini service not available")
    
    try:
        # Validate model
        if not gemini_service._validate_model(request.model):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "message": f"The model '{request.model}' does not exist",
                        "type": "invalid_request_error",
                        "param": "model",
                        "code": "model_not_found"
                    }
                }
            )
        
        if request.stream:
            return StreamingResponse(
                stream_chat_completion(request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            return await create_non_streaming_completion(request)
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Error in chat completion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error",
                    "param": None,
                    "code": "internal_error"
                }
            }
        )


async def create_non_streaming_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Create a non-streaming chat completion."""
    # Generate response using Gemini
    response = await gemini_service.generate_completion(request)
    
    # Create OpenAI-compatible response
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
    
    return ChatCompletionResponse(
        id=completion_id,
        object="chat.completion",
        created=int(time.time()),
        model=request.model,
        choices=[
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.text
                },
                "finish_reason": "stop"
            }
        ],
        usage={
            "prompt_tokens": len(str(request.messages)) // 4,  # Rough estimate
            "completion_tokens": len(response.text) // 4,  # Rough estimate
            "total_tokens": (len(str(request.messages)) + len(response.text)) // 4
        }
    )


async def stream_chat_completion(request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
    """Stream chat completion responses."""
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
    
    try:
        logger.info(f"Starting streaming completion for request: {completion_id}")
        chunk_count = 0
        stream_started = False
        
        # Generate streaming response using Gemini
        async for chunk in gemini_service.generate_streaming_completion(request):
            if not chunk:  # Skip empty chunks
                continue
            
            if not stream_started:
                logger.info(f"First chunk received for {completion_id}")
                stream_started = True
                
            chunk_count += 1
            logger.debug(f"Processing stream chunk {chunk_count}: '{chunk}'")
            
            # Create OpenAI-compatible streaming response
            stream_response = ChatCompletionStreamResponse(
                id=completion_id,
                object="chat.completion.chunk",
                created=int(time.time()),
                model=request.model,
                choices=[
                    {
                        "index": 0,
                        "delta": {
                            "content": chunk
                        },
                        "finish_reason": None
                    }
                ]
            )
            
            # Format as Server-Sent Event
            sse_data = f"data: {stream_response.model_dump_json()}\n\n"
            logger.debug(f"Yielding SSE data chunk {chunk_count}")
            yield sse_data
        
        if not stream_started:
            logger.warning(f"No chunks were generated for request: {completion_id}")
        
        logger.info(f"Completed streaming {chunk_count} chunks for request: {completion_id}")
        
        # Send final chunk
        logger.info(f"Sending final chunk for request: {completion_id}")
        final_response = ChatCompletionStreamResponse(
            id=completion_id,
            object="chat.completion.chunk",
            created=int(time.time()),
            model=request.model,
            choices=[
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        )
        
        final_sse = f"data: {final_response.model_dump_json()}\n\n"
        logger.debug(f"Final SSE data: {final_sse}")
        yield final_sse
        
        done_sse = "data: [DONE]\n\n"
        logger.debug(f"DONE SSE data: {done_sse}")
        yield done_sse
        
        logger.info(f"Streaming completion finished for request: {completion_id}")
        
    except Exception as e:
        logger.error(f"Error in streaming completion for {completion_id}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        error_response = {
            "error": {
                "message": f"Stream error: {str(e)}",
                "type": "internal_error",
                "param": None,
                "code": "internal_error"
            }
        }
        error_sse = f"data: {json.dumps(error_response)}\n\n"
        logger.error(f"Yielding error SSE: {error_sse}")
        yield error_sse


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )