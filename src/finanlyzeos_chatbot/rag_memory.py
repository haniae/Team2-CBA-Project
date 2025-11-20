"""
Memory-Augmented RAG for Uploaded Documents

Implements per-conversation, per-user document tracking and clustering:
- Per conversation document isolation
- Per user document tracking
- Document lifetime tracking
- Document-topic clustering
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from .rag_retriever import RetrievedDocument

LOGGER = logging.getLogger(__name__)


@dataclass
class DocumentMemory:
    """Memory entry for an uploaded document."""
    document_id: str
    conversation_id: Optional[str]
    user_id: Optional[str]
    filename: str
    uploaded_at: datetime
    last_accessed: datetime
    access_count: int = 0
    topics: List[str] = field(default_factory=list)  # Clustered topics
    chunk_ids: List[str] = field(default_factory=list)  # Vector store chunk IDs


@dataclass
class ConversationMemory:
    """Memory for a conversation's documents."""
    conversation_id: str
    documents: List[DocumentMemory]
    created_at: datetime
    last_accessed: datetime
    topic_clusters: Dict[str, List[str]] = field(default_factory=dict)  # topic -> document_ids


class MemoryAugmentedRAG:
    """
    Memory-augmented RAG for uploaded documents.
    
    Tracks documents per conversation/user and provides topic clustering.
    """
    
    def __init__(self, document_lifetime_days: int = 90):
        """
        Initialize memory-augmented RAG.
        
        Args:
            document_lifetime_days: Days before documents are considered stale (default 90)
        """
        self.document_lifetime = timedelta(days=document_lifetime_days)
        self.conversation_memories: Dict[str, ConversationMemory] = {}
        self.user_memories: Dict[str, Set[str]] = defaultdict(set)  # user_id -> conversation_ids
        self.document_registry: Dict[str, DocumentMemory] = {}
    
    def register_document(
        self,
        document_id: str,
        conversation_id: Optional[str],
        user_id: Optional[str],
        filename: str,
        chunk_ids: List[str],
        uploaded_at: Optional[datetime] = None,
    ) -> None:
        """
        Register a new document in memory.
        
        Args:
            document_id: Unique document ID
            conversation_id: Conversation ID (if scoped)
            user_id: User ID (if available)
            filename: Document filename
            chunk_ids: List of chunk IDs in vector store
            uploaded_at: Upload timestamp (defaults to now)
        """
        now = uploaded_at or datetime.now()
        
        memory = DocumentMemory(
            document_id=document_id,
            conversation_id=conversation_id,
            user_id=user_id,
            filename=filename,
            uploaded_at=now,
            last_accessed=now,
            chunk_ids=chunk_ids,
        )
        
        self.document_registry[document_id] = memory
        
        # Add to conversation memory
        if conversation_id:
            if conversation_id not in self.conversation_memories:
                self.conversation_memories[conversation_id] = ConversationMemory(
                    conversation_id=conversation_id,
                    documents=[],
                    created_at=now,
                    last_accessed=now,
                )
            self.conversation_memories[conversation_id].documents.append(memory)
            self.conversation_memories[conversation_id].last_accessed = now
        
        # Track user conversations
        if user_id and conversation_id:
            self.user_memories[user_id].add(conversation_id)
        
        LOGGER.debug(f"Registered document {document_id} in conversation {conversation_id}")
    
    def update_access(
        self,
        document_id: str,
        conversation_id: Optional[str] = None,
    ) -> None:
        """Update document access timestamp and count."""
        if document_id in self.document_registry:
            memory = self.document_registry[document_id]
            memory.last_accessed = datetime.now()
            memory.access_count += 1
            
            if conversation_id and conversation_id in self.conversation_memories:
                self.conversation_memories[conversation_id].last_accessed = datetime.now()
    
    def get_conversation_documents(
        self,
        conversation_id: str,
        include_stale: bool = False,
    ) -> List[DocumentMemory]:
        """
        Get all documents for a conversation.
        
        Args:
            conversation_id: Conversation ID
            include_stale: Include documents past lifetime (default False)
        
        Returns:
            List of DocumentMemory entries
        """
        if conversation_id not in self.conversation_memories:
            return []
        
        memory = self.conversation_memories[conversation_id]
        now = datetime.now()
        
        documents = []
        for doc in memory.documents:
            age = now - doc.uploaded_at
            if include_stale or age < self.document_lifetime:
                documents.append(doc)
        
        return documents
    
    def get_user_documents(
        self,
        user_id: str,
        include_stale: bool = False,
    ) -> List[DocumentMemory]:
        """
        Get all documents for a user (across all conversations).
        
        Args:
            user_id: User ID
            include_stale: Include stale documents (default False)
        
        Returns:
            List of DocumentMemory entries
        """
        conversation_ids = self.user_memories.get(user_id, set())
        all_docs = []
        
        for conv_id in conversation_ids:
            docs = self.get_conversation_documents(conv_id, include_stale)
            all_docs.extend(docs)
        
        return all_docs
    
    def cluster_documents_by_topic(
        self,
        conversation_id: str,
        documents: List[RetrievedDocument],
    ) -> Dict[str, List[str]]:
        """
        Cluster documents by topic (simplified - can be enhanced with topic modeling).
        
        Args:
            conversation_id: Conversation ID
            documents: Retrieved documents
        
        Returns:
            Dictionary mapping topic -> list of document IDs
        """
        # Simple keyword-based clustering (can be enhanced with LDA, BERTopic, etc.)
        topic_keywords = {
            "financial_metrics": ["revenue", "earnings", "profit", "margin", "ebitda"],
            "risk_analysis": ["risk", "uncertainty", "volatility", "exposure"],
            "forecasting": ["forecast", "projection", "outlook", "future"],
            "governance": ["board", "executive", "compensation", "governance"],
            "operations": ["operations", "business", "segment", "product"],
        }
        
        clusters: Dict[str, List[str]] = defaultdict(list)
        
        for doc in documents:
            text_lower = doc.text.lower()
            doc_id = doc.metadata.get("document_id") or doc.metadata.get("filename", "unknown")
            
            # Assign to topic based on keywords
            assigned = False
            for topic, keywords in topic_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    clusters[topic].append(doc_id)
                    assigned = True
                    break
            
            if not assigned:
                clusters["general"].append(doc_id)
        
        # Update conversation memory
        if conversation_id in self.conversation_memories:
            self.conversation_memories[conversation_id].topic_clusters = dict(clusters)
        
        return dict(clusters)
    
    def get_stale_documents(self, conversation_id: Optional[str] = None) -> List[str]:
        """
        Get list of stale document IDs (past lifetime).
        
        Args:
            conversation_id: Optional conversation ID to filter
        
        Returns:
            List of stale document IDs
        """
        now = datetime.now()
        stale = []
        
        if conversation_id:
            docs = self.get_conversation_documents(conversation_id, include_stale=True)
            for doc in docs:
                if now - doc.uploaded_at > self.document_lifetime:
                    stale.append(doc.document_id)
        else:
            for doc_id, doc in self.document_registry.items():
                if now - doc.uploaded_at > self.document_lifetime:
                    stale.append(doc_id)
        
        return stale
    
    def get_memory_stats(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get memory statistics.
        
        Args:
            conversation_id: Optional conversation ID to filter
        
        Returns:
            Dictionary with memory stats
        """
        if conversation_id:
            docs = self.get_conversation_documents(conversation_id, include_stale=True)
            return {
                "conversation_id": conversation_id,
                "total_documents": len(docs),
                "active_documents": len([d for d in docs if (datetime.now() - d.uploaded_at) < self.document_lifetime]),
                "stale_documents": len([d for d in docs if (datetime.now() - d.uploaded_at) >= self.document_lifetime]),
                "topic_clusters": self.conversation_memories.get(conversation_id, ConversationMemory("", [], datetime.now(), datetime.now())).topic_clusters,
            }
        else:
            return {
                "total_documents": len(self.document_registry),
                "total_conversations": len(self.conversation_memories),
                "total_users": len(self.user_memories),
            }

