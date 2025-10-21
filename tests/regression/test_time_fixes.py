#!/usr/bin/env python3
"""Test Time Period Parsing Fixes."""

import sys
import os
import time
import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional, Sequence

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import both original and fixed versions
from benchmarkos_chatbot.parsing.time_grammar import parse_periods as original_parse_periods

# Import fixed version
sys.path.insert(0, os.path.dirname(__file__))
from fixed_time_grammar import parse_periods as fixed_parse_periods

class TimeFixesTester:
    """Test Time Period Parsing fixes."""
    
    def __init__(self):
        self.test_cases = [
            # Basic year patterns - Calendar Year Default (CRITICAL FIX)
            ("2023", "single", "calendar_year", "Basic year - should default to calendar"),
            ("2024", "single", "calendar_year", "Basic year - should default to calendar"),
            ("2025", "single", "calendar_year", "Basic year - should default to calendar"),
            ("2020", "single", "calendar_year", "Basic year - should default to calendar"),
            
            # Fiscal year patterns
            ("FY2023", "single", "fiscal_year", "Fiscal year explicit"),
            ("FY 2024", "single", "fiscal_year", "Fiscal year with space"),
            ("FY2025", "single", "fiscal_year", "Fiscal year explicit"),
            ("FY 2020", "single", "fiscal_year", "Fiscal year with space"),
            
            # Calendar year patterns
            ("CY2023", "single", "calendar_year", "Calendar year explicit"),
            ("CY 2024", "single", "calendar_year", "Calendar year with space"),
            ("CY2025", "single", "calendar_year", "Calendar year explicit"),
            ("CY 2020", "single", "calendar_year", "Calendar year with space"),
            
            # Calendar keyword patterns
            ("calendar 2023", "single", "calendar_year", "Calendar year full"),
            ("calendar 2024", "single", "calendar_year", "Calendar year full"),
            ("calendar 2025", "single", "calendar_year", "Calendar year full"),
            ("calendar 2020", "single", "calendar_year", "Calendar year full"),
            
            # Quarter patterns - Calendar Quarter Default (CRITICAL FIX)
            ("Q1 2023", "single", "calendar_quarter", "Quarter 1 - should default to calendar"),
            ("Q2 2024", "single", "calendar_quarter", "Quarter 2 - should default to calendar"),
            ("Q3 2025", "single", "calendar_quarter", "Quarter 3 - should default to calendar"),
            ("Q4 2020", "single", "calendar_quarter", "Quarter 4 - should default to calendar"),
            
            # Fiscal quarter patterns
            ("Q1 FY2023", "single", "fiscal_quarter", "Quarter 1 fiscal"),
            ("Q2 FY 2024", "single", "fiscal_quarter", "Quarter 2 fiscal"),
            ("Q3 FY2025", "single", "fiscal_quarter", "Quarter 3 fiscal"),
            ("Q4 FY 2020", "single", "fiscal_quarter", "Quarter 4 fiscal"),
            
            # Calendar quarter patterns
            ("Q1 CY2023", "single", "calendar_quarter", "Quarter 1 calendar"),
            ("Q2 CY 2024", "single", "calendar_quarter", "Quarter 2 calendar"),
            ("Q3 CY2025", "single", "calendar_quarter", "Quarter 3 calendar"),
            ("Q4 CY 2020", "single", "calendar_quarter", "Quarter 4 calendar"),
            
            # Year quarter patterns (CRITICAL FIX)
            ("2023 Q1", "single", "calendar_quarter", "Year quarter - should default to calendar"),
            ("2024 Q2", "single", "calendar_quarter", "Year quarter - should default to calendar"),
            ("2025 Q3", "single", "calendar_quarter", "Year quarter - should default to calendar"),
            ("2020 Q4", "single", "calendar_quarter", "Year quarter - should default to calendar"),
            
            # Short format patterns (CRITICAL FIX)
            ("Q1 '23", "single", "calendar_quarter", "Quarter with 2-digit year - should default to calendar"),
            ("'24 Q2", "single", "calendar_quarter", "2-digit year quarter - should default to calendar"),
            ("Q3 '25", "single", "calendar_quarter", "Quarter with 2-digit year - should default to calendar"),
            ("'20 Q4", "single", "calendar_quarter", "2-digit year quarter - should default to calendar"),
            
            # Range patterns - Calendar Year Default (CRITICAL FIX)
            ("2020-2023", "range", "calendar_year", "Year range - should default to calendar"),
            ("2021 to 2024", "range", "calendar_year", "Year range with 'to' - should default to calendar"),
            ("2022..2024", "range", "calendar_year", "Year range with dots - should default to calendar"),
            ("2020-2025", "range", "calendar_year", "Year range - should default to calendar"),
            
            # Fiscal year range patterns
            ("FY2020-FY2023", "range", "fiscal_year", "Fiscal year range"),
            ("FY 2021 to FY 2024", "range", "fiscal_year", "Fiscal year range with 'to'"),
            ("FY2022-FY2025", "range", "fiscal_year", "Fiscal year range"),
            ("FY 2020 to FY 2025", "range", "fiscal_year", "Fiscal year range with 'to'"),
            
            # Calendar year range patterns
            ("CY2020-CY2023", "range", "calendar_year", "Calendar year range"),
            ("CY 2021 to CY 2024", "range", "calendar_year", "Calendar year range with 'to'"),
            ("CY2022-CY2025", "range", "calendar_year", "Calendar year range"),
            ("CY 2020 to CY 2025", "range", "calendar_year", "Calendar year range with 'to'"),
            
            # Quarter range patterns (CRITICAL FIX)
            ("Q1-Q3 2023", "range", "calendar_quarter", "Quarter range same year - should default to calendar"),
            ("Q1-Q4 2024", "range", "calendar_quarter", "Quarter range same year - should default to calendar"),
            ("Q1 2023-Q2 2024", "range", "calendar_quarter", "Quarter range different years - should default to calendar"),
            ("Q1 2024-Q2 2025", "range", "calendar_quarter", "Quarter range different years - should default to calendar"),
            
            # Relative patterns (CRITICAL FIX)
            ("last 3 years", "relative", "calendar_year", "Last 3 years - should default to calendar"),
            ("last 2 quarters", "relative", "calendar_quarter", "Last 2 quarters - should default to calendar"),
            ("last 5 years", "relative", "calendar_year", "Last 5 years - should default to calendar"),
            ("last 4 quarters", "relative", "calendar_quarter", "Last 4 quarters - should default to calendar"),
            
            # Current/This/Next/Previous patterns (CRITICAL FIX)
            ("current year", "relative", "calendar_year", "Current year - should default to calendar"),
            ("current quarter", "relative", "calendar_quarter", "Current quarter - should default to calendar"),
            ("this year", "relative", "calendar_year", "This year - should default to calendar"),
            ("this quarter", "relative", "calendar_quarter", "This quarter - should default to calendar"),
            ("next year", "relative", "calendar_year", "Next year - should default to calendar"),
            ("next quarter", "relative", "calendar_quarter", "Next quarter - should default to calendar"),
            ("previous year", "relative", "calendar_year", "Previous year - should default to calendar"),
            ("previous quarter", "relative", "calendar_quarter", "Previous quarter - should default to calendar"),
            
            # Short format patterns
            ("FY23", "single", "fiscal_year", "Fiscal year short format"),
            ("CY23", "single", "calendar_year", "Calendar year short format"),
            ("FY24", "single", "fiscal_year", "Fiscal year short format"),
            ("CY24", "single", "calendar_year", "Calendar year short format"),
            
            # Alternative formats (CRITICAL FIX)
            ("2023/2024", "range", "calendar_year", "Year slash format - should default to calendar"),
            ("2023-24", "range", "calendar_year", "Year short format - should default to calendar"),
            ("2024/2025", "range", "calendar_year", "Year slash format - should default to calendar"),
            ("2024-25", "range", "calendar_year", "Year short format - should default to calendar"),
            
            # Month patterns (CRITICAL FIX)
            ("Jan 2023", "single", "calendar_year", "Month year format - should default to calendar"),
            ("January 2023", "single", "calendar_year", "Full month year format - should default to calendar"),
            ("Feb 2024", "single", "calendar_year", "Month year format - should default to calendar"),
            ("February 2024", "single", "calendar_year", "Full month year format - should default to calendar"),
            
            # Half year patterns (CRITICAL FIX)
            ("H1 2023", "single", "calendar_year", "Half year format - should default to calendar"),
            ("H2 2023", "single", "calendar_year", "Half year format - should default to calendar"),
            ("1H 2023", "single", "calendar_year", "Half year format - should default to calendar"),
            ("2H 2023", "single", "calendar_year", "Half year format - should default to calendar"),
            
            # Period patterns (CRITICAL FIX)
            ("YTD 2023", "single", "calendar_year", "Year to date format - should default to calendar"),
            ("MTD 2023", "single", "calendar_year", "Month to date format - should default to calendar"),
            ("QTD 2023", "single", "calendar_year", "Quarter to date format - should default to calendar"),
            ("2023 YTD", "single", "calendar_year", "Year to date format - should default to calendar"),
            ("2023 MTD", "single", "calendar_year", "Month to date format - should default to calendar"),
            ("2023 QTD", "single", "calendar_year", "Quarter to date format - should default to calendar"),
        ]
        
        self.edge_cases = [
            # Case sensitivity
            ("fy2023", "single", "fiscal_year", "Lowercase fiscal year"),
            ("cy2024", "single", "calendar_year", "Lowercase calendar year"),
            ("q1 2023", "single", "calendar_quarter", "Lowercase quarter - should default to calendar"),
            ("FY 2023", "single", "fiscal_year", "Mixed case fiscal year"),
            ("CY 2024", "single", "calendar_year", "Mixed case calendar year"),
            
            # Whitespace variations
            ("  2023  ", "single", "calendar_year", "Year with spaces - should default to calendar"),
            ("  FY2023  ", "single", "fiscal_year", "Fiscal year with spaces"),
            ("  Q1 2023  ", "single", "calendar_quarter", "Quarter with spaces - should default to calendar"),
            ("2023\t", "single", "calendar_year", "Year with tab - should default to calendar"),
            ("FY2023\n", "single", "fiscal_year", "Fiscal year with newline"),
            
            # Special characters
            ("2023!", "single", "calendar_year", "Year with exclamation - should default to calendar"),
            ("FY2023?", "single", "fiscal_year", "Fiscal year with question"),
            ("Q1 2023.", "single", "calendar_quarter", "Quarter with period - should default to calendar"),
            ("2023,", "single", "calendar_year", "Year with comma - should default to calendar"),
            
            # Unicode normalization
            ("2023", "single", "calendar_year", "Year with potential unicode - should default to calendar"),
            ("FY2023", "single", "fiscal_year", "Fiscal year with potential unicode"),
            ("Q1 2023", "single", "calendar_quarter", "Quarter with potential unicode - should default to calendar"),
            
            # Complex phrases
            ("revenue for 2023", "single", "calendar_year", "Year in context - should default to calendar"),
            ("Q1 2023 results", "single", "calendar_quarter", "Quarter in context - should default to calendar"),
            ("FY2023 performance", "single", "fiscal_year", "Fiscal year in context"),
            ("last 3 years of data", "relative", "calendar_year", "Relative in context - should default to calendar"),
        ]
        
        self.integration_cases = [
            # Integration with company names (removing Johnson & Johnson)
            ("Apple revenue 2023", "single", "calendar_year", "Company + metric + year - should default to calendar"),
            ("Microsoft Q1 2024", "single", "calendar_quarter", "Company + quarter - should default to calendar"),
            ("Google FY2023", "single", "fiscal_year", "Company + fiscal year"),
            ("Amazon 2020-2023", "range", "calendar_year", "Company + year range - should default to calendar"),
            
            # Integration with metrics
            ("revenue 2023", "single", "calendar_year", "Metric + year - should default to calendar"),
            ("net income Q1 2024", "single", "calendar_quarter", "Metric + quarter - should default to calendar"),
            ("earnings FY2023", "single", "fiscal_year", "Metric + fiscal year"),
            ("profit 2020-2023", "range", "calendar_year", "Metric + year range - should default to calendar"),
            
            # Integration with actions
            ("show revenue 2023", "single", "calendar_year", "Action + metric + year - should default to calendar"),
            ("display Q1 2024 results", "single", "calendar_quarter", "Action + quarter - should default to calendar"),
            ("get FY2023 data", "single", "fiscal_year", "Action + fiscal year"),
            ("compare 2020-2023", "range", "calendar_year", "Action + year range - should default to calendar"),
            
            # Integration with comparisons
            ("Apple vs Microsoft 2023", "single", "calendar_year", "Comparison + year - should default to calendar"),
            ("revenue vs profit Q1 2024", "single", "calendar_quarter", "Comparison + quarter - should default to calendar"),
            ("growth vs decline FY2023", "single", "fiscal_year", "Comparison + fiscal year"),
            ("performance 2020-2023", "range", "calendar_year", "Comparison + year range - should default to calendar"),
        ]
        
        self.complex_cases = [
            # Complex multi-part queries
            ("Apple revenue and Microsoft profit 2023", "single", "calendar_year", "Multiple companies + metrics + year - should default to calendar"),
            ("Q1 2024 results for Apple and Google", "single", "calendar_quarter", "Quarter + companies - should default to calendar"),
            ("FY2023 performance comparison", "single", "fiscal_year", "Fiscal year + comparison"),
            ("2020-2023 growth analysis", "range", "calendar_year", "Year range + analysis - should default to calendar"),
            
            # Complex relative queries
            ("last 3 years revenue trend", "relative", "calendar_year", "Relative + metric + trend - should default to calendar"),
            ("last 2 quarters growth", "relative", "calendar_quarter", "Relative + metric - should default to calendar"),
            ("current year performance", "relative", "calendar_year", "Current + metric - should default to calendar"),
            ("this quarter results", "relative", "calendar_quarter", "This + metric - should default to calendar"),
            
            # Complex range queries
            ("2020-2023 annual revenue", "range", "calendar_year", "Year range + metric - should default to calendar"),
            ("Q1-Q3 2024 quarterly growth", "range", "calendar_quarter", "Quarter range + metric - should default to calendar"),
            ("FY2020-FY2023 fiscal performance", "range", "fiscal_year", "Fiscal year range + metric"),
            ("CY2020-CY2023 calendar results", "range", "calendar_year", "Calendar year range + metric"),
        ]
    
    def test_fixed_parsing(self) -> Dict[str, Any]:
        """Test fixed time period parsing."""
        
        print("TESTING FIXED TIME PERIOD PARSING")
        print("=" * 80)
        print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        results = []
        
        for input_text, expected_type, expected_granularity, description in self.test_cases:
            try:
                # Test fixed parsing
                parsed = fixed_parse_periods(input_text)
                
                actual_type = parsed.get("type")
                actual_granularity = parsed.get("granularity")
                
                type_match = actual_type == expected_type
                granularity_match = actual_granularity == expected_granularity
                
                if type_match and granularity_match:
                    status = "✅ PASS"
                else:
                    status = "❌ FAIL"
                
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "actual_type": actual_type,
                    "actual_granularity": actual_granularity,
                    "type_match": type_match,
                    "granularity_match": granularity_match,
                    "status": status,
                    "parsed": parsed
                })
                
                print(f"   {status} {input_text:<25} | {expected_type:<10} | {actual_type:<10} | {expected_granularity:<15} | {actual_granularity}")
                
            except Exception as e:
                status = "❌ ERROR"
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "actual_type": f"ERROR: {str(e)}",
                    "actual_granularity": f"ERROR: {str(e)}",
                    "type_match": False,
                    "granularity_match": False,
                    "status": status,
                    "parsed": None
                })
                print(f"   {status} {input_text:<25} | {expected_type:<10} | ERROR: {str(e)}")
        
        print()
        
        # Count results
        passed = sum(1 for r in results if r["status"] == "✅ PASS")
        failed = sum(1 for r in results if r["status"] == "❌ FAIL")
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"   Results: {passed} passed, {failed} failed")
        print(f"   Success Rate: {success_rate:.1f}%")
        print()
        
        return {
            "results": results,
            "passed": passed,
            "failed": failed,
            "total": total,
            "success_rate": success_rate
        }
    
    def test_edge_cases(self) -> Dict[str, Any]:
        """Test edge cases with fixed parsing."""
        
        print("TESTING EDGE CASES WITH FIXED PARSING")
        print("-" * 50)
        
        results = []
        
        for input_text, expected_type, expected_granularity, description in self.edge_cases:
            try:
                # Test fixed parsing
                parsed = fixed_parse_periods(input_text)
                
                actual_type = parsed.get("type")
                actual_granularity = parsed.get("granularity")
                
                type_match = actual_type == expected_type
                granularity_match = actual_granularity == expected_granularity
                
                if type_match and granularity_match:
                    status = "✅ PASS"
                else:
                    status = "❌ FAIL"
                
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "actual_type": actual_type,
                    "actual_granularity": actual_granularity,
                    "type_match": type_match,
                    "granularity_match": granularity_match,
                    "status": status,
                    "parsed": parsed
                })
                
                print(f"   {status} {input_text:<25} | {expected_type:<10} | {actual_type:<10} | {expected_granularity:<15} | {actual_granularity}")
                
            except Exception as e:
                status = "❌ ERROR"
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "actual_type": f"ERROR: {str(e)}",
                    "actual_granularity": f"ERROR: {str(e)}",
                    "type_match": False,
                    "granularity_match": False,
                    "status": status,
                    "parsed": None
                })
                print(f"   {status} {input_text:<25} | {expected_type:<10} | ERROR: {str(e)}")
        
        print()
        
        # Count results
        passed = sum(1 for r in results if r["status"] == "✅ PASS")
        failed = sum(1 for r in results if r["status"] == "❌ FAIL")
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"   Edge Case Results: {passed} passed, {failed} failed")
        print(f"   Edge Case Success Rate: {success_rate:.1f}%")
        print()
        
        return {
            "results": results,
            "passed": passed,
            "failed": failed,
            "total": total,
            "success_rate": success_rate
        }
    
    def test_integration_cases(self) -> Dict[str, Any]:
        """Test integration cases with fixed parsing."""
        
        print("TESTING INTEGRATION CASES WITH FIXED PARSING")
        print("-" * 50)
        
        results = []
        
        for input_text, expected_type, expected_granularity, description in self.integration_cases:
            try:
                # Test fixed parsing
                parsed = fixed_parse_periods(input_text)
                
                actual_type = parsed.get("type")
                actual_granularity = parsed.get("granularity")
                
                type_match = actual_type == expected_type
                granularity_match = actual_granularity == expected_granularity
                
                if type_match and granularity_match:
                    status = "✅ PASS"
                else:
                    status = "❌ FAIL"
                
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "actual_type": actual_type,
                    "actual_granularity": actual_granularity,
                    "type_match": type_match,
                    "granularity_match": granularity_match,
                    "status": status,
                    "parsed": parsed
                })
                
                print(f"   {status} {input_text:<35} | {expected_type:<10} | {actual_type:<10} | {expected_granularity:<15} | {actual_granularity}")
                
            except Exception as e:
                status = "❌ ERROR"
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "actual_type": f"ERROR: {str(e)}",
                    "actual_granularity": f"ERROR: {str(e)}",
                    "type_match": False,
                    "granularity_match": False,
                    "status": status,
                    "parsed": None
                })
                print(f"   {status} {input_text:<35} | {expected_type:<10} | ERROR: {str(e)}")
        
        print()
        
        # Count results
        passed = sum(1 for r in results if r["status"] == "✅ PASS")
        failed = sum(1 for r in results if r["status"] == "❌ FAIL")
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"   Integration Results: {passed} passed, {failed} failed")
        print(f"   Integration Success Rate: {success_rate:.1f}%")
        print()
        
        return {
            "results": results,
            "passed": passed,
            "failed": failed,
            "total": total,
            "success_rate": success_rate
        }
    
    def test_complex_cases(self) -> Dict[str, Any]:
        """Test complex cases with fixed parsing."""
        
        print("TESTING COMPLEX CASES WITH FIXED PARSING")
        print("-" * 50)
        
        results = []
        
        for input_text, expected_type, expected_granularity, description in self.complex_cases:
            try:
                # Test fixed parsing
                parsed = fixed_parse_periods(input_text)
                
                actual_type = parsed.get("type")
                actual_granularity = parsed.get("granularity")
                
                type_match = actual_type == expected_type
                granularity_match = actual_granularity == expected_granularity
                
                if type_match and granularity_match:
                    status = "✅ PASS"
                else:
                    status = "❌ FAIL"
                
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "actual_type": actual_type,
                    "actual_granularity": actual_granularity,
                    "type_match": type_match,
                    "granularity_match": granularity_match,
                    "status": status,
                    "parsed": parsed
                })
                
                print(f"   {status} {input_text:<45} | {expected_type:<10} | {actual_type:<10} | {expected_granularity:<15} | {actual_granularity}")
                
            except Exception as e:
                status = "❌ ERROR"
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "actual_type": f"ERROR: {str(e)}",
                    "actual_granularity": f"ERROR: {str(e)}",
                    "type_match": False,
                    "granularity_match": False,
                    "status": status,
                    "parsed": None
                })
                print(f"   {status} {input_text:<45} | {expected_type:<10} | ERROR: {str(e)}")
        
        print()
        
        # Count results
        passed = sum(1 for r in results if r["status"] == "✅ PASS")
        failed = sum(1 for r in results if r["status"] == "❌ FAIL")
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"   Complex Results: {passed} passed, {failed} failed")
        print(f"   Complex Success Rate: {success_rate:.1f}%")
        print()
        
        return {
            "results": results,
            "passed": passed,
            "failed": failed,
            "total": total,
            "success_rate": success_rate
        }
    
    def compare_original_vs_fixed(self) -> Dict[str, Any]:
        """Compare original vs fixed parsing."""
        
        print("COMPARING ORIGINAL VS FIXED PARSING")
        print("-" * 50)
        
        results = []
        
        for input_text, expected_type, expected_granularity, description in self.test_cases:
            try:
                # Test original parsing
                original_parsed = original_parse_periods(input_text)
                
                # Test fixed parsing
                fixed_parsed = fixed_parse_periods(input_text)
                
                original_type = original_parsed.get("type")
                original_granularity = original_parsed.get("granularity")
                fixed_type = fixed_parsed.get("type")
                fixed_granularity = fixed_parsed.get("granularity")
                
                original_correct = (original_type == expected_type and original_granularity == expected_granularity)
                fixed_correct = (fixed_type == expected_type and fixed_granularity == expected_granularity)
                
                improvement = not original_correct and fixed_correct
                
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "original_type": original_type,
                    "original_granularity": original_granularity,
                    "fixed_type": fixed_type,
                    "fixed_granularity": fixed_granularity,
                    "original_correct": original_correct,
                    "fixed_correct": fixed_correct,
                    "improvement": improvement
                })
                
                improvement_indicator = "📈" if improvement else "➡️"
                print(f"   {improvement_indicator} {input_text:<25} | {expected_type:<10} | {original_type} {original_granularity} → {fixed_type} {fixed_granularity}")
                
            except Exception as e:
                results.append({
                    "input": input_text,
                    "description": description,
                    "expected_type": expected_type,
                    "expected_granularity": expected_granularity,
                    "original_type": f"ERROR: {str(e)}",
                    "original_granularity": f"ERROR: {str(e)}",
                    "fixed_type": f"ERROR: {str(e)}",
                    "fixed_granularity": f"ERROR: {str(e)}",
                    "original_correct": False,
                    "fixed_correct": False,
                    "improvement": False
                })
                print(f"   ❌ {input_text:<25} | {expected_type:<10} | ERROR: {str(e)}")
        
        print()
        
        # Count improvements
        improvements = sum(1 for r in results if r["improvement"])
        total = len(results)
        improvement_rate = (improvements / total * 100) if total > 0 else 0
        
        print(f"   Improvements: {improvements}/{total} ({improvement_rate:.1f}%)")
        print()
        
        return {
            "results": results,
            "improvements": improvements,
            "total": total,
            "improvement_rate": improvement_rate
        }
    
    def generate_fixes_report(self) -> Dict[str, Any]:
        """Generate comprehensive fixes report."""
        
        print("GENERATING FIXES REPORT")
        print("-" * 30)
        
        # Test all categories with fixed parsing
        basic_results = self.test_fixed_parsing()
        edge_results = self.test_edge_cases()
        integration_results = self.test_integration_cases()
        complex_results = self.test_complex_cases()
        
        # Compare with original
        comparison_results = self.compare_original_vs_fixed()
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "basic_results": basic_results,
            "edge_results": edge_results,
            "integration_results": integration_results,
            "complex_results": complex_results,
            "comparison_results": comparison_results,
            "summary": {
                "total_tests": len(self.test_cases + self.edge_cases + self.integration_cases + self.complex_cases),
                "total_passed": (basic_results["passed"] + edge_results["passed"] + 
                               integration_results["passed"] + complex_results["passed"]),
                "total_failed": (basic_results["failed"] + edge_results["failed"] + 
                               integration_results["failed"] + complex_results["failed"]),
                "overall_success_rate": ((basic_results["passed"] + edge_results["passed"] + 
                                        integration_results["passed"] + complex_results["passed"]) / 
                                       (len(self.test_cases + self.edge_cases + self.integration_cases + self.complex_cases)) * 100)
            }
        }
        
        print(f"   Basic Success Rate: {report['basic_results']['success_rate']:.1f}%")
        print(f"   Edge Success Rate: {report['edge_results']['success_rate']:.1f}%")
        print(f"   Integration Success Rate: {report['integration_results']['success_rate']:.1f}%")
        print(f"   Complex Success Rate: {report['complex_results']['success_rate']:.1f}%")
        print(f"   Overall Success Rate: {report['summary']['overall_success_rate']:.1f}%")
        print(f"   Improvements Made: {report['comparison_results']['improvement_rate']:.1f}%")
        print()
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save the fixes report."""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"time_fixes_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"   Report saved to: {filename}")

def main():
    """Test time period parsing fixes."""
    
    tester = TimeFixesTester()
    report = tester.generate_fixes_report()
    tester.save_report(report)
    
    print("=" * 80)
    print("TIME PERIOD PARSING FIXES TESTING COMPLETE")
    print(f"Basic Success Rate: {report['basic_results']['success_rate']:.1f}%")
    print(f"Edge Success Rate: {report['edge_results']['success_rate']:.1f}%")
    print(f"Integration Success Rate: {report['integration_results']['success_rate']:.1f}%")
    print(f"Complex Success Rate: {report['complex_results']['success_rate']:.1f}%")
    print(f"Overall Success Rate: {report['summary']['overall_success_rate']:.1f}%")
    print(f"Improvements Made: {report['comparison_results']['improvement_rate']:.1f}%")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Total Passed: {report['summary']['total_passed']}")
    print(f"Total Failed: {report['summary']['total_failed']}")

if __name__ == "__main__":
    main()
