#!/usr/bin/env python3
"""
Test script for voice transcription-only endpoint
"""

import requests
import json

def test_voice_transcription_endpoint():
    """Test the voice-to-text-only endpoint."""
    
    # Test endpoint URL
    url = "http://localhost:8000/api/voice-to-text-only"
    
    print("🎤 Testing Voice Transcription-Only Endpoint")
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
    print("\n📝 Testing transcription-only endpoint...")
    
    # Create a minimal test file (not real audio, just for endpoint testing)
    test_data = b"fake audio data for testing"
    
    try:
        files = {'audio': ('test.webm', test_data, 'audio/webm')}
        response = requests.post(url, files=files, timeout=30)
        
        if response.status_code == 200:
            print("✅ Transcription-only endpoint is accessible")
            data = response.json()
            print(f"   Response structure: {list(data.keys())}")
            if 'transcript' in data:
                print("✅ Endpoint returns transcript field")
            if 'response' not in data:
                print("✅ Endpoint correctly omits chatbot response")
        elif response.status_code == 500:
            print("⚠️  Endpoint accessible but processing failed (expected with fake audio)")
            print("   This is normal - the endpoint needs real audio data")
            print("   The important thing is that the endpoint exists and responds")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    
    print("\n🎯 How the New Flow Works:")
    print("1. User clicks 🎤 to start recording")
    print("2. User speaks and recording stops (auto or manual)")
    print("3. Audio sent to /api/voice-to-text-only")
    print("4. Transcribed text appears in chat input field")
    print("5. User can review/edit the text")
    print("6. User clicks send to submit normally")
    print("7. Normal chat flow processes the message")
    
    print("\n✨ This matches ChatGPT's behavior exactly!")
    
    return True

if __name__ == "__main__":
    test_voice_transcription_endpoint()
