#!/usr/bin/env python3
"""
Whisprly v2.0 Backend API Test Suite
Tests all backend endpoints for the conversation assistant app
"""

import requests
import json
import base64
import uuid
from datetime import datetime
import time

# Get backend URL from frontend env
BACKEND_URL = "https://context-aware-5.preview.emergentagent.com/api"

class WhisprlyAPITester:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.note_id = None
        self.suggestion_id = None
        self.test_results = []
        
    def log_test(self, test_name, success, details=""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def test_health_endpoints(self):
        """Test basic health check endpoints"""
        print("\n=== Testing Health Endpoints ===")
        
        # Test root endpoint
        try:
            response = requests.get(f"{BACKEND_URL}/")
            if response.status_code == 200:
                data = response.json()
                self.log_test("GET /api/", True, f"Version: {data.get('version', 'N/A')}")
            else:
                self.log_test("GET /api/", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/", False, f"Error: {str(e)}")
            
        # Test health endpoint
        try:
            response = requests.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test("GET /api/health", True, f"Status: {data.get('status', 'N/A')}")
            else:
                self.log_test("GET /api/health", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/health", False, f"Error: {str(e)}")
    
    def test_transcribe_base64(self):
        """Test POST /api/transcribe-base64 endpoint"""
        print("\n=== Testing Audio Transcription ===")
        
        # Test with empty audio (should fail gracefully)
        try:
            payload = {
                "audio": "",
                "language": "en"
            }
            response = requests.post(f"{BACKEND_URL}/transcribe-base64", json=payload)
            data = response.json()
            # The endpoint returns 200 with success:false and error message for empty audio
            if response.status_code == 200 and not data.get("success", True) and "No audio data provided" in data.get("error", ""):
                self.log_test("POST /api/transcribe-base64 (empty audio)", True, "Correctly rejected empty audio")
            else:
                self.log_test("POST /api/transcribe-base64 (empty audio)", False, f"Status: {response.status_code}, Response: {data}")
        except Exception as e:
            self.log_test("POST /api/transcribe-base64 (empty audio)", False, f"Error: {str(e)}")
            
        # Test with invalid base64 (should fail gracefully)
        try:
            payload = {
                "audio": "invalid_base64_data",
                "language": "en"
            }
            response = requests.post(f"{BACKEND_URL}/transcribe-base64", json=payload)
            data = response.json()
            if response.status_code == 200 and not data.get("success", True):
                self.log_test("POST /api/transcribe-base64 (invalid base64)", True, "Correctly handled invalid base64")
            else:
                self.log_test("POST /api/transcribe-base64 (invalid base64)", False, f"Unexpected response: {data}")
        except Exception as e:
            self.log_test("POST /api/transcribe-base64 (invalid base64)", False, f"Error: {str(e)}")
    
    def test_suggestions_save(self):
        """Test POST /api/suggestions/save endpoint"""
        print("\n=== Testing Save Suggestion ===")
        
        try:
            payload = {
                "session_id": self.session_id,
                "text": "That's an excellent point about market positioning. I'd like to explore how we can leverage our competitive advantages.",
                "tone": "confident",
                "tags": ["business", "strategy", "competitive-analysis"]
            }
            response = requests.post(f"{BACKEND_URL}/suggestions/save", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "timestamp" in data:
                    self.suggestion_id = data["id"]
                    self.log_test("POST /api/suggestions/save", True, f"Saved suggestion with ID: {self.suggestion_id}")
                else:
                    self.log_test("POST /api/suggestions/save", False, "Missing required fields in response")
            else:
                self.log_test("POST /api/suggestions/save", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/suggestions/save", False, f"Error: {str(e)}")
    
    def test_suggestions_get_saved(self):
        """Test GET /api/suggestions/saved/{session_id} endpoint"""
        print("\n=== Testing Get Saved Suggestions ===")
        
        try:
            response = requests.get(f"{BACKEND_URL}/suggestions/saved/{self.session_id}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0 and self.suggestion_id:
                        # Check if our saved suggestion is in the list
                        found = any(s.get("id") == self.suggestion_id for s in data)
                        if found:
                            self.log_test("GET /api/suggestions/saved/{session_id}", True, f"Found {len(data)} saved suggestions")
                        else:
                            self.log_test("GET /api/suggestions/saved/{session_id}", False, "Previously saved suggestion not found")
                    else:
                        self.log_test("GET /api/suggestions/saved/{session_id}", True, "Empty suggestions list (valid)")
                else:
                    self.log_test("GET /api/suggestions/saved/{session_id}", False, "Response is not an array")
            else:
                self.log_test("GET /api/suggestions/saved/{session_id}", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/suggestions/saved/{session_id}", False, f"Error: {str(e)}")
    
    def test_notes_create(self):
        """Test POST /api/notes endpoint"""
        print("\n=== Testing Create Note ===")
        
        try:
            payload = {
                "session_id": self.session_id,
                "text": "Key discussion points from today's meeting:\n- Market expansion strategy for Q2\n- Budget allocation for new initiatives\n- Timeline for product launch"
            }
            response = requests.post(f"{BACKEND_URL}/notes", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "created_at" in data:
                    self.note_id = data["id"]
                    self.log_test("POST /api/notes", True, f"Created note with ID: {self.note_id}")
                else:
                    self.log_test("POST /api/notes", False, "Missing required fields in response")
            else:
                self.log_test("POST /api/notes", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/notes", False, f"Error: {str(e)}")
    
    def test_notes_get(self):
        """Test GET /api/notes/{session_id} endpoint"""
        print("\n=== Testing Get Notes ===")
        
        try:
            response = requests.get(f"{BACKEND_URL}/notes/{self.session_id}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0 and self.note_id:
                        # Check if our created note is in the list
                        found = any(n.get("id") == self.note_id for n in data)
                        if found:
                            self.log_test("GET /api/notes/{session_id}", True, f"Found {len(data)} notes")
                        else:
                            self.log_test("GET /api/notes/{session_id}", False, "Previously created note not found")
                    else:
                        self.log_test("GET /api/notes/{session_id}", True, "Empty notes list (valid)")
                else:
                    self.log_test("GET /api/notes/{session_id}", False, "Response is not an array")
            else:
                self.log_test("GET /api/notes/{session_id}", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/notes/{session_id}", False, f"Error: {str(e)}")
    
    def test_notes_update(self):
        """Test PATCH /api/notes/{note_id} endpoint"""
        print("\n=== Testing Update Note ===")
        
        if not self.note_id:
            self.log_test("PATCH /api/notes/{note_id}", False, "No note ID available for testing")
            return
            
        try:
            payload = {
                "text": "Updated meeting notes:\n- Market expansion strategy for Q2 (approved)\n- Budget allocation for new initiatives ($500K allocated)\n- Timeline for product launch (moved to Q3)\n- Follow-up meeting scheduled for next week"
            }
            response = requests.patch(f"{BACKEND_URL}/notes/{self.note_id}", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "updated_at" in data and data.get("text") == payload["text"]:
                    self.log_test("PATCH /api/notes/{note_id}", True, "Note updated successfully")
                else:
                    self.log_test("PATCH /api/notes/{note_id}", False, "Note update not reflected in response")
            else:
                self.log_test("PATCH /api/notes/{note_id}", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("PATCH /api/notes/{note_id}", False, f"Error: {str(e)}")
    
    def test_sessions_get_history(self):
        """Test GET /api/sessions endpoint"""
        print("\n=== Testing Session History ===")
        
        try:
            response = requests.get(f"{BACKEND_URL}/sessions")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # Check if response includes required fields
                    if len(data) > 0:
                        session = data[0]
                        required_fields = ["id", "mode", "saved_suggestions_count", "notes_count", "created_at"]
                        missing_fields = [field for field in required_fields if field not in session]
                        
                        if not missing_fields:
                            self.log_test("GET /api/sessions", True, f"Found {len(data)} sessions with correct structure")
                        else:
                            self.log_test("GET /api/sessions", False, f"Missing fields: {missing_fields}")
                    else:
                        self.log_test("GET /api/sessions", True, "Empty sessions list (valid)")
                else:
                    self.log_test("GET /api/sessions", False, "Response is not an array")
            else:
                self.log_test("GET /api/sessions", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/sessions", False, f"Error: {str(e)}")
    
    def test_sessions_create(self):
        """Test POST /api/sessions endpoint"""
        print("\n=== Testing Create Session ===")
        
        try:
            payload = {
                "mode": "business"
            }
            response = requests.post(f"{BACKEND_URL}/sessions", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "mode" in data and data["mode"] == "business":
                    self.log_test("POST /api/sessions", True, f"Created session with ID: {data['id']}")
                else:
                    self.log_test("POST /api/sessions", False, "Missing required fields in response")
            else:
                self.log_test("POST /api/sessions", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/sessions", False, f"Error: {str(e)}")
    
    def test_sessions_update(self):
        """Test PATCH /api/sessions/{session_id} endpoint"""
        print("\n=== Testing Update Session ===")
        
        try:
            payload = {
                "transcript_enabled": True,
                "duration": 120
            }
            response = requests.patch(f"{BACKEND_URL}/sessions/{self.session_id}", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("transcript_enabled") == True and data.get("duration") == 120:
                    self.log_test("PATCH /api/sessions/{session_id}", True, "Session updated successfully")
                else:
                    self.log_test("PATCH /api/sessions/{session_id}", False, "Session update not reflected in response")
            else:
                self.log_test("PATCH /api/sessions/{session_id}", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("PATCH /api/sessions/{session_id}", False, f"Error: {str(e)}")
    
    def test_suggestions_endpoint(self):
        """Test POST /api/suggestions endpoint (core functionality)"""
        print("\n=== Testing Get Suggestions ===")
        
        try:
            payload = {
                "transcript": "What are your thoughts on our Q2 marketing strategy and budget allocation?",
                "mode": "business",
                "session_id": self.session_id,
                "context": ["We've been discussing the upcoming product launch timeline."]
            }
            response = requests.post(f"{BACKEND_URL}/suggestions", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["suggestions", "detected_question", "session_id"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    suggestions = data.get("suggestions", [])
                    if len(suggestions) == 3:  # Should return exactly 3 suggestions
                        self.log_test("POST /api/suggestions", True, f"Generated {len(suggestions)} suggestions")
                    else:
                        self.log_test("POST /api/suggestions", False, f"Expected 3 suggestions, got {len(suggestions)}")
                else:
                    self.log_test("POST /api/suggestions", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("POST /api/suggestions", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/suggestions", False, f"Error: {str(e)}")
    
    def test_notes_delete(self):
        """Test DELETE /api/notes/{note_id} endpoint"""
        print("\n=== Testing Delete Note ===")
        
        if not self.note_id:
            self.log_test("DELETE /api/notes/{note_id}", False, "No note ID available for testing")
            return
            
        try:
            response = requests.delete(f"{BACKEND_URL}/notes/{self.note_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_test("DELETE /api/notes/{note_id}", True, "Note deleted successfully")
                else:
                    self.log_test("DELETE /api/notes/{note_id}", False, "No confirmation message in response")
            else:
                self.log_test("DELETE /api/notes/{note_id}", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("DELETE /api/notes/{note_id}", False, f"Error: {str(e)}")
    
    def test_sessions_delete_all(self):
        """Test DELETE /api/sessions endpoint (careful!)"""
        print("\n=== Testing Delete All Sessions (WARNING: Destructive) ===")
        
        # This is a destructive operation, so we'll test it last
        try:
            response = requests.delete(f"{BACKEND_URL}/sessions")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_test("DELETE /api/sessions", True, "All data deleted successfully")
                else:
                    self.log_test("DELETE /api/sessions", False, "No confirmation message in response")
            else:
                self.log_test("DELETE /api/sessions", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("DELETE /api/sessions", False, f"Error: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend API tests"""
        print(f"🚀 Starting Whisprly v2.0 Backend API Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Test Session ID: {self.session_id}")
        print("=" * 60)
        
        # Test in logical order
        self.test_health_endpoints()
        self.test_sessions_create()
        self.test_transcribe_base64()
        self.test_suggestions_endpoint()
        self.test_suggestions_save()
        self.test_suggestions_get_saved()
        self.test_notes_create()
        self.test_notes_get()
        self.test_notes_update()
        self.test_sessions_get_history()
        self.test_sessions_update()
        self.test_notes_delete()
        # Note: Skipping delete_all_sessions to preserve data
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        else:
            print("\n🎉 ALL TESTS PASSED!")
        
        return passed == total

if __name__ == "__main__":
    tester = WhisprlyAPITester()
    success = tester.run_all_tests()
    exit(0 if success else 1)