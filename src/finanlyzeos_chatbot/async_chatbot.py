"""Async/await implementation of the chatbot for maximum performance."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class AsyncChatbotPipeline:
    """High-performance async chatbot pipeline."""
    
    def __init__(self, chatbot):
        self.chatbot = chatbot
        self.executor = None  # Will be set by the async runtime
    
    async def process_query_async(
        self,
        user_input: str,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        Process a query using async/await for maximum performance.
        
        This method parallelizes all I/O operations for dramatic speed improvements.
        """
        start_time = time.time()
        
        def emit(stage: str, detail: str) -> None:
            if progress_callback:
                progress_callback(stage, detail)
        
        try:
            emit("async_start", "🚀 Starting async processing pipeline")
            
            # Step 1: Parallel initialization
            emit("parallel_init", "Initializing components in parallel")
            
            # Run multiple initialization tasks in parallel
            init_tasks = [
                self._async_classify_query(user_input),
                self._async_detect_tickers(user_input),
                self._async_build_document_context(user_input),
                self._async_check_cache(user_input),
            ]
            
            (complexity_data, tickers, doc_context, cached_response) = await asyncio.gather(*init_tasks)
            
            # If we have a cached response, return it immediately
            if cached_response:
                emit("cache_hit", "✅ Using cached response")
                return cached_response
            
            emit("parallel_init_complete", f"Initialization complete in {time.time() - start_time:.2f}s")
            
            # Step 2: Parallel data retrieval
            if complexity_data["complexity"] == "simple":
                # Fast path for simple queries
                emit("fast_path", "Using fast path for simple query")
                response = await self._async_handle_simple_query(user_input, tickers)
                if response:
                    emit("fast_path_complete", f"Fast path complete in {time.time() - start_time:.2f}s")
                    return response
            
            # Step 3: Parallel RAG retrieval (for complex queries)
            emit("parallel_retrieval", "Starting parallel RAG retrieval")
            
            retrieval_tasks = []
            
            # SQL data retrieval
            retrieval_tasks.append(self._async_retrieve_sql_data(tickers))
            
            # Semantic search (if needed)
            if tickers:
                retrieval_tasks.append(self._async_retrieve_semantic_data(user_input, tickers))
            
            # Document context (if available)
            if doc_context:
                retrieval_tasks.append(self._async_process_document_context(doc_context))
            
            # Execute all retrievals in parallel
            retrieval_results = await asyncio.gather(*retrieval_tasks, return_exceptions=True)
            
            # Combine results
            sql_data = retrieval_results[0] if len(retrieval_results) > 0 else None
            semantic_data = retrieval_results[1] if len(retrieval_results) > 1 else None
            doc_data = retrieval_results[2] if len(retrieval_results) > 2 else None
            
            emit("parallel_retrieval_complete", f"Retrieval complete in {time.time() - start_time:.2f}s")
            
            # Step 4: Build context and generate response
            emit("context_building", "Building final context")
            
            context = await self._async_build_context(
                user_input, sql_data, semantic_data, doc_data
            )
            
            emit("llm_generation", "Generating LLM response")
            response = await self._async_generate_llm_response(context, user_input)
            
            # Step 5: Post-processing in parallel
            emit("post_processing", "Post-processing response")
            
            post_tasks = [
                self._async_cache_response(user_input, response),
                self._async_log_interaction(user_input, response),
            ]
            
            await asyncio.gather(*post_tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            emit("async_complete", f"✅ Async processing complete in {total_time:.2f}s")
            
            return response
            
        except Exception as e:
            LOGGER.error(f"Async pipeline error: {e}", exc_info=True)
            emit("async_error", f"❌ Error in async pipeline: {str(e)}")
            
            # Fallback to synchronous processing
            emit("fallback_sync", "Falling back to synchronous processing")
            return self.chatbot.ask(user_input, progress_callback=progress_callback)
    
    async def _async_classify_query(self, user_input: str) -> Dict[str, Any]:
        """Classify query asynchronously."""
        loop = asyncio.get_event_loop()
        
        def classify():
            from .query_classifier import classify_query
            complexity, query_type, metadata = classify_query(user_input)
            return {
                "complexity": complexity.value,
                "query_type": query_type.value,
                "metadata": metadata
            }
        
        return await loop.run_in_executor(None, classify)
    
    async def _async_detect_tickers(self, user_input: str) -> List[str]:
        """Detect tickers asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.chatbot._detect_tickers, user_input)
    
    async def _async_build_document_context(self, user_input: str) -> Optional[str]:
        """Build document context asynchronously."""
        loop = asyncio.get_event_loop()
        
        def build_context():
            try:
                from .document_context import build_uploaded_document_context
                return build_uploaded_document_context(
                    user_input,
                    getattr(self.chatbot.conversation, "conversation_id", None),
                    Path(self.chatbot.settings.database_path),
                )
            except Exception:
                return None
        
        return await loop.run_in_executor(None, build_context)
    
    async def _async_check_cache(self, user_input: str) -> Optional[str]:
        """Check cache asynchronously."""
        loop = asyncio.get_event_loop()
        
        def check_cache():
            try:
                canonical_prompt = self.chatbot._canonical_prompt(user_input, None)
                if self.chatbot._should_cache_prompt(canonical_prompt):
                    cached_entry = self.chatbot._get_cached_reply(canonical_prompt)
                    return cached_entry.reply if cached_entry else None
            except Exception:
                pass
            return None
        
        return await loop.run_in_executor(None, check_cache)
    
    async def _async_handle_simple_query(self, user_input: str, tickers: List[str]) -> Optional[str]:
        """Handle simple queries asynchronously."""
        loop = asyncio.get_event_loop()
        
        def handle_simple():
            try:
                query_metadata = {"tickers": tickers}
                return self.chatbot._handle_simple_factual_query(user_input, query_metadata)
            except Exception:
                return None
        
        return await loop.run_in_executor(None, handle_simple)
    
    async def _async_retrieve_sql_data(self, tickers: List[str]) -> Optional[Dict[str, Any]]:
        """Retrieve SQL data asynchronously."""
        loop = asyncio.get_event_loop()
        
        def retrieve_sql():
            try:
                if not tickers:
                    return None
                
                # Get metrics for all tickers in parallel
                all_metrics = []
                for ticker in tickers:
                    try:
                        metrics = self.chatbot.analytics_engine.get_metrics(ticker)
                        all_metrics.extend(metrics)
                    except Exception as e:
                        LOGGER.debug(f"Failed to get metrics for {ticker}: {e}")
                
                return {"metrics": all_metrics, "tickers": tickers}
            except Exception as e:
                LOGGER.debug(f"SQL retrieval failed: {e}")
                return None
        
        return await loop.run_in_executor(None, retrieve_sql)
    
    async def _async_retrieve_semantic_data(self, query: str, tickers: List[str]) -> Optional[Dict[str, Any]]:
        """Retrieve semantic data asynchronously."""
        loop = asyncio.get_event_loop()
        
        def retrieve_semantic():
            try:
                # Use RAG orchestrator if available
                rag_orchestrator = self.chatbot._get_rag_orchestrator()
                if rag_orchestrator:
                    prompt, result, metadata = rag_orchestrator.process_query(
                        query, self.chatbot.conversation.conversation_id
                    )
                    return {"prompt": prompt, "result": result, "metadata": metadata}
                else:
                    # Fallback to basic RAG context
                    context = self.chatbot._build_rag_context(query)
                    return {"context": context}
            except Exception as e:
                LOGGER.debug(f"Semantic retrieval failed: {e}")
                return None
        
        return await loop.run_in_executor(None, retrieve_semantic)
    
    async def _async_process_document_context(self, doc_context: str) -> Optional[Dict[str, Any]]:
        """Process document context asynchronously."""
        # Document context is already built, just return it
        return {"document_context": doc_context}
    
    async def _async_build_context(
        self, 
        user_input: str, 
        sql_data: Optional[Dict[str, Any]], 
        semantic_data: Optional[Dict[str, Any]], 
        doc_data: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Build final context asynchronously."""
        loop = asyncio.get_event_loop()
        
        def build_context():
            try:
                # Combine all data sources into a comprehensive context
                context_parts = []
                
                if sql_data and sql_data.get("metrics"):
                    # Format SQL metrics
                    metrics_text = self._format_metrics_context(sql_data["metrics"])
                    context_parts.append(f"## Financial Metrics\n{metrics_text}")
                
                if semantic_data:
                    if "prompt" in semantic_data:
                        context_parts.append(semantic_data["prompt"])
                    elif "context" in semantic_data:
                        context_parts.append(semantic_data["context"])
                
                if doc_data and doc_data.get("document_context"):
                    context_parts.append(f"## Document Context\n{doc_data['document_context']}")
                
                return "\n\n".join(context_parts) if context_parts else None
            except Exception as e:
                LOGGER.debug(f"Context building failed: {e}")
                return None
        
        return await loop.run_in_executor(None, build_context)
    
    async def _async_generate_llm_response(self, context: Optional[str], user_input: str) -> str:
        """Generate LLM response asynchronously."""
        loop = asyncio.get_event_loop()
        
        def generate_response():
            try:
                if context:
                    return self.chatbot._generate_llm_reply(context, user_input)
                else:
                    return self.chatbot._generate_llm_reply(None, user_input)
            except Exception as e:
                LOGGER.error(f"LLM generation failed: {e}")
                return f"I apologize, but I encountered an error processing your request: {str(e)}"
        
        return await loop.run_in_executor(None, generate_response)
    
    async def _async_cache_response(self, user_input: str, response: str) -> None:
        """Cache response asynchronously."""
        loop = asyncio.get_event_loop()
        
        def cache_response():
            try:
                canonical_prompt = self.chatbot._canonical_prompt(user_input, None)
                if self.chatbot._should_cache_prompt(canonical_prompt):
                    self.chatbot._store_cached_reply(canonical_prompt, response, {})
            except Exception as e:
                LOGGER.debug(f"Response caching failed: {e}")
        
        await loop.run_in_executor(None, cache_response)
    
    async def _async_log_interaction(self, user_input: str, response: str) -> None:
        """Log interaction asynchronously."""
        loop = asyncio.get_event_loop()
        
        def log_interaction():
            try:
                from . import database
                from datetime import datetime
                
                database.log_message(
                    self.chatbot.settings.database_path,
                    self.chatbot.conversation.conversation_id,
                    role="assistant",
                    content=response,
                    created_at=datetime.utcnow(),
                )
            except Exception as e:
                LOGGER.debug(f"Interaction logging failed: {e}")
        
        await loop.run_in_executor(None, log_interaction)
    
    def _format_metrics_context(self, metrics: List[Any]) -> str:
        """Format metrics for context."""
        if not metrics:
            return "No metrics available."
        
        formatted = []
        for metric in metrics[:10]:  # Limit to top 10 metrics
            try:
                ticker = getattr(metric, 'ticker', 'Unknown')
                metric_name = getattr(metric, 'metric', 'Unknown')
                value = getattr(metric, 'value', None)
                period = getattr(metric, 'period', 'latest')
                
                if value is not None:
                    formatted.append(f"- {ticker} {metric_name}: {value} ({period})")
            except Exception:
                continue
        
        return "\n".join(formatted) if formatted else "No valid metrics found."


# Integration function for existing chatbot
def add_async_support(chatbot) -> AsyncChatbotPipeline:
    """Add async support to an existing chatbot."""
    return AsyncChatbotPipeline(chatbot)
