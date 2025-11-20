"""
RAG Evaluation Script

Evaluates RAG system quality using retrieval and QA metrics.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.finanlyzeos_chatbot.rag_evaluation import RAGEvaluator, RetrievalEvaluation
from src.finanlyzeos_chatbot.rag_retriever import RAGRetriever
from src.finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
from src.finanlyzeos_chatbot.config import Settings


def load_evaluation_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
    """Load evaluation dataset from JSON file."""
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        print("Creating example dataset template...")
        # Create directory if it doesn't exist
        dataset_path.parent.mkdir(parents=True, exist_ok=True)
        example_dataset = [
            {
                "query": "What is Apple's revenue?",
                "tickers": ["AAPL"],
                "relevant_doc_ids": ["sec:AAPL_10K_2024", "metric:revenue"],
                "expected_answer": "Apple's revenue is $394.3 billion in FY2024",
                "key_facts": ["$394.3 billion", "FY2024"]
            }
        ]
        dataset_path.write_text(json.dumps(example_dataset, indent=2))
        print(f"Created example dataset at {dataset_path}")
        return []
    
    return json.loads(dataset_path.read_text())


def evaluate_retrieval(
    evaluator: RAGEvaluator,
    retriever: RAGRetriever,
    test_cases: List[Dict[str, Any]],
) -> List[RetrievalEvaluation]:
    """Evaluate retrieval quality."""
    evaluations = []
    
    for i, test_case in enumerate(test_cases):
        query = test_case["query"]
        tickers = test_case.get("tickers", [])
        relevant_doc_ids = set(test_case.get("relevant_doc_ids", []))
        
        print(f"\n[{i+1}/{len(test_cases)}] Evaluating: {query}")
        
        # Retrieve
        result = retriever.retrieve(
            query=query,
            tickers=tickers,
            use_reranking=True,
        )
        
        # Evaluate
        eval_result = evaluator.evaluate_retrieval(
            query=query,
            result=result,
            relevant_doc_ids=relevant_doc_ids,
        )
        
        evaluations.append(eval_result)
        
        # Print metrics
        print(f"  Recall@5: {eval_result.recall_at_5:.3f}")
        print(f"  MRR: {eval_result.mrr:.3f}")
        print(f"  nDCG@5: {eval_result.ndcg_at_5:.3f}")
    
    return evaluations


def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG system quality")
    parser.add_argument("--database", type=Path, required=True, help="Path to database")
    parser.add_argument("--dataset", type=Path, default=Path("data/evaluation/rag_test_set.json"), help="Evaluation dataset path")
    parser.add_argument("--output", type=Path, help="Output JSON file for results")
    
    args = parser.parse_args()
    
    # Load dataset
    test_cases = load_evaluation_dataset(args.dataset)
    if not test_cases:
        print("No test cases found. Please create a dataset file.")
        return 1
    
    # Initialize components
    settings = Settings(database_path=args.database)
    analytics_engine = AnalyticsEngine(settings)
    retriever = RAGRetriever(args.database, analytics_engine)
    evaluator = RAGEvaluator()
    
    # Evaluate
    print(f"Evaluating {len(test_cases)} test cases...")
    evaluations = evaluate_retrieval(evaluator, retriever, test_cases)
    
    # Aggregate metrics
    aggregate = evaluator.evaluate_batch(evaluations)
    
    print("\n" + "="*60)
    print("AGGREGATE METRICS")
    print("="*60)
    for metric, value in aggregate.items():
        print(f"{metric:20s}: {value:.3f}")
    
    # Save results
    if args.output:
        results = {
            "aggregate_metrics": aggregate,
            "individual_evaluations": [
                {
                    "query": e.query,
                    "recall_at_5": e.recall_at_5,
                    "mrr": e.mrr,
                    "ndcg_at_5": e.ndcg_at_5,
                }
                for e in evaluations
            ]
        }
        args.output.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

