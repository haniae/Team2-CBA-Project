"""Streaming response implementation for real-time chatbot feedback."""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator, Dict, Any, Optional, Callable
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from starlette.responses import Response

LOGGER = logging.getLogger(__name__)


class StreamingChatbot:
    """Wrapper for chatbot that supports streaming responses."""
    
    def __init__(self, chatbot):
        self.chatbot = chatbot
        self.current_stream_data = {}
    
    async def stream_response(
        self, 
        user_input: str, 
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chatbot response in real-time chunks."""
        
        # Send immediate acknowledgment
        yield self._format_stream_chunk("status", "🔍 Analyzing your query...")
        
        # Track progress through streaming callback
        progress_data = {"stage": "", "detail": "", "timestamp": time.time()}
        
        def progress_callback(stage: str, detail: str) -> None:
            progress_data["stage"] = stage
            progress_data["detail"] = detail
            progress_data["timestamp"] = time.time()
        
        # Start processing in background
        try:
            # Send early progress updates
            yield self._format_stream_chunk("progress", "📊 Gathering financial data...")
            
            # Call the chatbot with streaming callback
            response = self.chatbot.ask(
                user_input, 
                progress_callback=progress_callback
            )
            
            # Stream the response in chunks
            if response:
                # Send response in chunks for better perceived performance
                chunk_size = 50  # words per chunk
                words = response.split()
                
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i + chunk_size])
                    yield self._format_stream_chunk("content", chunk)
                    
                    # Small delay to make streaming visible
                    await self._async_sleep(0.1)
                
                # Send completion signal
                yield self._format_stream_chunk("complete", "✅ Response complete")
            else:
                yield self._format_stream_chunk("error", "❌ No response generated")
                
        except Exception as e:
            LOGGER.error(f"Streaming error: {e}", exc_info=True)
            yield self._format_stream_chunk("error", f"❌ Error: {str(e)}")
    
    def _format_stream_chunk(self, chunk_type: str, content: str) -> str:
        """Format a streaming chunk as JSON."""
        chunk_data = {
            "type": chunk_type,
            "content": content,
            "timestamp": time.time()
        }
        return f"data: {json.dumps(chunk_data)}\n\n"
    
    async def _async_sleep(self, duration: float) -> None:
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(duration)


def add_streaming_endpoints(app: FastAPI, chatbot_factory: Callable):
    """Add streaming endpoints to FastAPI app."""
    
    @app.get("/chat/stream")
    async def stream_chat(
        prompt: str,
        conversation_id: Optional[str] = None
    ) -> StreamingResponse:
        """Stream chatbot response in real-time."""
        
        if not prompt.strip():
            return Response("Prompt cannot be empty", status_code=400)
        
        # Create chatbot instance
        bot = chatbot_factory(conversation_id)
        streaming_bot = StreamingChatbot(bot)
        
        # Return streaming response
        return StreamingResponse(
            streaming_bot.stream_response(prompt, conversation_id),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
    
    @app.post("/chat/stream")
    async def stream_chat_post(request: Dict[str, Any]) -> StreamingResponse:
        """Stream chatbot response via POST."""
        
        prompt = request.get("prompt", "").strip()
        conversation_id = request.get("conversation_id")
        
        if not prompt:
            return Response("Prompt cannot be empty", status_code=400)
        
        # Create chatbot instance  
        bot = chatbot_factory(conversation_id)
        streaming_bot = StreamingChatbot(bot)
        
        # Return streaming response
        return StreamingResponse(
            streaming_bot.stream_response(prompt, conversation_id),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache", 
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
