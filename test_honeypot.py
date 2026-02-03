#!/usr/bin/env python3
"""
Test script for GUVI Honeypot system
Tests various scam scenarios and validates API responses
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
API_URL = "http://localhost:5000/api/honeypot"
API_KEY = "guvi_secret_123"

# ANSI colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}[PASS] {text}{Colors.RESET}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}[FAIL] {text}{Colors.RESET}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}[INFO] {text}{Colors.RESET}")

def test_api(test_name: str, payload: Dict[str, Any]) -> bool:
    """Send test request to API and validate response"""
    
    print_info(f"Testing: {test_name}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": API_KEY
        }
        
        start_time = time.time()
        response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
        elapsed = time.time() - start_time
        
        print_info(f"Response Time: {elapsed:.2f}s")
        print_info(f"Status Code: {response.status_code}")
        
        # Check response
        if response.status_code not in [200, 401, 500]:
            print_error(f"Unexpected status code: {response.status_code}")
            return False
        
        try:
            data = response.json()
            print_info(f"Response:\n{json.dumps(data, indent=2)}")
            
            # Validate response structure for success responses
            if response.status_code == 200:
                required_fields = ["status", "sessionId", "scamDetected", "engagementMetrics", "agentReply"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    print_error(f"Missing fields: {missing}")
                    return False
                
                print_success(f"Response valid. Scam detected: {data['scamDetected']}")
                return True
            else:
                print_error(f"API returned error: {data.get('message', 'Unknown error')}")
                return False
                
        except json.JSONDecodeError:
            print_error("Response is not valid JSON")
            return False
        
    except requests.exceptions.Timeout:
        print_error("Request timeout (10s)")
        return False
    except requests.exceptions.ConnectionError as e:
        print_error(f"Connection error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def test_api_key_validation():
    """Test 1: API Key Validation"""
    print_header("Test 1: API Key Validation")
    
    payload = {
        "sessionId": "test-001",
        "message": {
            "sender": "scammer",
            "text": "Your account is blocked"
        },
        "conversationHistory": []
    }
    
    # Try with invalid key
    print_info("Testing with invalid API key...")
    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": "invalid_key_12345"
        }
        response = requests.post(API_URL, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 401:
            print_success("Invalid API key correctly rejected (401)")
            return True
        else:
            print_error(f"Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_high_confidence_scam():
    """Test 2: High Confidence Scam Detection"""
    print_header("Test 2: High Confidence Scam Detection")
    
    # Scam message with multiple signals (urgency + financial + link)
    payload = {
        "sessionId": "test-scam-001",
        "message": {
            "sender": "scammer",
            "text": "Your bank account will be blocked immediately! Verify now at https://fake-bank.com. Click immediately!"
        },
        "conversationHistory": []
    }
    
    return test_api("High confidence scam (score >= 4)", payload)

def test_medium_confidence_scam():
    """Test 3: Medium Confidence Scam with History"""
    print_header("Test 3: Medium Confidence Scam (Score 2-3)")
    
    # Medium signal message with scam history
    payload = {
        "sessionId": "test-scam-002",
        "message": {
            "sender": "scammer",
            "text": "Share your UPI ID to verify your account"
        },
        "conversationHistory": [
            {
                "sender": "scammer",
                "text": "Your account needs urgent verification"
            },
            {
                "sender": "user",
                "text": "Why do I need to verify?"
            }
        ]
    }
    
    return test_api("Medium confidence scam with history", payload)

def test_safe_message():
    """Test 4: Safe Message Detection"""
    print_header("Test 4: Safe Message Detection")
    
    # Benign message
    payload = {
        "sessionId": "test-safe-001",
        "message": {
            "sender": "scammer",
            "text": "Hello, how are you doing today?"
        },
        "conversationHistory": []
    }
    
    return test_api("Safe message detection", payload)

def test_multi_turn_conversation():
    """Test 5: Multi-Turn Conversation Engagement"""
    print_header("Test 5: Multi-Turn Conversation Engagement")
    
    # Simulate multi-turn conversation
    print_info("Simulating 4-turn conversation...")
    
    session_id = "test-multi-turn-001"
    conversation = [
        ("Your bank account is blocked. Verify immediately!", "scammer"),
        ("Why is my account blocked?", "user"),
        ("We detected unusual activity. Confirm your UPI ID.", "scammer"),
        ("I'm confused, what should I do?", "user")
    ]
    
    history = []
    
    for i, (text, sender) in enumerate(conversation):
        print_info(f"Turn {i+1}: {sender} - {text[:50]}...")
        
        payload = {
            "sessionId": session_id,
            "message": {
                "sender": sender,
                "text": text
            },
            "conversationHistory": history.copy()
        }
        
        try:
            headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
            response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Turn {i+1}: scamDetected={data['scamDetected']}, reply={data['agentReply'][:40]}...")
                
                # Update history for next turn
                history.append({"sender": sender, "text": text})
            else:
                print_error(f"Turn {i+1} failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Turn {i+1} error: {e}")
            return False
    
    print_success("Multi-turn conversation completed successfully")
    return True

def test_intelligence_extraction():
    """Test 6: Intelligence Extraction from Scam Messages"""
    print_header("Test 6: Intelligence Extraction")
    
    # Message with multiple intelligence patterns
    payload = {
        "sessionId": "test-intel-001",
        "message": {
            "sender": "scammer",
            "text": "Send money to attacker@paytm. Call +919876543210 or visit https://malicious-site.com. Account 1234-5678-9012"
        },
        "conversationHistory": [
            {"sender": "scammer", "text": "Your account is blocked. Urgent verification needed!"},
            {"sender": "user", "text": "What should I do?"},
            {"sender": "scammer", "text": "Send payment to attacker@upi immediately"},
            {"sender": "user", "text": "How much should I send?"}
        ]
    }
    
    print_info("Testing intelligence extraction with 4+ message history...")
    
    try:
        headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
        response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "extractedIntelligence" in data:
                intel = data["extractedIntelligence"]
                print_success("Intelligence extracted:")
                print(f"  UPI IDs: {intel.get('upiIds', [])}")
                print(f"  Phone Numbers: {intel.get('phoneNumbers', [])}")
                print(f"  Phishing Links: {intel.get('phishingLinks', [])}")
                print(f"  Bank Accounts: {intel.get('bankAccounts', [])}")
                print(f"  Keywords: {intel.get('suspiciousKeywords', [])[:5]}...")
                return True
            else:
                print_error("No intelligence extracted in response")
                return False
        else:
            print_error(f"Request failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_metadata_handling():
    """Test 7: Request with Optional Metadata"""
    print_header("Test 7: Optional Metadata Handling")
    
    payload = {
        "sessionId": "test-meta-001",
        "message": {
            "sender": "scammer",
            "text": "Verify your account immediately or it will be suspended!",
            "timestamp": "2026-01-21T10:15:30Z"
        },
        "conversationHistory": [],
        "metadata": {
            "channel": "SMS",
            "language": "English",
            "locale": "IN"
        }
    }
    
    return test_api("Request with metadata", payload)

def main():
    """Run all tests"""
    print_header("GUVI Honeypot - Comprehensive Test Suite")
    print_info(f"API URL: {API_URL}")
    print_info("Ensure the Flask server is running before executing tests")
    
    # Wait a moment for user to prepare
    time.sleep(1)
    
    tests = [
        ("API Key Validation", test_api_key_validation),
        ("High Confidence Scam", test_high_confidence_scam),
        ("Medium Confidence Scam", test_medium_confidence_scam),
        ("Safe Message", test_safe_message),
        ("Multi-Turn Conversation", test_multi_turn_conversation),
        ("Intelligence Extraction", test_intelligence_extraction),
        ("Metadata Handling", test_metadata_handling),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results[test_name] = False
        
        time.sleep(0.5)  # Small delay between tests
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {status} - {test_name}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] All tests passed!{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}[WARN] Some tests failed. Check logs above.{Colors.RESET}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_info("\nTests interrupted by user")
    except Exception as e:
        print_error(f"Fatal error: {e}")
