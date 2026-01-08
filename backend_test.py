#!/usr/bin/env python3
"""
Whisprly Backend API Test Suite
Tests all backend endpoints for the Whisprly conversation assistant app.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Get backend URL from frontend .env
BACKEND_URL = "https://context-aware-5.preview.emergentagent.com/api"

class WhisprlyAPITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        print()

    def test_health_check(self):
        """Test GET /api/ endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                expected_message = "Whisprly API is running"
                expected_version = "1.0.0"
                
                if (data.get("message") == expected_message and 
                    data.get("version") == expected_version):
                    self.log_test("Health Check Endpoint", True, 
                                f"Response: {data}")
                else:
                    self.log_test("Health Check Endpoint", False, 
                                f"Unexpected response: {data}")
            else:
                self.log_test("Health Check Endpoint", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Health Check Endpoint", False, f"Exception: {str(e)}")

    def test_health_status(self):
        """Test GET /api/health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                
                if "status" in data and "timestamp" in data:
                    self.log_test("Health Status Endpoint", True, 
                                f"Status: {data.get('status')}, Timestamp: {data.get('timestamp')}")
                else:
                    self.log_test("Health Status Endpoint", False, 
                                f"Missing required fields: {data}")
            else:
                self.log_test("Health Status Endpoint", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Health Status Endpoint", False, f"Exception: {str(e)}")

    def test_create_session(self, mode: str = "interview"):
        """Test POST /api/sessions endpoint"""
        try:
            payload = {"mode": mode}
            response = self.session.post(f"{self.base_url}/sessions", 
                                       json=payload)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "mode", "context", "created_at", "updated_at"]
                
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields and data.get("mode") == mode:
                    self.log_test(f"Create Session ({mode})", True, 
                                f"Session ID: {data.get('id')}, Mode: {data.get('mode')}")
                    return data.get("id")  # Return session ID for further tests
                else:
                    self.log_test(f"Create Session ({mode})", False, 
                                f"Missing fields: {missing_fields}, Response: {data}")
            else:
                self.log_test(f"Create Session ({mode})", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test(f"Create Session ({mode})", False, f"Exception: {str(e)}")
        
        return None

    def test_get_suggestions(self, mode: str = "interview", session_id: str = None):
        """Test POST /api/suggestions endpoint"""
        try:
            # Use a realistic transcript based on mode
            transcripts = {
                "interview": "Can you tell me about your experience with project management?",
                "business": "We need to discuss the quarterly budget allocation for next year.",
                "sales": "I'm interested in your software solution but I'm concerned about the pricing.",
                "general": "What do you think about the new restaurant that opened downtown?"
            }
            
            transcript = transcripts.get(mode, transcripts["general"])
            
            payload = {
                "transcript": transcript,
                "mode": mode,
                "session_id": session_id or "test-session-123",
                "context": []
            }
            
            response = self.session.post(f"{self.base_url}/suggestions", 
                                       json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                required_fields = ["suggestions", "detected_question", "session_id"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test(f"Get Suggestions ({mode})", False, 
                                f"Missing fields: {missing_fields}")
                    return
                
                # Verify suggestions array
                suggestions = data.get("suggestions", [])
                if len(suggestions) != 3:
                    self.log_test(f"Get Suggestions ({mode})", False, 
                                f"Expected 3 suggestions, got {len(suggestions)}")
                    return
                
                # Verify each suggestion structure
                for i, suggestion in enumerate(suggestions):
                    required_suggestion_fields = ["text", "tone", "priority"]
                    missing_suggestion_fields = [field for field in required_suggestion_fields 
                                               if field not in suggestion]
                    
                    if missing_suggestion_fields:
                        self.log_test(f"Get Suggestions ({mode})", False, 
                                    f"Suggestion {i+1} missing fields: {missing_suggestion_fields}")
                        return
                
                # Verify detected_question is boolean
                if not isinstance(data.get("detected_question"), bool):
                    self.log_test(f"Get Suggestions ({mode})", False, 
                                f"detected_question should be boolean, got {type(data.get('detected_question'))}")
                    return
                
                self.log_test(f"Get Suggestions ({mode})", True, 
                            f"Got {len(suggestions)} suggestions, Question detected: {data.get('detected_question')}")
                
            else:
                self.log_test(f"Get Suggestions ({mode})", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test(f"Get Suggestions ({mode})", False, f"Exception: {str(e)}")

    def test_empty_transcript(self):
        """Test POST /api/suggestions with empty transcript (should return 400)"""
        try:
            payload = {
                "transcript": "",
                "mode": "general",
                "session_id": "test-session-empty",
                "context": []
            }
            
            response = self.session.post(f"{self.base_url}/suggestions", 
                                       json=payload)
            
            if response.status_code == 400:
                self.log_test("Empty Transcript Validation", True, 
                            "Correctly returned 400 for empty transcript")
            else:
                self.log_test("Empty Transcript Validation", False, 
                            f"Expected 400, got {response.status_code}")
                
        except Exception as e:
            self.log_test("Empty Transcript Validation", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all API tests"""
        print(f"🚀 Starting Whisprly API Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Test basic endpoints
        self.test_health_check()
        self.test_health_status()
        
        # Test session creation for all modes
        modes = ["interview", "business", "sales", "general"]
        session_ids = {}
        
        for mode in modes:
            session_id = self.test_create_session(mode)
            if session_id:
                session_ids[mode] = session_id
        
        # Test suggestions for all modes
        for mode in modes:
            session_id = session_ids.get(mode)
            self.test_get_suggestions(mode, session_id)
        
        # Test error handling
        self.test_empty_transcript()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = WhisprlyAPITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Some tests failed!")
        exit(1)