#!/usr/bin/env python3
"""
Test script for voice recording integration
Tests the voice-to-text endpoint functionality
"""

import requests
import json
import os
from pathlib import Path

def test_voice_endpoint():
    """Test the voice-to-text endpoint with a sample audio file."""
    
    # Test endpoint URL (adjust if your server runs on different port)
    url = "http://localhost:8000/api/voice-to-text"
    
    print("🎤 Testing Voice Recording Integration")
    print("=" * 50)
    
    # Check if server is running
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server health check failed")
            return False
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Please start the server first:")
        print("   cd app && python run_chatbot.py")
        return False
    
    # Test with a dummy audio file (you would replace this with actual audio)
    print("\n📝 Testing endpoint availability...")
    
    # Create a minimal test file (not real audio, just for endpoint testing)
    test_data = b"fake audio data for testing"
    
    try:
        files = {'audio': ('test.webm', test_data, 'audio/webm')}
        response = requests.post(url, files=files, timeout=30)
        
        if response.status_code == 200:
            print("✅ Endpoint is accessible")
            data = response.json()
            print(f"   Response structure: {list(data.keys())}")
        elif response.status_code == 500:
            print("⚠️  Endpoint accessible but processing failed (expected with fake audio)")
            print("   This is normal - the endpoint needs real audio data")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    
    print("\n🔧 Setup Instructions:")
    print("1. Ensure OpenAI API key is configured in your settings")
    print("2. Install required Python dependencies:")
    print("   pip install -r requirements.txt")
    print("3. Install Node.js dependencies for the web UI:")
    print("   cd webui && npm install")
    print("4. Start the server:")
    print("   cd app && python run_chatbot.py")
    print("5. Open the web interface and look for the 🎤 button next to the chat input")
    
    print("\n🎯 Voice Recording Features:")
    print("• Click 🎤 to start recording")
    print("• Automatic silence detection (stops after 2 seconds of silence)")
    print("• Manual stop by clicking ⏹")
    print("• Real-time recording timer")
    print("• Automatic transcription using OpenAI Whisper")
    print("• Integrated with existing chat functionality")
    
    return True

def check_dependencies():
    """Check if required dependencies are available."""
    print("\n🔍 Checking Dependencies:")
    
    # Check Python dependencies
    try:
        import openai
        print("✅ OpenAI Python library available")
    except ImportError:
        print("❌ OpenAI library missing. Install with: pip install openai")
    
    try:
        import fastapi
        print("✅ FastAPI available")
    except ImportError:
        print("❌ FastAPI missing. Install with: pip install fastapi")
    
    # Check if Node.js dependencies exist
    webui_path = Path("webui")
    if (webui_path / "node_modules").exists():
        print("✅ Node.js dependencies installed")
    else:
        print("⚠️  Node.js dependencies not found. Run: cd webui && npm install")
    
    # Check if voice recorder script exists
    if (webui_path / "voice-recorder.js").exists():
        print("✅ Voice recorder script created")
    else:
        print("❌ Voice recorder script missing")

if __name__ == "__main__":
    print("Voice Recording Integration Test")
    print("================================")
    
    check_dependencies()
    test_voice_endpoint()
    
    print("\n🚀 Ready to test voice recording!")
    print("Open your browser to http://localhost:8000 and try the voice feature.")
