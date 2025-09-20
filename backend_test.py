#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Secure Exam Platform
Tests all endpoints systematically and verifies data models work correctly with MongoDB
"""

import requests
import json
import uuid
from datetime import datetime, timezone
import sys
import os
import io
import subprocess

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except Exception as e:
        print(f"Error reading frontend .env: {e}")
        return None

BASE_URL = get_backend_url()
if not BASE_URL:
    print("ERROR: Could not get REACT_APP_BACKEND_URL from frontend/.env")
    sys.exit(1)

API_URL = f"{BASE_URL}/api"
print(f"Testing backend API at: {API_URL}")

class ExamPlatformTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_question_id = None
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def log_result(self, test_name, success, message=""):
        if success:
            print(f"✅ {test_name}: PASSED {message}")
            self.results['passed'] += 1
        else:
            print(f"❌ {test_name}: FAILED {message}")
            self.results['failed'] += 1
            self.results['errors'].append(f"{test_name}: {message}")
    
    def test_api_health_check(self):
        """Test 1: Basic API Health Check - Test the root endpoint /api/"""
        try:
            response = self.session.get(f"{API_URL}/")
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "Secure Exam Platform API" in data["message"]:
                    self.log_result("API Health Check", True, f"Response: {data}")
                else:
                    self.log_result("API Health Check", False, f"Unexpected response: {data}")
            else:
                self.log_result("API Health Check", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("API Health Check", False, f"Exception: {str(e)}")
    
    def test_admin_authentication(self):
        """Test 2: Admin Authentication - Test admin login with default credentials"""
        try:
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            response = self.session.post(f"{API_URL}/admin/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "message" in data:
                    self.admin_token = data["token"]
                    self.log_result("Admin Authentication", True, f"Token received: {data['message']}")
                else:
                    self.log_result("Admin Authentication", False, f"Missing token or message in response: {data}")
            else:
                self.log_result("Admin Authentication", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Admin Authentication", False, f"Exception: {str(e)}")
    
    def test_create_mcq_question(self):
        """Test 3a: Question Management - Test creating MCQ questions with all 4 options and correct answer"""
        try:
            question_data = {
                "question_text": "What is the capital of France?",
                "option_a": "London",
                "option_b": "Berlin", 
                "option_c": "Paris",
                "option_d": "Madrid",
                "correct_answer": "C"
            }
            
            response = self.session.post(f"{API_URL}/admin/questions", json=question_data)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer", "created_at"]
                
                if all(field in data for field in required_fields):
                    self.test_question_id = data["id"]  # Store for deletion test
                    self.log_result("Create MCQ Question", True, f"Question created with ID: {data['id']}")
                else:
                    missing_fields = [field for field in required_fields if field not in data]
                    self.log_result("Create MCQ Question", False, f"Missing fields: {missing_fields}")
            else:
                self.log_result("Create MCQ Question", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Create MCQ Question", False, f"Exception: {str(e)}")
    
    def test_fetch_all_questions_admin(self):
        """Test 3b: Question Management - Test fetching all questions from admin panel"""
        try:
            response = self.session.get(f"{API_URL}/admin/questions")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0:
                        # Check if questions have all required fields including correct_answer
                        sample_question = data[0]
                        required_fields = ["id", "question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer"]
                        
                        if all(field in sample_question for field in required_fields):
                            self.log_result("Fetch All Questions (Admin)", True, f"Retrieved {len(data)} questions with correct answers")
                        else:
                            missing_fields = [field for field in required_fields if field not in sample_question]
                            self.log_result("Fetch All Questions (Admin)", False, f"Questions missing fields: {missing_fields}")
                    else:
                        self.log_result("Fetch All Questions (Admin)", True, "No questions found (empty database)")
                else:
                    self.log_result("Fetch All Questions (Admin)", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Fetch All Questions (Admin)", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Fetch All Questions (Admin)", False, f"Exception: {str(e)}")
    
    def test_fetch_exam_questions(self):
        """Test 3c: Question Management - Test fetching exam questions (should not include correct answers)"""
        try:
            response = self.session.get(f"{API_URL}/questions")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0:
                        # Check that correct_answer is NOT included
                        sample_question = data[0]
                        if "correct_answer" not in sample_question:
                            required_fields = ["id", "question_text", "option_a", "option_b", "option_c", "option_d"]
                            if all(field in sample_question for field in required_fields):
                                self.log_result("Fetch Exam Questions", True, f"Retrieved {len(data)} questions without correct answers")
                            else:
                                missing_fields = [field for field in required_fields if field not in sample_question]
                                self.log_result("Fetch Exam Questions", False, f"Questions missing fields: {missing_fields}")
                        else:
                            self.log_result("Fetch Exam Questions", False, "Questions include correct_answer (security issue)")
                    else:
                        self.log_result("Fetch Exam Questions", True, "No questions found (empty database)")
                else:
                    self.log_result("Fetch Exam Questions", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Fetch Exam Questions", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Fetch Exam Questions", False, f"Exception: {str(e)}")
    
    def test_delete_question(self):
        """Test 3d: Question Management - Test deleting questions"""
        if not self.test_question_id:
            self.log_result("Delete Question", False, "No question ID available for deletion test")
            return
        
        try:
            response = self.session.delete(f"{API_URL}/admin/questions/{self.test_question_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "deleted successfully" in data["message"]:
                    self.log_result("Delete Question", True, f"Question deleted: {data['message']}")
                else:
                    self.log_result("Delete Question", False, f"Unexpected response: {data}")
            elif response.status_code == 404:
                self.log_result("Delete Question", False, "Question not found (404)")
            else:
                self.log_result("Delete Question", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Delete Question", False, f"Exception: {str(e)}")
    
    def test_create_exam_log(self):
        """Test 4a: Exam Logging - Test creating exam logs with log_id, timestamp, video URL, and reason"""
        try:
            log_data = {
                "log_id": f"exam_log_{uuid.uuid4()}",
                "video_url": "https://example.com/exam_video_123.mp4",
                "reason": "Suspicious activity detected - multiple browser tabs opened",
                "student_id": "student_12345",
                "exam_session_id": f"session_{uuid.uuid4()}"
            }
            
            response = self.session.post(f"{API_URL}/exam/logs", json=log_data)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "log_id", "timestamp", "video_url", "reason", "student_id", "exam_session_id"]
                
                if all(field in data for field in required_fields):
                    self.log_result("Create Exam Log", True, f"Exam log created with ID: {data['id']}")
                else:
                    missing_fields = [field for field in required_fields if field not in data]
                    self.log_result("Create Exam Log", False, f"Missing fields: {missing_fields}")
            else:
                self.log_result("Create Exam Log", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Create Exam Log", False, f"Exception: {str(e)}")
    
    def test_fetch_exam_logs(self):
        """Test 4b: Exam Logging - Test fetching exam logs"""
        try:
            response = self.session.get(f"{API_URL}/admin/logs")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Fetch Exam Logs", True, f"Retrieved {len(data)} exam logs")
                else:
                    self.log_result("Fetch Exam Logs", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Fetch Exam Logs", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Fetch Exam Logs", False, f"Exception: {str(e)}")
    
    def test_device_check_post(self):
        """Test 5a: Device Check API - Test posting device check results"""
        try:
            device_data = {
                "has_multiple_keyboards": True,
                "has_external_monitors": False,
                "keyboard_count": 2,
                "monitor_count": 1,
                "detected_devices": ["USB Keyboard", "Wireless Mouse", "Built-in Camera"]
            }
            
            response = self.session.post(f"{API_URL}/device/check", json=device_data)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["has_multiple_keyboards", "has_external_monitors", "keyboard_count", "monitor_count", "detected_devices", "check_timestamp"]
                
                if all(field in data for field in required_fields):
                    self.log_result("Post Device Check", True, f"Device check recorded at: {data['check_timestamp']}")
                else:
                    missing_fields = [field for field in required_fields if field not in data]
                    self.log_result("Post Device Check", False, f"Missing fields: {missing_fields}")
            else:
                self.log_result("Post Device Check", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Post Device Check", False, f"Exception: {str(e)}")
    
    def test_fetch_device_checks(self):
        """Test 5b: Device Check API - Test fetching device check results"""
        try:
            response = self.session.get(f"{API_URL}/admin/device-checks")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Fetch Device Checks", True, f"Retrieved {len(data)} device check records")
                else:
                    self.log_result("Fetch Device Checks", False, f"Expected list, got: {type(data)}")
            else:
                self.log_result("Fetch Device Checks", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("Fetch Device Checks", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("=" * 80)
        print("STARTING COMPREHENSIVE BACKEND API TESTING")
        print("=" * 80)
        
        # Test 1: Basic API Health Check
        self.test_api_health_check()
        
        # Test 2: Admin Authentication
        self.test_admin_authentication()
        
        # Test 3: Question Management
        self.test_create_mcq_question()
        self.test_fetch_all_questions_admin()
        self.test_fetch_exam_questions()
        self.test_delete_question()
        
        # Test 4: Exam Logging
        self.test_create_exam_log()
        self.test_fetch_exam_logs()
        
        # Test 5: Device Check API
        self.test_device_check_post()
        self.test_fetch_device_checks()
        
        # Test 6: Speech Detection API
        self.test_speech_detection_with_speech()
        self.test_speech_detection_with_silence()
        self.test_speech_detection_with_non_speech_sound()
        self.test_speech_detection_violation_logging()
        self.test_speech_detection_error_handling()
        self.test_speech_detection_different_formats()
        
        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 TOTAL: {self.results['passed'] + self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 DETAILED ERRORS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = ExamPlatformTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Backend API is working correctly.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {tester.results['failed']} TESTS FAILED! Check the errors above.")
        sys.exit(1)