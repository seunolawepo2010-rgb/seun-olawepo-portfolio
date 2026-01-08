#!/usr/bin/env python3
"""
Focused test for specific review request scenarios
"""

import requests
import json
import base64
from datetime import datetime

BACKEND_URL = "https://realtalk-assist.preview.emergentagent.com/api"

def log_test(test_name, status, details=""):
    """Log test results with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"[{timestamp}] {status_symbol} {test_name}")
    if details:
        print(f"    {details}")
    print()

def test_health_check():
    """Test GET /api/health - should return healthy status"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "status" in data and data["status"] == "healthy":
                log_test("Health Check", "PASS", f"Status: {data['status']}")
                return True
            else:
                log_test("Health Check", "FAIL", f"Invalid response: {data}")
                return False
        else:
            log_test("Health Check", "FAIL", f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        log_test("Health Check", "FAIL", f"Exception: {str(e)}")
        return False

def test_transcription_empty_audio():
    """Test with empty audio data - should return error 'No audio data provided'"""
    try:
        payload = {"audio": "", "language": "en"}
        response = requests.post(f"{BACKEND_URL}/transcribe-base64", 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if (data.get("success") == False and 
                "No audio data provided" in data.get("error", "")):
                log_test("Transcription - Empty Audio Error", "PASS", 
                        f"Correctly returned: {data}")
                return True
            else:
                log_test("Transcription - Empty Audio Error", "FAIL", 
                        f"Unexpected response: {data}")
                return False
        else:
            log_test("Transcription - Empty Audio Error", "FAIL", 
                    f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        log_test("Transcription - Empty Audio Error", "FAIL", f"Exception: {str(e)}")
        return False

def test_transcription_short_audio():
    """Test with very short audio - should return error containing 'Audio too short'"""
    try:
        # Create short base64 string (less than 1000 chars)
        short_audio = base64.b64encode(b"short_audio_data").decode()
        
        payload = {"audio": short_audio, "language": "en"}
        response = requests.post(f"{BACKEND_URL}/transcribe-base64", 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if (data.get("success") == False and 
                "Audio too short" in data.get("error", "")):
                log_test("Transcription - Short Audio Error", "PASS", 
                        f"Correctly returned: {data}")
                return True
            else:
                log_test("Transcription - Short Audio Error", "FAIL", 
                        f"Unexpected response: {data}")
                return False
        else:
            log_test("Transcription - Short Audio Error", "FAIL", 
                    f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        log_test("Transcription - Short Audio Error", "FAIL", f"Exception: {str(e)}")
        return False

def test_transcription_invalid_base64():
    """Test with invalid base64 - should handle gracefully"""
    try:
        # Create long but invalid base64 string
        invalid_audio = "invalid_base64_data_that_is_long_enough" * 50  # Make it long enough
        
        payload = {"audio": invalid_audio, "language": "en"}
        response = requests.post(f"{BACKEND_URL}/transcribe-base64", 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Should handle gracefully with error response
            if data.get("success") == False and "error" in data:
                log_test("Transcription - Invalid Base64", "PASS", 
                        f"Gracefully handled: {data}")
                return True
            else:
                log_test("Transcription - Invalid Base64", "FAIL", 
                        f"Unexpected response: {data}")
                return False
        else:
            log_test("Transcription - Invalid Base64", "FAIL", 
                    f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        log_test("Transcription - Invalid Base64", "FAIL", f"Exception: {str(e)}")
        return False

def test_suggestions_interview_mode():
    """Test suggestion generation for Interview mode"""
    try:
        payload = {
            "transcript": "Can you tell me about your experience with project management?",
            "mode": "interview",
            "session_id": "test-interview-1"
        }
        
        response = requests.post(f"{BACKEND_URL}/suggestions", 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            suggestions = data.get("suggestions", [])
            
            if (len(suggestions) == 3 and 
                all("text" in s and "tone" in s and "priority" in s for s in suggestions)):
                log_test("Suggestions - Interview Mode", "PASS", 
                        f"Generated 3 suggestions: {[s['text'][:50]+'...' for s in suggestions]}")
                return True
            else:
                log_test("Suggestions - Interview Mode", "FAIL", 
                        f"Invalid suggestions structure: {data}")
                return False
        else:
            log_test("Suggestions - Interview Mode", "FAIL", 
                    f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        log_test("Suggestions - Interview Mode", "FAIL", f"Exception: {str(e)}")
        return False

def test_suggestions_business_mode():
    """Test suggestion generation for Business mode"""
    try:
        payload = {
            "transcript": "What are your thoughts on the budget proposal?",
            "mode": "business",
            "session_id": "test-business-2"
        }
        
        response = requests.post(f"{BACKEND_URL}/suggestions", 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            suggestions = data.get("suggestions", [])
            
            if (len(suggestions) == 3 and 
                all("text" in s and "tone" in s and "priority" in s for s in suggestions)):
                log_test("Suggestions - Business Mode", "PASS", 
                        f"Generated 3 suggestions: {[s['text'][:50]+'...' for s in suggestions]}")
                return True
            else:
                log_test("Suggestions - Business Mode", "FAIL", 
                        f"Invalid suggestions structure: {data}")
                return False
        else:
            log_test("Suggestions - Business Mode", "FAIL", 
                    f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        log_test("Suggestions - Business Mode", "FAIL", f"Exception: {str(e)}")
        return False

def test_create_session():
    """Test session creation"""
    try:
        payload = {"mode": "interview"}
        
        response = requests.post(f"{BACKEND_URL}/sessions", 
                               json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if ("id" in data and "mode" in data and 
                data["mode"] == "interview"):
                log_test("Create Session", "PASS", 
                        f"Created session: {data}")
                return True, data["id"]
            else:
                log_test("Create Session", "FAIL", 
                        f"Invalid session structure: {data}")
                return False, None
        else:
            log_test("Create Session", "FAIL", 
                    f"HTTP {response.status_code}: {response.text}")
            return False, None
            
    except Exception as e:
        log_test("Create Session", "FAIL", f"Exception: {str(e)}")
        return False, None

def test_get_sessions():
    """Test session listing"""
    try:
        response = requests.get(f"{BACKEND_URL}/sessions", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                log_test("Get Sessions", "PASS", 
                        f"Retrieved {len(data)} sessions")
                return True
            else:
                log_test("Get Sessions", "FAIL", 
                        f"Expected list, got: {type(data)}")
                return False
        else:
            log_test("Get Sessions", "FAIL", 
                    f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        log_test("Get Sessions", "FAIL", f"Exception: {str(e)}")
        return False

def main():
    """Run focused tests based on review request"""
    print("=" * 70)
    print("WHISPRLY BACKEND API - FOCUSED TEST SUITE")
    print("Testing specific scenarios from review request")
    print("=" * 70)
    print(f"Backend URL: {BACKEND_URL}")
    print()
    
    results = []
    
    # Priority Test Cases from review request:
    
    print("🔍 PRIORITY TEST CASES:")
    print()
    
    # 1. Health Check
    results.append(test_health_check())
    
    # 2. Transcription Error Handling
    results.append(test_transcription_empty_audio())
    results.append(test_transcription_short_audio())
    results.append(test_transcription_invalid_base64())
    
    # 3. Suggestion Generation
    results.append(test_suggestions_interview_mode())
    results.append(test_suggestions_business_mode())
    
    # 4. Session Management
    session_created, session_id = test_create_session()
    results.append(session_created)
    results.append(test_get_sessions())
    
    # Summary
    print("=" * 70)
    print("FOCUSED TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL PRIORITY TESTS PASSED!")
        print("✅ Health check working")
        print("✅ Transcription error handling working")
        print("✅ Suggestion generation working for Interview and Business modes")
        print("✅ Session management working")
        print("\nBackend is ready for Interview and Business modes!")
    else:
        print(f"\n⚠️  {total-passed} test(s) failed. Check logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    main()