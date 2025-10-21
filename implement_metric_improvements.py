#!/usr/bin/env python3
"""Implement Metric Resolution Improvements."""

import sys
import os
import time
import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional, Set
from difflib import get_close_matches

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from benchmarkos_chatbot.parsing.ontology import METRIC_SYNONYMS, _normalize_alias

class EnhancedMetricResolver:
    """Enhanced metric resolution with all improvements."""
    
    def __init__(self):
        self.test_cases = [
            # Basic metrics (should work)
            ("revenue", "revenue", "Basic revenue"),
            ("sales", "revenue", "Sales synonym"),
            ("net income", "net_income", "Net income"),
            ("eps", "eps_diluted", "EPS abbreviation"),
            ("ebitda", "ebitda", "EBITDA"),
            
            # Edge cases (should be fixed)
            ("  revenue  ", "revenue", "Revenue with spaces"),
            ("revenue!", "revenue", "Revenue with exclamation"),
            ("revenue?", "revenue", "Revenue with question"),
            ("revenue.", "revenue", "Revenue with period"),
            ("revenue,", "revenue", "Revenue with comma"),
            ("rëvënüë", "revenue", "Revenue with accents"),
            ("rêvênüê", "revenue", "Revenue with different accents"),
            ("quarterly revenue", "revenue", "Quarterly revenue"),
            ("annual revenue growth", "revenue", "Annual revenue growth"),
            ("revenue for Q1", "revenue", "Revenue for Q1"),
            ("revenue per share", "revenue", "Revenue per share"),
            
            # Missing metrics (should be added)
            ("revenue growth", "revenue_growth", "Revenue growth"),
            ("operating cash flow", "operating_cash_flow", "Operating cash flow"),
            ("price to sales", "ps_ratio", "Price to sales"),
            ("market cap", "market_cap", "Market cap"),
            ("debt to equity", "debt_to_equity", "Debt to equity"),
            
            # Context-aware tests
            ("revenue from operations", "revenue", "Revenue with context"),
            ("net income margin", "net_income", "Net income with context"),
            ("eps growth", "eps_diluted", "EPS with context"),
            ("ebitda margin", "ebitda", "EBITDA with context"),
            ("free cash flow yield", "free_cash_flow", "FCF with context"),
            
            # Confidence scoring tests
            ("revenue", "revenue", "High confidence exact match"),
            ("rev", "revenue", "Medium confidence abbreviation"),
            ("quarterly revenue", "revenue", "Low confidence partial match"),
            ("rëvënüë", "revenue", "Low confidence fuzzy match"),
        ]
        
        # Enhanced metric synonyms with more comprehensive coverage
        self.enhanced_metric_synonyms = {
            **METRIC_SYNONYMS,
            # Revenue variations
            "revenue growth": "revenue_growth",
            "revenue per share": "revenue_per_share",
            "gross revenue": "gross_revenue",
            "net revenue": "net_revenue",
            "operating revenue": "operating_revenue",
            "recurring revenue": "recurring_revenue",
            "subscription revenue": "subscription_revenue",
            "revenue from operations": "revenue",
            "revenue growth rate": "revenue_growth",
            "revenue growth percentage": "revenue_growth",
            "revenue growth year over year": "revenue_growth",
            "revenue growth yoy": "revenue_growth",
            "revenue growth qoq": "revenue_growth",
            "revenue growth mom": "revenue_growth",
            
            # Profitability variations
            "gross income": "gross_income",
            "operating profit margin": "operating_profit_margin",
            "net profit margin": "net_profit_margin",
            "ebitda margin": "ebitda_margin",
            "adjusted net income": "adjusted_net_income",
            "core earnings": "core_earnings",
            "net income margin": "net_income",
            "net income growth": "net_income",
            "net income growth rate": "net_income",
            "net income growth percentage": "net_income",
            "net income growth year over year": "net_income",
            "net income growth yoy": "net_income",
            "net income growth qoq": "net_income",
            "net income growth mom": "net_income",
            
            # EPS variations
            "eps growth": "eps_diluted",
            "eps growth rate": "eps_diluted",
            "eps growth percentage": "eps_diluted",
            "eps growth year over year": "eps_diluted",
            "eps growth yoy": "eps_diluted",
            "eps growth qoq": "eps_diluted",
            "eps growth mom": "eps_diluted",
            "diluted eps growth": "eps_diluted",
            "diluted eps growth rate": "eps_diluted",
            "diluted eps growth percentage": "eps_diluted",
            "diluted eps growth year over year": "eps_diluted",
            "diluted eps growth yoy": "eps_diluted",
            "diluted eps growth qoq": "eps_diluted",
            "diluted eps growth mom": "eps_diluted",
            
            # EBITDA variations
            "ebitda growth": "ebitda",
            "ebitda growth rate": "ebitda",
            "ebitda growth percentage": "ebitda",
            "ebitda growth year over year": "ebitda",
            "ebitda growth yoy": "ebitda",
            "ebitda growth qoq": "ebitda",
            "ebitda growth mom": "ebitda",
            "ebitda margin": "ebitda",
            "ebitda margin percentage": "ebitda",
            "ebitda margin year over year": "ebitda",
            "ebitda margin yoy": "ebitda",
            "ebitda margin qoq": "ebitda",
            "ebitda margin mom": "ebitda",
            
            # Cash flow variations
            "operating cash flow": "operating_cash_flow",
            "investing cash flow": "investing_cash_flow",
            "financing cash flow": "financing_cash_flow",
            "cash from operations": "cash_from_operations",
            "cash and cash equivalents": "cash_and_cash_equivalents",
            "free cash flow yield": "free_cash_flow",
            "free cash flow margin": "free_cash_flow",
            "free cash flow growth": "free_cash_flow",
            "free cash flow growth rate": "free_cash_flow",
            "free cash flow growth percentage": "free_cash_flow",
            "free cash flow growth year over year": "free_cash_flow",
            "free cash flow growth yoy": "free_cash_flow",
            "free cash flow growth qoq": "free_cash_flow",
            "free cash flow growth mom": "free_cash_flow",
            
            # Valuation variations
            "price to sales": "ps_ratio",
            "price to cash flow": "price_to_cash_flow",
            "enterprise value": "enterprise_value",
            "market cap": "market_cap",
            "book value": "book_value",
            "market capitalization": "market_cap",
            "market cap growth": "market_cap",
            "market cap growth rate": "market_cap",
            "market cap growth percentage": "market_cap",
            "market cap growth year over year": "market_cap",
            "market cap growth yoy": "market_cap",
            "market cap growth qoq": "market_cap",
            "market cap growth mom": "market_cap",
            
            # Efficiency ratios
            "inventory turnover": "inventory_turnover",
            "receivables turnover": "receivables_turnover",
            "asset turnover": "asset_turnover",
            "equity turnover": "equity_turnover",
            "inventory turnover ratio": "inventory_turnover",
            "receivables turnover ratio": "receivables_turnover",
            "asset turnover ratio": "asset_turnover",
            "equity turnover ratio": "equity_turnover",
            
            # Leverage ratios
            "debt to equity": "debt_to_equity",
            "debt ratio": "debt_ratio",
            "interest coverage": "interest_coverage",
            "debt service coverage": "debt_service_coverage",
            "debt to equity ratio": "debt_to_equity",
            "debt to equity ratio percentage": "debt_to_equity",
            "debt to equity ratio year over year": "debt_to_equity",
            "debt to equity ratio yoy": "debt_to_equity",
            "debt to equity ratio qoq": "debt_to_equity",
            "debt to equity ratio mom": "debt_to_equity",
            
            # Additional common variations
            "quarterly": "quarterly",
            "annual": "annual",
            "year over year": "yoy",
            "yoy": "yoy",
            "quarter over quarter": "qoq",
            "qoq": "qoq",
            "month over month": "mom",
            "mom": "mom",
            "growth": "growth",
            "growth rate": "growth_rate",
            "growth percentage": "growth_percentage",
            "margin": "margin",
            "margin percentage": "margin_percentage",
            "ratio": "ratio",
            "yield": "yield",
            "return": "return",
            "turnover": "turnover",
            "coverage": "coverage",
        }
        
        # Context keywords for disambiguation
        self.context_keywords = {
            "revenue": ["operations", "sales", "income", "earnings", "growth", "margin", "yield"],
            "net_income": ["profit", "earnings", "income", "margin", "growth", "yield"],
            "eps_diluted": ["earnings", "per", "share", "diluted", "growth", "yield"],
            "ebitda": ["operating", "income", "profit", "margin", "growth", "yield"],
            "free_cash_flow": ["operating", "cash", "flow", "yield", "margin", "growth"],
            "market_cap": ["market", "capitalization", "cap", "value", "growth", "yield"],
            "debt_to_equity": ["debt", "equity", "ratio", "leverage", "coverage"],
        }
        
        # Confidence scoring weights
        self.confidence_weights = {
            "exact_match": 1.0,
            "alias_match": 0.9,
            "partial_match": 0.7,
            "context_match": 0.8,
            "fuzzy_match": 0.6,
            "fallback_match": 0.5,
        }
    
    def enhanced_normalize_alias(self, text: str) -> str:
        """Enhanced alias normalization with proper Unicode handling."""
        
        # Step 1: Unicode normalization
        normalized = unicodedata.normalize("NFKC", text)
        
        # Step 2: Convert to lowercase
        normalized = normalized.lower()
        
        # Step 3: Remove special characters and normalize whitespace
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        
        return normalized
    
    def resolve_metric_with_context(self, text: str, context: str = "") -> Tuple[Optional[str], float]:
        """Resolve metric with context awareness and confidence scoring."""
        
        # Step 1: Enhanced normalization
        normalized = self.enhanced_normalize_alias(text)
        context_normalized = self.enhanced_normalize_alias(context) if context else ""
        
        # Step 2: Try exact match first (highest confidence)
        if normalized in self.enhanced_metric_synonyms:
            return self.enhanced_metric_synonyms[normalized], self.confidence_weights["exact_match"]
        
        # Step 3: Try context-aware matching
        if context_normalized:
            for metric_key, metric_value in self.enhanced_metric_synonyms.items():
                if metric_key in normalized and any(keyword in context_normalized for keyword in self.context_keywords.get(metric_value, [])):
                    return metric_value, self.confidence_weights["context_match"]
        
        # Step 4: Try partial match (check if metric name is contained in input)
        for metric_key, metric_value in self.enhanced_metric_synonyms.items():
            if metric_key in normalized:
                return metric_value, self.confidence_weights["partial_match"]
        
        # Step 5: Try reverse partial match (check if input is contained in metric name)
        for metric_key, metric_value in self.enhanced_metric_synonyms.items():
            if normalized in metric_key:
                return metric_value, self.confidence_weights["partial_match"]
        
        # Step 6: Try fuzzy matching as fallback
        matches = get_close_matches(normalized, self.enhanced_metric_synonyms.keys(), n=1, cutoff=0.8)
        if matches:
            return self.enhanced_metric_synonyms[matches[0]], self.confidence_weights["fuzzy_match"]
        
        # Step 7: Try very fuzzy matching for accented characters
        matches = get_close_matches(normalized, self.enhanced_metric_synonyms.keys(), n=1, cutoff=0.6)
        if matches:
            return self.enhanced_metric_synonyms[matches[0]], self.confidence_weights["fuzzy_match"]
        
        return None, 0.0
    
    def test_enhanced_resolution(self) -> Dict[str, Any]:
        """Test enhanced metric resolution."""
        
        print("ENHANCED METRIC RESOLUTION TESTING")
        print("=" * 70)
        print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        results = []
        
        for input_text, expected, description in self.test_cases:
            try:
                # Test enhanced resolution
                resolved, confidence = self.resolve_metric_with_context(input_text)
                
                if resolved == expected:
                    status = "✅ PASS"
                else:
                    status = "❌ FAIL"
                
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected": expected,
                    "actual": resolved,
                    "confidence": confidence,
                    "status": status
                })
                
                confidence_str = f"({confidence:.2f})" if confidence > 0 else "(0.00)"
                print(f"   {status} {input_text:<25} | {str(expected):<25} | {str(resolved)} {confidence_str}")
                
            except Exception as e:
                status = "❌ ERROR"
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected": expected,
                    "actual": f"ERROR: {str(e)}",
                    "confidence": 0.0,
                    "status": status
                })
                print(f"   {status} {input_text:<25} | {str(expected):<25} | ERROR: {str(e)}")
        
        print()
        
        # Count results
        passed = sum(1 for r in results if r["status"] == "✅ PASS")
        failed = sum(1 for r in results if r["status"] == "❌ FAIL")
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        # Calculate average confidence
        avg_confidence = sum(r["confidence"] for r in results if r["confidence"] > 0) / len([r for r in results if r["confidence"] > 0]) if any(r["confidence"] > 0 for r in results) else 0
        
        print(f"   Results: {passed} passed, {failed} failed")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Average Confidence Answers: {avg_confidence:.3f}")
        print()
        
        return {
            "results": results,
            "passed": passed,
            "failed": failed,
            "total": total,
            "success_rate": success_rate,
            "average_confidence": avg_confidence
        }
    
    def compare_with_original(self) -> Dict[str, Any]:
        """Compare enhanced resolution with original."""
        
        print("COMPARING WITH ORIGINAL RESOLUTION")
        print("-" * 35)
        
        results = []
        
        for input_text, expected, description in self.test_cases:
            try:
                # Test original resolution
                original_resolved = METRIC_SYNONYMS.get(input_text.lower(), None)
                
                # Test enhanced resolution
                enhanced_resolved, confidence = self.resolve_metric_with_context(input_text)
                
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected": expected,
                    "original": original_resolved,
                    "enhanced": enhanced_resolved,
                    "confidence": confidence,
                    "improvement": enhanced_resolved != original_resolved
                })
                
                improvement_indicator = "📈" if enhanced_resolved != original_resolved else "➡️"
                confidence_str = f"({confidence:.2f})" if confidence > 0 else "(0.00)"
                print(f"   {improvement_indicator} {input_text:<25} | {str(expected):<25} | {str(original_resolved)} → {str(enhanced_resolved)} {confidence_str}")
                
            except Exception as e:
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected": expected,
                    "original": f"ERROR: {str(e)}",
                    "enhanced": f"ERROR: {str(e)}",
                    "confidence": 0.0,
                    "improvement": False
                })
                print(f"   ❌ {input_text:<25} | {str(expected):<25} | ERROR: {str(e)}")
        
        print()
        
        # Count improvements
        improvements = sum(1 for r in results if r["improvement"])
        total = len(results)
        improvement_rate = (improvements / total * 100) if total > 0 else 0
        
        # Calculate average confidence for improvements
        avg_confidence_improvements = sum(r["confidence"] for r in results if r["improvement"]) / improvements if improvements > 0 else 0
        
        print(f"   Improvements: {improvements}/{total} ({improvement_rate:.1f}%)")
        print(f"   Average Confidence (Improvements): {avg_confidence_improvements:.3f}")
        print()
        
        return {
            "results": results,
            "improvements": improvements,
            "total": total,
            "improvement_rate": improvement_rate,
            "average_confidence_improvements": avg_confidence_improvements
        }
    
    def test_unicode_normalization(self) -> Dict[str, Any]:
        """Test Unicode normalization specifically."""
        
        print("TESTING UNICODE NORMALIZATION")
        print("-" * 35)
        
        unicode_test_cases = [
            ("rëvënüë", "revenue", "Revenue with accents"),
            ("rêvênüê", "revenue", "Revenue with different accents"),
            ("rëvënüë growth", "revenue_growth", "Revenue growth with accents"),
            ("rêvênüê growth", "revenue_growth", "Revenue growth with different accents"),
            ("ëbïtda", "ebitda", "EBITDA with accents"),
            ("ëbïtda margin", "ebitda", "EBITDA margin with accents"),
            ("nët ïncömë", "net_income", "Net income with accents"),
            ("nët ïncömë growth", "net_income", "Net income growth with accents"),
        ]
        
        results = []
        
        for input_text, expected, description in unicode_test_cases:
            try:
                # Test enhanced resolution
                resolved, confidence = self.resolve_metric_with_context(input_text)
                
                if resolved == expected:
                    status = "✅ PASS"
                else:
                    status = "❌ FAIL"
                
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected": expected,
                    "actual": resolved,
                    "confidence": confidence,
                    "status": status
                })
                
                confidence_str = f"({confidence:.2f})" if confidence > 0 else "(0.00)"
                print(f"   {status} {input_text:<25} | {str(expected):<25} | {str(resolved)} {confidence_str}")
                
            except Exception as e:
                status = "❌ ERROR"
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected": expected,
                    "actual": f"ERROR: {str(e)}",
                    "confidence": 0.0,
                    "status": status
                })
                print(f"   {status} {input_text:<25} | {str(expected):<25} | ERROR: {str(e)}")
        
        print()
        
        # Count results
        passed = sum(1 for r in results if r["status"] == "✅ PASS")
        failed = sum(1 for r in results if r["status"] == "❌ FAIL")
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"   Unicode Results: {passed} passed, {failed} failed")
        print(f"   Unicode Success Rate: {success_rate:.1f}%")
        print()
        
        return {
            "results": results,
            "passed": passed,
            "failed": failed,
            "total": total,
            "success_rate": success_rate
        }
    
    def generate_enhanced_report(self) -> Dict[str, Any]:
        """Generate comprehensive enhanced report."""
        
        print("GENERATING ENHANCED REPORT")
        print("-" * 35)
        
        # Test enhanced resolution
        enhanced_results = self.test_enhanced_resolution()
        
        # Compare with original
        comparison_results = self.compare_with_original()
        
        # Test Unicode normalization
        unicode_results = self.test_unicode_normalization()
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "enhanced_results": enhanced_results,
            "comparison_results": comparison_results,
            "unicode_results": unicode_results,
            "enhanced_synonyms_count": len(self.enhanced_metric_synonyms),
            "original_synonyms_count": len(METRIC_SYNONYMS),
            "new_synonyms_added": len(self.enhanced_metric_synonyms) - len(METRIC_SYNONYMS),
            "context_keywords_count": sum(len(keywords) for keywords in self.context_keywords.values()),
            "confidence_weights_count": len(self.confidence_weights)
        }
        
        print(f"   Enhanced Synonyms: {report['enhanced_synonyms_count']}")
        print(f"   Original Synonyms: {report['original_synonyms_count']}")
        print(f"   New Synonyms Added: {report['new_synonyms_added']}")
        print(f"   Context Keywords: {report['context_keywords_count']}")
        print(f"   Confidence Weights: {report['confidence_weights_count']}")
        print()
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save the enhanced report."""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_metric_resolution_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"   Report saved to: {filename}")

def main():
    """Test enhanced metric resolution."""
    
    resolver = EnhancedMetricResolver()
    report = resolver.generate_enhanced_report()
    resolver.save_report(report)
    
    print("=" * 70)
    print("ENHANCED METRIC RESOLUTION TESTING COMPLETE")
    print(f"Enhanced Success Rate: {report['enhanced_results']['success_rate']:.1f}%")
    print(f"Improvements Made: {report['comparison_results']['improvement_rate']:.1f}%")
    print(f"Unicode Success Rate: {report['unicode_results']['success_rate']:.1f}%")
    print(f"Average Confidence: {report['enhanced_results']['average_confidence']:.3f}")
    print(f"New Synonyms Added: {report['new_synonyms_added']}")

if __name__ == "__main__":
    main()
