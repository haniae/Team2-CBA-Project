"""
RAG Prompt Template Module

Implements RAG-style prompting as shown in Lecture 2:
"Read the following documents... Use them to answer the question: ..."

This module formats retrieved context into RAG-style prompts that explicitly
instruct the LLM to use only the retrieved documents.
"""

from __future__ import annotations

from typing import List, Dict, Any
from .rag_retriever import RetrievalResult, RetrievedDocument


def build_rag_prompt(
    user_query: str,
    retrieval_result: RetrievalResult,
    *,
    include_instructions: bool = True,
    confidence_instruction: Optional[str] = None,
    grounded_instruction: Optional[str] = None,
) -> str:
    """
    Build RAG-style prompt following Lecture 2 format.
    
    Format matches the lecture's example:
    "Read the following documents... Use them to answer the question: ..."
    
    Args:
        user_query: Original user question
        retrieval_result: Retrieved context from RAG Retriever
        include_instructions: Whether to include RAG instructions
        
    Returns:
        Formatted prompt for LLM Generator
    """
    sections = []
    
    # RAG-style header (matching Lecture 2 format)
    if include_instructions:
        sections.append(
            "╔═══════════════════════════════════════════════════════════════════════════════╗\n"
            "║                    RAG CONTEXT - USE ONLY THE DATA BELOW                      ║\n"
            "╚═══════════════════════════════════════════════════════════════════════════════╝\n\n"
            "📋 **INSTRUCTIONS**:\n"
            "Read the following retrieved documents, metrics, and data excerpts.\n"
            "Use ONLY this information to answer the user's question.\n"
            "Cite sources with URLs and filenames where provided.\n"
            "Do NOT use information from your training data that contradicts the retrieved data.\n"
        )
        
        # Add confidence instruction if provided
        if confidence_instruction:
            sections.append(f"\n🎯 **RETRIEVAL CONFIDENCE**: {confidence_instruction}\n")
        
        # Add grounded decision instruction if provided
        if grounded_instruction:
            sections.append(f"\n{grounded_instruction}\n")
        
        sections.append("\n═══════════════════════════════════════════════════════════════════════════════\n\n")
    
    # Section 1: Deterministic Metrics (SQL retrieval)
    if retrieval_result.metrics:
        sections.append("📊 **FINANCIAL METRICS** (from database):\n")
        sections.append(_format_metrics(retrieval_result.metrics))
        sections.append("\n")
    
    # Section 2: SEC Filing Narratives (semantic search)
    if retrieval_result.sec_narratives:
        sections.append("📄 **SEC FILING EXCERPTS** (semantic search results):\n")
        sections.append(_format_sec_narratives(retrieval_result.sec_narratives))
        sections.append("\n")
    
    # Section 3: Uploaded Documents (semantic search)
    if retrieval_result.uploaded_docs:
        sections.append("📎 **UPLOADED DOCUMENTS** (semantic search results):\n")
        sections.append(_format_uploaded_docs(retrieval_result.uploaded_docs))
        sections.append("\n")
    
    # Section 4: Additional context
    if retrieval_result.macro_data:
        sections.append("🌍 **MACROECONOMIC DATA**:\n")
        sections.append(_format_dict(retrieval_result.macro_data))
        sections.append("\n")
    
    if retrieval_result.portfolio_data:
        sections.append("💼 **PORTFOLIO DATA**:\n")
        sections.append(_format_dict(retrieval_result.portfolio_data))
        sections.append("\n")
    
    if retrieval_result.ml_forecasts:
        sections.append("🔮 **ML FORECASTS**:\n")
        sections.append(_format_dict(retrieval_result.ml_forecasts))
        sections.append("\n")
    
    # Add retrieval confidence if available
    if retrieval_result.overall_confidence is not None:
        confidence_pct = int(retrieval_result.overall_confidence * 100)
        sections.append(
            f"\n📊 **RETRIEVAL CONFIDENCE**: {confidence_pct}% "
            f"({'High' if retrieval_result.overall_confidence >= 0.7 else 'Medium' if retrieval_result.overall_confidence >= 0.4 else 'Low'})\n"
        )
    
    # RAG-style query instruction (matching Lecture 2)
    sections.append(
        "═══════════════════════════════════════════════════════════════════════════════\n\n"
        "❓ **USER QUESTION**:\n"
        f"{user_query}\n\n"
        "📝 **YOUR TASK**:\n"
        "Using ONLY the retrieved documents, metrics, and data above, answer the user's question.\n"
        "Cite specific sources (SEC filing URLs, document filenames, metric periods) in your response.\n"
    )
    
    # Add confidence-based instruction
    if retrieval_result.overall_confidence is not None:
        if retrieval_result.overall_confidence < 0.35:
            sections.append(
                "⚠️ **LOW CONFIDENCE WARNING**: The retrieved information has limited relevance. "
                "Be cautious and explicit about information gaps. If the data doesn't contain enough "
                "information, say so explicitly.\n"
            )
        elif retrieval_result.overall_confidence < 0.7:
            sections.append(
                "ℹ️ **MODERATE CONFIDENCE**: The retrieved information is moderately relevant. "
                "Provide a helpful answer but acknowledge any uncertainties.\n"
            )
    
    sections.append(
        "If the retrieved data doesn't contain enough information, say so explicitly.\n"
    )
    
    return "\n".join(sections)


def _format_metrics(metrics: List[Dict[str, Any]]) -> str:
    """Format metrics for RAG prompt."""
    lines = []
    current_ticker = None
    
    for metric in metrics:
        ticker = metric.get("ticker", "Unknown")
        if ticker != current_ticker:
            lines.append(f"\n**{ticker}**:")
            current_ticker = ticker
        
        metric_name = metric.get("metric", "unknown")
        value = metric.get("value")
        period = metric.get("period", "N/A")
        source = metric.get("source", "database")
        
        # Format value
        if isinstance(value, (int, float)):
            if abs(value) >= 1e9:
                value_str = f"${value/1e9:.2f}B"
            elif abs(value) >= 1e6:
                value_str = f"${value/1e6:.2f}M"
            else:
                value_str = f"${value:,.0f}"
        else:
            value_str = str(value)
        
        lines.append(f"  - {metric_name}: {value_str} ({period}) [Source: {source}]")
    
    return "\n".join(lines)


def _format_sec_narratives(narratives: List[RetrievedDocument]) -> str:
    """Format SEC filing narratives for RAG prompt."""
    lines = []
    
    for i, doc in enumerate(narratives, 1):
        meta = doc.metadata
        lines.append(f"\n**Excerpt {i}** - {meta.get('section', 'N/A')} Section")
        lines.append(f"Source: {meta.get('filing_type', 'N/A')} FY{meta.get('fiscal_year', 'N/A')}")
        
        if meta.get("source_url"):
            lines.append(f"URL: {meta.get('source_url')}")
        
        if doc.score is not None:
            lines.append(f"Relevance Score: {1 - doc.score:.3f}")  # Convert distance to similarity
        
        lines.append(f"\n{doc.text[:1000]}...")
        lines.append("─" * 80)
    
    return "\n".join(lines)


def _format_uploaded_docs(docs: List[RetrievedDocument]) -> str:
    """Format uploaded documents for RAG prompt."""
    lines = []
    
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        filename = meta.get("filename", "Unknown")
        file_type = meta.get("file_type", "unknown")
        uploaded_at = meta.get("uploaded_at", "N/A")
        
        lines.append(f"\n**Document {i}**: {filename}")
        lines.append(f"Type: {file_type} | Uploaded: {uploaded_at}")
        
        if doc.score is not None:
            lines.append(f"Relevance Score: {1 - doc.score:.3f}")
        
        lines.append(f"\n{doc.text[:1000]}...")
        lines.append("─" * 80)
    
    return "\n".join(lines)


def _format_dict(data: Dict[str, Any]) -> str:
    """Format dictionary data for RAG prompt."""
    lines = []
    for key, value in data.items():
        lines.append(f"  - {key}: {value}")
    return "\n".join(lines)

