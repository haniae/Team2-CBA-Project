"""
Online Feedback → Reranker / Policy Tuning

Collects user feedback and uses it to improve retrieval:
- Logs queries, retrieved docs, answers, and user feedback
- Uses feedback to calibrate scores and adjust thresholds
- Enables learning-to-rank on user data
"""

from __future__ import annotations

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

LOGGER = logging.getLogger(__name__)


class FeedbackLabel(Enum):
    """User feedback labels."""
    GOOD = "good"  # Answer was helpful and accurate
    BAD = "bad"  # Answer was incorrect or unhelpful
    PARTIAL = "partial"  # Answer was partially correct


@dataclass
class FeedbackRecord:
    """Record of user feedback for a query."""
    query: str
    doc_ids: List[str]  # IDs of retrieved documents
    doc_scores: List[float]  # Scores of retrieved documents
    answer: str
    label: FeedbackLabel
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    timestamp: Optional[str] = None
    reason: Optional[str] = None  # Why feedback was given
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class FeedbackCollector:
    """
    Collects and stores user feedback for RAG queries.
    """
    
    def __init__(self, feedback_file: Optional[Path] = None):
        """
        Initialize feedback collector.
        
        Args:
            feedback_file: Path to JSON file for storing feedback (optional)
        """
        self.feedback_file = feedback_file or Path("data/rag_feedback.json")
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        self.feedback_records: List[FeedbackRecord] = []
        self._load_feedback()
    
    def record_feedback(
        self,
        query: str,
        doc_ids: List[str],
        doc_scores: List[float],
        answer: str,
        label: FeedbackLabel,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """
        Record user feedback.
        
        Args:
            query: User query
            doc_ids: IDs of retrieved documents
            doc_scores: Scores of retrieved documents
            answer: Generated answer
            label: Feedback label
            user_id: Optional user ID
            conversation_id: Optional conversation ID
            reason: Optional reason for feedback
        """
        record = FeedbackRecord(
            query=query,
            doc_ids=doc_ids,
            doc_scores=doc_scores,
            answer=answer,
            label=label,
            user_id=user_id,
            conversation_id=conversation_id,
            reason=reason,
        )
        
        self.feedback_records.append(record)
        self._save_feedback()
        
        LOGGER.info(f"Feedback recorded: {label.value} for query '{query[:50]}...'")
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get statistics about collected feedback.
        
        Returns:
            Dictionary with feedback statistics
        """
        if not self.feedback_records:
            return {
                "total": 0,
                "good": 0,
                "bad": 0,
                "partial": 0,
            }
        
        total = len(self.feedback_records)
        good = sum(1 for r in self.feedback_records if r.label == FeedbackLabel.GOOD)
        bad = sum(1 for r in self.feedback_records if r.label == FeedbackLabel.BAD)
        partial = sum(1 for r in self.feedback_records if r.label == FeedbackLabel.PARTIAL)
        
        return {
            "total": total,
            "good": good,
            "bad": bad,
            "partial": partial,
            "good_ratio": good / total if total > 0 else 0.0,
        }
    
    def _load_feedback(self):
        """Load feedback records from file."""
        if not self.feedback_file.exists():
            return
        
        try:
            with open(self.feedback_file, 'r') as f:
                data = json.load(f)
                for record_data in data:
                    record_data['label'] = FeedbackLabel(record_data['label'])
                    self.feedback_records.append(FeedbackRecord(**record_data))
            LOGGER.info(f"Loaded {len(self.feedback_records)} feedback records")
        except Exception as e:
            LOGGER.warning(f"Failed to load feedback: {e}")
    
    def _save_feedback(self):
        """Save feedback records to file."""
        try:
            data = [asdict(record) for record in self.feedback_records]
            # Convert enum to string
            for record_data in data:
                record_data['label'] = record_data['label'].value
            
            with open(self.feedback_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            LOGGER.warning(f"Failed to save feedback: {e}")


class ScoreCalibrator:
    """
    Calibrates retrieval scores based on user feedback.
    
    Simple logistic regression or threshold adjustment based on feedback.
    """
    
    def __init__(self, feedback_collector: Optional[FeedbackCollector] = None):
        """
        Initialize score calibrator.
        
        Args:
            feedback_collector: FeedbackCollector instance
        """
        self.feedback_collector = feedback_collector
        self.calibration_threshold = 0.5  # Default threshold
    
    def calibrate_score(
        self,
        score: float,
        source_type: str,
        doc_id: Optional[str] = None,
    ) -> float:
        """
        Calibrate a retrieval score based on feedback.
        
        Args:
            score: Original score
            source_type: Source type (e.g., "sec_narratives")
            doc_id: Optional document ID for per-document calibration
        
        Returns:
            Calibrated score
        """
        # Simple calibration: adjust threshold based on feedback
        # More sophisticated: train a small ML model
        
        if not self.feedback_collector:
            return score
        
        # Get feedback stats for this source type
        stats = self.feedback_collector.get_feedback_stats()
        
        # Adjust score based on overall feedback quality
        if stats.get("good_ratio", 0.5) > 0.7:
            # High quality feedback - slightly boost scores
            calibrated = min(1.0, score * 1.1)
        elif stats.get("good_ratio", 0.5) < 0.3:
            # Low quality feedback - slightly reduce scores
            calibrated = max(0.0, score * 0.9)
        else:
            calibrated = score
        
        return calibrated
    
    def update_from_feedback(self):
        """Update calibration parameters from feedback."""
        if not self.feedback_collector:
            return
        
        stats = self.feedback_collector.get_feedback_stats()
        
        # Adjust threshold based on feedback
        if stats.get("good_ratio", 0.5) > 0.7:
            # Lower threshold if feedback is good (be more permissive)
            self.calibration_threshold = max(0.3, self.calibration_threshold - 0.05)
        elif stats.get("good_ratio", 0.5) < 0.3:
            # Raise threshold if feedback is bad (be more strict)
            self.calibration_threshold = min(0.7, self.calibration_threshold + 0.05)
        
        LOGGER.debug(f"Calibration threshold updated to {self.calibration_threshold:.2f}")

