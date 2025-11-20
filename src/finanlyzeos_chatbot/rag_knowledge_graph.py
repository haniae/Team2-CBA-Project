"""
Knowledge-Graph + RAG Hybrid

Builds a small entity/relation graph from filings:
- Nodes: companies, segments, products, risks, metrics
- Edges: "AAPL has segment 'Services'", "AAPL faces risk 'FX exposure'"

For relationship queries, queries KG first for candidate nodes,
then uses RAG on docs only for explaining those relations.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

LOGGER = logging.getLogger(__name__)

# Optional import for networkx
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None


@dataclass
class Entity:
    """Entity in knowledge graph."""
    id: str
    name: str
    entity_type: str  # "company", "segment", "product", "risk", "metric"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """Relation between entities."""
    source_id: str
    target_id: str
    relation_type: str  # "has_segment", "faces_risk", "has_metric"
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """
    Simple knowledge graph for financial entities and relations.
    
    Stores:
    - Companies and their segments, products, risks, metrics
    - Relations between entities
    """
    
    def __init__(self):
        """Initialize knowledge graph."""
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.graph = None
        
        if NETWORKX_AVAILABLE:
            self.graph = nx.DiGraph()
        else:
            LOGGER.warning("networkx not available. Install: pip install networkx")
    
    def add_entity(self, entity: Entity):
        """Add entity to graph."""
        self.entities[entity.id] = entity
        if self.graph:
            self.graph.add_node(entity.id, **entity.metadata)
    
    def add_relation(self, relation: Relation):
        """Add relation to graph."""
        self.relations.append(relation)
        if self.graph:
            self.graph.add_edge(
                relation.source_id,
                relation.target_id,
                relation_type=relation.relation_type,
                **relation.metadata,
            )
    
    def get_related_entities(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
    ) -> List[str]:
        """
        Get entities related to given entity.
        
        Args:
            entity_id: Entity ID
            relation_type: Optional relation type filter
        
        Returns:
            List of related entity IDs
        """
        if not self.graph:
            # Fallback: use relations list
            related = []
            for rel in self.relations:
                if rel.source_id == entity_id:
                    if relation_type is None or rel.relation_type == relation_type:
                        related.append(rel.target_id)
            return related
        
        # Use networkx
        if entity_id not in self.graph:
            return []
        
        related = []
        for target_id in self.graph.successors(entity_id):
            if relation_type is None:
                related.append(target_id)
            else:
                edge_data = self.graph[entity_id][target_id]
                if edge_data.get("relation_type") == relation_type:
                    related.append(target_id)
        
        return related
    
    def find_common_entities(
        self,
        entity_ids: List[str],
        relation_type: Optional[str] = None,
    ) -> List[str]:
        """
        Find entities related to all given entities.
        
        Args:
            entity_ids: List of entity IDs
            relation_type: Optional relation type filter
        
        Returns:
            List of common related entity IDs
        """
        if not entity_ids:
            return []
        
        # Get related entities for each
        all_related = []
        for entity_id in entity_ids:
            related = self.get_related_entities(entity_id, relation_type)
            all_related.append(set(related))
        
        # Find intersection
        common = set.intersection(*all_related) if all_related else set()
        return list(common)
    
    def extract_from_document(
        self,
        text: str,
        ticker: str,
        metadata: Dict[str, Any],
    ):
        """
        Extract entities and relations from document text.
        
        Args:
            text: Document text
            ticker: Ticker symbol
            metadata: Document metadata
        """
        # Simple extraction (can be enhanced with NER)
        ticker_upper = ticker.upper()
        
        # Add company entity
        company_id = f"company_{ticker_upper}"
        if company_id not in self.entities:
            self.add_entity(Entity(
                id=company_id,
                name=ticker_upper,
                entity_type="company",
                metadata={"ticker": ticker_upper},
            ))
        
        # Extract segments (simple pattern matching)
        segment_patterns = [
            r'(?:segment|division|business unit)[s]?\s+(?:called|named|:)?\s*["\']?([A-Z][^"\']+)["\']?',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+segment',
        ]
        
        for pattern in segment_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                segment_name = match.group(1).strip()
                segment_id = f"segment_{ticker_upper}_{segment_name.lower().replace(' ', '_')}"
                
                if segment_id not in self.entities:
                    self.add_entity(Entity(
                        id=segment_id,
                        name=segment_name,
                        entity_type="segment",
                        metadata={"ticker": ticker_upper},
                    ))
                
                # Add relation
                self.add_relation(Relation(
                    source_id=company_id,
                    target_id=segment_id,
                    relation_type="has_segment",
                    metadata={"source": "document"},
                ))
        
        LOGGER.debug(f"Extracted entities and relations from document for {ticker_upper}")


class KGRAGHybrid:
    """
    Hybrid KG + RAG retriever.
    
    For relationship queries:
    1. Query KG for candidate entities
    2. Use RAG on docs to explain relations
    """
    
    def __init__(
        self,
        knowledge_graph: KnowledgeGraph,
        rag_retriever: Any,  # RAGRetriever
    ):
        """
        Initialize KG+RAG hybrid.
        
        Args:
            knowledge_graph: KnowledgeGraph instance
            rag_retriever: RAGRetriever instance
        """
        self.kg = knowledge_graph
        self.rag_retriever = rag_retriever
    
    def is_relationship_query(self, query: str) -> bool:
        """Check if query is asking about relationships."""
        query_lower = query.lower()
        relationship_keywords = [
            "relationship", "related", "connection", "link", "associate",
            "both", "common", "shared", "affect", "impact",
        ]
        return any(keyword in query_lower for keyword in relationship_keywords)
    
    def retrieve_hybrid(
        self,
        query: str,
        tickers: List[str],
    ) -> Tuple[List[str], List[str]]:
        """
        Retrieve using KG + RAG hybrid approach.
        
        Args:
            query: User query
            tickers: List of tickers
        
        Returns:
            Tuple of (kg_entities, rag_docs)
        """
        if not self.is_relationship_query(query):
            # Not a relationship query - use RAG only
            return [], []
        
        # Query KG for candidate entities
        kg_entities = []
        for ticker in tickers:
            company_id = f"company_{ticker.upper()}"
            related = self.kg.get_related_entities(company_id)
            kg_entities.extend(related)
        
        # If multiple tickers, find common entities
        if len(tickers) > 1:
            company_ids = [f"company_{t.upper()}" for t in tickers]
            common = self.kg.find_common_entities(company_ids)
            kg_entities.extend(common)
        
        # Use RAG to explain relations
        # (This would call rag_retriever.retrieve() with query focused on entities)
        rag_docs = []  # Placeholder - would call actual RAG retriever
        
        LOGGER.debug(
            f"KG+RAG hybrid: {len(kg_entities)} entities, "
            f"{len(rag_docs)} RAG docs for query '{query[:50]}...'"
        )
        
        return kg_entities, rag_docs

