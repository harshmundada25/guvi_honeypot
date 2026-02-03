#!/usr/bin/env python3
"""Comprehensive test suite for GUVI Honeypot v2.0."""
import json
import time
from typing import Any, Dict

import requests

API_URL = "http://localhost:5000/api/honeypot"
API_KEY = "guvi_secret_123"


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def _print(status: str, msg: str) -> None:
    print(f"{status} {msg}{Colors.RESET}")


def call_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=10)
    return {"status": resp.status_code, "json": resp.json()}


def test_api_key_rejection() -> bool:
    headers = {"Content-Type": "application/json", "x-api-key": "bad-key"}
    resp = requests.post(API_URL, json={"message": {"text": "hi"}}, headers=headers, timeout=5)
    ok = resp.status_code == 401
    _print(Colors.GREEN if ok else Colors.RED, f"API key validation -> {resp.status_code}")
    return ok


def test_legitimate_message_safe() -> bool:
    payload = {
        "sessionId": "legit-001",
        "message": {"sender": "bank", "text": "INR 2,500 debited from A/C XXXX1234 on 02-Feb."},
        "conversationHistory": [],
    }
    resp = call_api(payload)
    data = resp["json"]
    ok = resp["status"] == 200 and data.get("scamDetected") is False and data.get("detectionSignals", {}).get("legitimacyScore", 0) >= 0.2
    _print(Colors.GREEN if ok else Colors.RED, "Legitimate bank alert should be SAFE")
    return ok


def test_high_confidence_scam() -> bool:
    payload = {
        "sessionId": "scam-001",
        "message": {
            "sender": "scammer",
            "text": "Your bank account will be blocked immediately! Verify now at https://fake-bank.com",
        },
        "conversationHistory": [],
    }
    resp = call_api(payload)
    data = resp["json"]
    ok = resp["status"] == 200 and data.get("scamDetected") is True
    _print(Colors.GREEN if ok else Colors.RED, "High confidence scam detection")
    return ok


def test_multi_turn_and_callback() -> bool:
    session_id = "multi-001"
    history = []
    turns = [
        ("scammer", "Your bank account is blocked. Verify immediately!"),
        ("user", "Why is it blocked?"),
        ("scammer", "We detected unusual activity. Confirm your UPI ID."),
        ("user", "This sounds odd."),
        ("scammer", "Click https://bad.link and send to scam@upi now"),
    ]
    last_response = {}
    for sender, text in turns:
        payload = {"sessionId": session_id, "message": {"sender": sender, "text": text}, "conversationHistory": history}
        resp = call_api(payload)
        if resp["status"] != 200:
            _print(Colors.RED, f"Turn failed with status {resp['status']}")
            return False
        last_response = resp["json"]
        history.append({"sender": sender, "text": text})
        time.sleep(0.2)
    intel_present = "extractedIntelligence" in last_response and last_response.get("scamDetected")
    _print(Colors.GREEN if intel_present else Colors.RED, "Callback/intelligence triggered after 4+ messages")
    return intel_present


def test_metadata_handling() -> bool:
    payload = {
        "sessionId": "meta-001",
        "message": {"sender": "scammer", "text": "Verify now", "timestamp": "2026-02-03T10:00:00Z"},
        "conversationHistory": [],
        "metadata": {"channel": "SMS", "language": "English"},
    }
    resp = call_api(payload)
    ok = resp["status"] == 200 and "agentReply" in resp["json"]
    _print(Colors.GREEN if ok else Colors.RED, "Metadata handled with normal response")
    return ok


def run_all():
    tests = [
        ("API key validation", test_api_key_rejection),
        ("Legitimate message safe", test_legitimate_message_safe),
        ("High confidence scam", test_high_confidence_scam),
        ("Multi-turn + callback", test_multi_turn_and_callback),
        ("Metadata handling", test_metadata_handling),
    ]
    passed = 0
    for name, func in tests:
        try:
            if func():
                passed += 1
        except Exception as exc:
            _print(Colors.RED, f"{name} crashed: {exc}")
        time.sleep(0.2)
    print(f"\n{Colors.BOLD}Summary: {passed}/{len(tests)} tests passed{Colors.RESET}")


if __name__ == "__main__":
    run_all()
