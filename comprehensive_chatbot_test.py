#!/usr/bin/env python3
"""Comprehensive Real-World Chatbot Testing Suite."""

import sys
import os
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from benchmarkos_chatbot import BenchmarkOSChatbot, load_settings

class ChatbotTester:
    """Comprehensive testing suite for BenchmarkOS chatbot with real-world prompts."""
    
    def __init__(self):
        """Initialize the tester with chatbot instance."""
        self.chatbot = None
        self.results = []
        self.start_time = None
        
    def setup_chatbot(self):
        """Initialize the chatbot instance."""
        try:
            print("🔧 Setting up BenchmarkOS Chatbot...")
            settings = load_settings()
            self.chatbot = BenchmarkOSChatbot.create(settings)
            print("✅ Chatbot initialized successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize chatbot: {e}")
            return False
    
    def test_complex_prompts(self):
        """Test with complex, real-world financial prompts."""
        
        # Complex real-world test cases
        test_cases = [
            # Multi-company comparisons
            {
                "category": "Multi-Company Analysis",
                "prompts": [
                    "Compare Apple, Microsoft, and Google's revenue growth over the last 3 years",
                    "Which tech company has the best profit margins: Apple, Microsoft, or Amazon?",
                    "Show me the debt-to-equity ratios for Tesla, Ford, and GM for 2022 and 2023",
                    "How do the P/E ratios of NVIDIA, AMD, and Intel compare in Q3 2023?"
                ]
            },
            
            # Time period analysis
            {
                "category": "Time Period Analysis", 
                "prompts": [
                    "What was Apple's revenue trend from 2020 to 2023?",
                    "Show me Microsoft's quarterly earnings for the last 2 years",
                    "How has Tesla's stock price performed over the past 5 years?",
                    "Compare Amazon's Q4 performance across 2021, 2022, and 2023"
                ]
            },
            
            # Financial metrics and KPIs
            {
                "category": "Financial Metrics",
                "prompts": [
                    "What is Apple's current ROE and how does it compare to industry average?",
                    "Show me the cash flow from operations for Microsoft for the last 4 quarters",
                    "What are the key profitability ratios for Google in 2023?",
                    "Analyze Tesla's gross margin trends over the past 2 years"
                ]
            },
            
            # Ranking and comparison queries
            {
                "category": "Ranking & Comparison",
                "prompts": [
                    "Which S&P 500 companies have the highest revenue growth in 2023?",
                    "Rank the FAANG stocks by market capitalization",
                    "What are the top 5 most profitable companies in the tech sector?",
                    "Which companies have the best return on assets in the automotive industry?"
                ]
            },
            
            # Complex analytical queries
            {
                "category": "Complex Analytics",
                "prompts": [
                    "Analyze the correlation between Apple's stock price and its quarterly revenue",
                    "What factors contributed to Microsoft's revenue growth in 2023?",
                    "How does Google's advertising revenue compare to its cloud revenue?",
                    "What is the impact of interest rates on Tesla's financial performance?"
                ]
            },
            
            # Industry-specific queries
            {
                "category": "Industry Analysis",
                "prompts": [
                    "Compare the financial health of major banks: JPMorgan, Bank of America, and Wells Fargo",
                    "How do pharmaceutical companies like Pfizer, Moderna, and Johnson & Johnson compare?",
                    "Analyze the energy sector: Exxon, Chevron, and Shell's performance metrics",
                    "What are the key differences between retail giants Walmart, Target, and Amazon?"
                ]
            },
            
            # Edge cases and complex scenarios
            {
                "category": "Edge Cases",
                "prompts": [
                    "Show me the financial data for companies with tickers starting with 'A'",
                    "What happened to GameStop's financials during the meme stock period?",
                    "Compare the performance of electric vehicle companies: Tesla, Rivian, and Lucid",
                    "How do traditional automakers like Ford and GM compare to EV companies?"
                ]
            }
        ]
        
        print("\n🚀 Starting Comprehensive Chatbot Testing...")
        print("=" * 60)
        
        total_tests = sum(len(category["prompts"]) for category in test_cases)
        current_test = 0
        
        for category in test_cases:
            print(f"\n📊 Testing Category: {category['category']}")
            print("-" * 40)
            
            for prompt in category["prompts"]:
                current_test += 1
                print(f"\n[{current_test}/{total_tests}] Testing: {prompt[:60]}...")
                
                result = self._test_single_prompt(prompt, category["category"])
                self.results.append(result)
                
                # Small delay to avoid overwhelming the system
                time.sleep(0.5)
        
        return self.results
    
    def _test_single_prompt(self, prompt: str, category: str) -> Dict[str, Any]:
        """Test a single prompt and return detailed results."""
        start_time = time.time()
        
        try:
            # Send the prompt to the chatbot
            response = self.chatbot.ask(prompt)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Analyze the response
            result = {
                "prompt": prompt,
                "category": category,
                "response": response,
                "response_time": response_time,
                "success": True,
                "error": None,
                "timestamp": datetime.now().isoformat(),
                "response_length": len(response) if response else 0,
                "has_data": self._analyze_response_content(response)
            }
            
            print(f"✅ Success ({response_time:.2f}s) - Response length: {result['response_length']}")
            
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            result = {
                "prompt": prompt,
                "category": category,
                "response": None,
                "response_time": response_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "response_length": 0,
                "has_data": False
            }
            
            print(f"❌ Failed ({response_time:.2f}s) - Error: {str(e)[:50]}...")
        
        return result
    
    def _analyze_response_content(self, response: str) -> Dict[str, Any]:
        """Analyze the response content for data quality indicators."""
        if not response:
            return {"has_tables": False, "has_numbers": False, "has_comparisons": False}
        
        # Check for various data indicators
        has_tables = "|" in response or "table" in response.lower()
        has_numbers = any(char.isdigit() for char in response)
        has_comparisons = any(word in response.lower() for word in ["compare", "vs", "versus", "better", "higher", "lower"])
        has_metrics = any(word in response.lower() for word in ["revenue", "profit", "margin", "ratio", "growth", "earnings"])
        
        return {
            "has_tables": has_tables,
            "has_numbers": has_numbers,
            "has_comparisons": has_comparisons,
            "has_metrics": has_metrics
        }
    
    def generate_report(self):
        """Generate a comprehensive test report."""
        if not self.results:
            print("❌ No test results available!")
            return
        
        # Calculate statistics
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests) * 100
        
        # Calculate average response time
        avg_response_time = sum(r["response_time"] for r in self.results) / total_tests
        
        # Category-wise analysis
        category_stats = {}
        for result in self.results:
            category = result["category"]
            if category not in category_stats:
                category_stats[category] = {"total": 0, "success": 0, "avg_time": 0}
            
            category_stats[category]["total"] += 1
            if result["success"]:
                category_stats[category]["success"] += 1
        
        # Calculate category success rates
        for category in category_stats:
            stats = category_stats[category]
            stats["success_rate"] = (stats["success"] / stats["total"]) * 100
            stats["avg_time"] = sum(r["response_time"] for r in self.results 
                                   if r["category"] == category) / stats["total"]
        
        # Generate report
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "average_response_time": avg_response_time,
                "test_timestamp": datetime.now().isoformat()
            },
            "category_analysis": category_stats,
            "detailed_results": self.results
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE CHATBOT TEST REPORT")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests} ({success_rate:.1f}%)")
        print(f"Failed: {failed_tests}")
        print(f"Average Response Time: {avg_response_time:.2f}s")
        
        print("\n📈 Category Performance:")
        for category, stats in category_stats.items():
            print(f"  {category}: {stats['success_rate']:.1f}% success, {stats['avg_time']:.2f}s avg")
        
        # Save detailed report
        report_filename = f"chatbot_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_filename}")
        
        return report

def main():
    """Main testing function."""
    print("🤖 BenchmarkOS Chatbot Comprehensive Testing Suite")
    print("=" * 60)
    
    tester = ChatbotTester()
    
    # Setup chatbot
    if not tester.setup_chatbot():
        print("❌ Failed to setup chatbot. Exiting.")
        return
    
    # Run comprehensive tests
    print("\n🧪 Running comprehensive real-world tests...")
    tester.test_complex_prompts()
    
    # Generate and display report
    tester.generate_report()
    
    print("\n🎉 Testing completed!")

if __name__ == "__main__":
    main()
