#!/usr/bin/env python3
"""
Backend API Test Suite for Seun M. Olawepo's Portfolio Website
Tests all API endpoints and validates data integrity
"""

import requests
import json
import os
from datetime import datetime
from typing import Dict, Any, List

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/app/frontend/.env')

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://agile-portfolio.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class PortfolioAPITester:
    def __init__(self):
        self.base_url = API_BASE
        self.test_results = []
        self.failed_tests = []
        
    def log_test(self, test_name: str, success: bool, message: str, data: Any = None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.test_results.append(result)
        if not success:
            self.failed_tests.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        
    def test_health_check(self):
        """Test basic health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "Portfolio API" in data["message"]:
                    self.log_test("Health Check", True, "API is responding correctly", data)
                    return True
                else:
                    self.log_test("Health Check", False, f"Unexpected response format: {data}")
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
        return False
    
    def test_database_seeding(self):
        """Test database seeding endpoint"""
        try:
            response = requests.post(f"{self.base_url}/seed", timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Database Seeding", True, "Database seeded successfully", data)
                    return True
                else:
                    self.log_test("Database Seeding", False, f"Seeding failed: {data.get('message', 'Unknown error')}")
            else:
                self.log_test("Database Seeding", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Database Seeding", False, f"Error: {str(e)}")
        return False
    
    def test_hero_data(self):
        """Test hero section API"""
        try:
            response = requests.get(f"{self.base_url}/portfolio/hero", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Validate required fields
                required_fields = ['name', 'short_title', 'long_title', 'bio']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Hero Data", False, f"Missing required fields: {missing_fields}")
                    return False
                
                # Validate specific content
                if data.get('name') == "Seun M. Olawepo" and "Senior Agile & Cloud Applications Leader" in data.get('short_title', ''):
                    self.log_test("Hero Data", True, "Hero data retrieved and validated successfully", {
                        'name': data.get('name'),
                        'title': data.get('short_title')
                    })
                    return True
                else:
                    self.log_test("Hero Data", False, f"Content validation failed. Name: {data.get('name')}, Title: {data.get('short_title')}")
            else:
                self.log_test("Hero Data", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Hero Data", False, f"Error: {str(e)}")
        return False
    
    def test_about_data(self):
        """Test about section API"""
        try:
            response = requests.get(f"{self.base_url}/portfolio/about", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Validate structure
                if 'short' in data and 'long' in data and 'key_stats' in data:
                    # Validate key stats
                    key_stats = data.get('key_stats', [])
                    if len(key_stats) >= 4:
                        stats_labels = [stat.get('label') for stat in key_stats]
                        expected_stats = ['Years Experience', 'Budget Managed', 'Teams Mentored', 'Delivery Improvement']
                        
                        if all(stat in stats_labels for stat in expected_stats):
                            self.log_test("About Data", True, "About data structure and content validated", {
                                'stats_count': len(key_stats),
                                'stats_labels': stats_labels
                            })
                            return True
                        else:
                            self.log_test("About Data", False, f"Missing expected stats. Found: {stats_labels}")
                    else:
                        self.log_test("About Data", False, f"Insufficient key stats. Expected 4+, got {len(key_stats)}")
                else:
                    self.log_test("About Data", False, "Missing required fields: short, long, or key_stats")
            else:
                self.log_test("About Data", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("About Data", False, f"Error: {str(e)}")
        return False
    
    def test_projects_data(self):
        """Test projects API with filtering"""
        try:
            # Test all projects
            response = requests.get(f"{self.base_url}/portfolio/projects", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'projects' in data and 'total' in data and 'filtered' in data:
                    projects = data['projects']
                    
                    # Validate we have expected number of projects (6 case studies)
                    if len(projects) >= 6:
                        # Validate project structure
                        first_project = projects[0]
                        required_fields = ['title', 'category', 'problem', 'role', 'approach', 'outcomes', 'metrics']
                        missing_fields = [field for field in required_fields if field not in first_project]
                        
                        if not missing_fields:
                            self.log_test("Projects Data", True, f"Retrieved {len(projects)} projects with valid structure", {
                                'total_projects': len(projects),
                                'first_project_title': first_project.get('title')
                            })
                            
                            # Test filtering by category
                            return self.test_project_filtering()
                        else:
                            self.log_test("Projects Data", False, f"Project missing required fields: {missing_fields}")
                    else:
                        self.log_test("Projects Data", False, f"Expected 6+ projects, got {len(projects)}")
                else:
                    self.log_test("Projects Data", False, "Response missing required fields: projects, total, filtered")
            else:
                self.log_test("Projects Data", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Projects Data", False, f"Error: {str(e)}")
        return False
    
    def test_project_filtering(self):
        """Test project filtering by category and tag"""
        try:
            # Test category filtering
            categories_to_test = ["Agile Leadership", "Product Management", "Release Train Engineering"]
            
            for category in categories_to_test:
                response = requests.get(f"{self.base_url}/portfolio/projects?category={category}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    projects = data.get('projects', [])
                    
                    # Validate all returned projects match the category
                    if projects:
                        category_match = all(project.get('category') == category for project in projects)
                        if category_match:
                            self.log_test(f"Project Filtering - {category}", True, f"Found {len(projects)} projects in category", {
                                'category': category,
                                'count': len(projects)
                            })
                        else:
                            self.log_test(f"Project Filtering - {category}", False, "Some projects don't match category filter")
                            return False
                    else:
                        self.log_test(f"Project Filtering - {category}", False, f"No projects found for category: {category}")
                        return False
                else:
                    self.log_test(f"Project Filtering - {category}", False, f"HTTP {response.status_code}")
                    return False
            
            # Test tag filtering
            response = requests.get(f"{self.base_url}/portfolio/projects?tag=SAFe", timeout=10)
            if response.status_code == 200:
                data = response.json()
                projects = data.get('projects', [])
                if projects:
                    safe_projects = [p for p in projects if 'SAFe' in p.get('tags', [])]
                    if len(safe_projects) == len(projects):
                        self.log_test("Project Filtering - Tags", True, f"Found {len(projects)} projects with SAFe tag")
                        return True
                    else:
                        self.log_test("Project Filtering - Tags", False, "Tag filtering not working correctly")
                else:
                    self.log_test("Project Filtering - Tags", False, "No projects found with SAFe tag")
            else:
                self.log_test("Project Filtering - Tags", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Project Filtering", False, f"Error: {str(e)}")
        return False
    
    def test_experience_data(self):
        """Test experience API"""
        try:
            response = requests.get(f"{self.base_url}/portfolio/experience", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list) and len(data) >= 6:
                    # Validate experience structure
                    first_exp = data[0]
                    required_fields = ['company', 'role', 'period', 'achievements']
                    missing_fields = [field for field in required_fields if field not in first_exp]
                    
                    if not missing_fields:
                        # Check for expected companies
                        companies = [exp.get('company') for exp in data]
                        expected_companies = ['TSPi', 'Fidelity Investments', 'UnitedHealth Group', 'Mastercard']
                        
                        found_companies = [comp for comp in expected_companies if comp in companies]
                        if len(found_companies) >= 3:
                            self.log_test("Experience Data", True, f"Retrieved {len(data)} experience entries with expected companies", {
                                'total_entries': len(data),
                                'companies_found': found_companies
                            })
                            return True
                        else:
                            self.log_test("Experience Data", False, f"Missing expected companies. Found: {companies}")
                    else:
                        self.log_test("Experience Data", False, f"Experience missing required fields: {missing_fields}")
                else:
                    self.log_test("Experience Data", False, f"Expected list with 6+ entries, got {type(data)} with {len(data) if isinstance(data, list) else 'N/A'} entries")
            else:
                self.log_test("Experience Data", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Experience Data", False, f"Error: {str(e)}")
        return False
    
    def test_skills_data(self):
        """Test skills API"""
        try:
            response = requests.get(f"{self.base_url}/portfolio/skills", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'skills' in data:
                    skills = data['skills']
                    expected_categories = ['Agile Frameworks', 'Leadership & Delivery', 'Cloud & DevOps', 'Tools & Platforms', 'Business Analysis', 'Technical']
                    
                    found_categories = [cat for cat in expected_categories if cat in skills]
                    if len(found_categories) >= 5:
                        # Validate some specific skills
                        agile_skills = skills.get('Agile Frameworks', [])
                        if 'SAFe (Scaled Agile Framework)' in agile_skills and 'Scrum' in agile_skills:
                            self.log_test("Skills Data", True, f"Skills data validated with {len(found_categories)} categories", {
                                'categories_found': found_categories,
                                'agile_skills_count': len(agile_skills)
                            })
                            return True
                        else:
                            self.log_test("Skills Data", False, f"Missing expected Agile skills. Found: {agile_skills}")
                    else:
                        self.log_test("Skills Data", False, f"Missing skill categories. Expected 5+, found: {found_categories}")
                else:
                    self.log_test("Skills Data", False, "Response missing 'skills' field")
            else:
                self.log_test("Skills Data", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Skills Data", False, f"Error: {str(e)}")
        return False
    
    def test_certifications_data(self):
        """Test certifications API"""
        try:
            response = requests.get(f"{self.base_url}/portfolio/certifications", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'certifications' in data and 'education' in data:
                    certifications = data['certifications']
                    education = data['education']
                    
                    # Validate certifications
                    expected_certs = ['PMP', 'PSM', 'CSM', 'SAFe RTE', 'AWS Cloud Practitioner']
                    cert_names = [cert.get('name', '') for cert in certifications]
                    
                    found_certs = [cert for cert in expected_certs if any(cert in name for name in cert_names)]
                    
                    if len(found_certs) >= 4:
                        # Validate education
                        if len(education) >= 2:
                            degrees = [edu.get('degree') for edu in education]
                            if 'Master of Science' in degrees:
                                self.log_test("Certifications Data", True, f"Validated {len(certifications)} certifications and {len(education)} education entries", {
                                    'certifications_count': len(certifications),
                                    'education_count': len(education),
                                    'found_certs': found_certs
                                })
                                return True
                            else:
                                self.log_test("Certifications Data", False, f"Missing expected Master's degree. Found: {degrees}")
                        else:
                            self.log_test("Certifications Data", False, f"Expected 2+ education entries, got {len(education)}")
                    else:
                        self.log_test("Certifications Data", False, f"Missing expected certifications. Found: {found_certs}")
                else:
                    self.log_test("Certifications Data", False, "Response missing 'certifications' or 'education' fields")
            else:
                self.log_test("Certifications Data", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Certifications Data", False, f"Error: {str(e)}")
        return False
    
    def test_contact_info(self):
        """Test contact info API"""
        try:
            response = requests.get(f"{self.base_url}/portfolio/contact", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                required_fields = ['email', 'availability']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    if data.get('email') == 'seunolawepo2010@gmail.com' and '8am' in data.get('availability', '') and '5pm CST' in data.get('availability', ''):
                        self.log_test("Contact Info", True, "Contact information validated", {
                            'email': data.get('email'),
                            'availability': data.get('availability')
                        })
                        return True
                    else:
                        self.log_test("Contact Info", False, f"Contact details don't match expected values. Email: {data.get('email')}, Availability: {data.get('availability')}")
                else:
                    self.log_test("Contact Info", False, f"Missing required fields: {missing_fields}")
            else:
                self.log_test("Contact Info", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Contact Info", False, f"Error: {str(e)}")
        return False
    
    def test_contact_message_submission(self):
        """Test contact form submission"""
        try:
            test_message = {
                "name": "John Smith",
                "email": "john.smith@example.com",
                "subject": "Portfolio Inquiry",
                "message": "I'm interested in discussing potential collaboration opportunities. Your experience with SAFe and Agile transformation aligns well with our current needs.",
                "availability_preference": "Morning meetings preferred"
            }
            
            response = requests.post(f"{self.base_url}/contact/message", json=test_message, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and 'message_id' in data.get('data', {}):
                    message_id = data['data']['message_id']
                    self.log_test("Contact Message Submission", True, "Contact message submitted successfully", {
                        'message_id': message_id,
                        'response_message': data.get('message')
                    })
                    
                    # Test retrieving the message
                    return self.test_contact_messages_retrieval()
                else:
                    self.log_test("Contact Message Submission", False, f"Unexpected response format: {data}")
            else:
                self.log_test("Contact Message Submission", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Contact Message Submission", False, f"Error: {str(e)}")
        return False
    
    def test_contact_messages_retrieval(self):
        """Test retrieving contact messages (admin endpoint)"""
        try:
            response = requests.get(f"{self.base_url}/contact/messages", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'messages' in data and 'total' in data:
                    messages = data['messages']
                    if len(messages) > 0:
                        # Check if our test message is there
                        test_message_found = any(msg.get('email') == 'john.smith@example.com' for msg in messages)
                        if test_message_found:
                            self.log_test("Contact Messages Retrieval", True, f"Retrieved {len(messages)} contact messages including test message", {
                                'total_messages': len(messages)
                            })
                            return True
                        else:
                            self.log_test("Contact Messages Retrieval", False, "Test message not found in retrieved messages")
                    else:
                        self.log_test("Contact Messages Retrieval", False, "No messages found")
                else:
                    self.log_test("Contact Messages Retrieval", False, "Response missing 'messages' or 'total' fields")
            else:
                self.log_test("Contact Messages Retrieval", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Contact Messages Retrieval", False, f"Error: {str(e)}")
        return False
    
    def test_contact_info_endpoint(self):
        """Test contact info endpoint (different from portfolio contact)"""
        try:
            response = requests.get(f"{self.base_url}/contact/info", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'email' in data:
                    self.log_test("Contact Info Endpoint", True, "Contact info endpoint working", data)
                    return True
                else:
                    self.log_test("Contact Info Endpoint", False, "Contact info endpoint missing email field")
            else:
                self.log_test("Contact Info Endpoint", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Contact Info Endpoint", False, f"Error: {str(e)}")
        return False
    
    def run_all_tests(self):
        """Run all API tests"""
        print(f"\n🚀 Starting Portfolio API Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("Database Seeding", self.test_database_seeding),
            ("Hero Data", self.test_hero_data),
            ("About Data", self.test_about_data),
            ("Projects Data", self.test_projects_data),
            ("Experience Data", self.test_experience_data),
            ("Skills Data", self.test_skills_data),
            ("Certifications Data", self.test_certifications_data),
            ("Contact Info", self.test_contact_info),
            ("Contact Message Submission", self.test_contact_message_submission),
            ("Contact Info Endpoint", self.test_contact_info_endpoint),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                self.log_test(test_name, False, f"Test execution error: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for failed in self.failed_tests:
                print(f"  - {failed['test']}: {failed['message']}")
        
        return passed == total

def main():
    """Main test execution"""
    tester = PortfolioAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/test_results_detailed.json', 'w') as f:
        json.dump(tester.test_results, f, indent=2, default=str)
    
    print(f"\n📝 Detailed results saved to: /app/test_results_detailed.json")
    
    if success:
        print("\n🎉 All tests passed! Backend API is working correctly.")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Check the detailed results above.")
        return 1

if __name__ == "__main__":
    exit(main())