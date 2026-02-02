from flask import Flask, request, jsonify
import re
import requests
import os
import time
import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Load .env so GROQ_API_KEY etc. work when running from IDE or without exporting
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ===================== SETUP =====================

app = Flask(__name__)

ai_available = False
groq_client = None

_groq_key = (os.getenv("GROQ_API_KEY") or "").strip()
if not _groq_key:
    print("[TIP] GROQ_API_KEY not set. In PowerShell use: $env:GROQ_API_KEY = \"gsk_...\"")
    print("      Or create a .env file with: GROQ_API_KEY=gsk_your_key")
if _groq_key:
    try:
        from groq import Groq
        groq_client = Groq(api_key=_groq_key)
        ai_available = True
        print("[OK] Groq API initialized (free tier)")
    except ImportError:
        groq_client = None
        print("[INFO] Install groq: pip install groq")
    except Exception as e:
        groq_client = None
        print(f"[INFO] Groq init failed: {e}")

if not ai_available:
    print("[INFO] No AI provider. Using heuristic detection + template replies.")

API_KEY = "guvi_secret_123"

# ===================== BASIC HELPERS =====================

def contains_link(text):
    return bool(re.search(r"https?://", text))

def contains_urgency(text):
    urgency_words = ["urgent", "immediately", "asap", "within", "hurry", "quick", "fast", "now", "today", "tonight"]
    return any(word in text.lower() for word in urgency_words)

# ===================== SCAM SIGNAL SCORING =====================

def scam_signal_score(text: str) -> int:
    """
    Heuristic scoring for scam signals:
    - Urgency markers: +2
    - Financial terms: +2
    - Action triggers: +1
    - Reward/prize language: +2
    - Links: +3 (phishing indicator)
    """
    score = 0
    text_lower = text.lower()
    
    # Urgency/threat
    urgency_signals = ["urgent", "immediately", "within", "blocked", "suspended", "deactivated", 
                       "limited", "unusual activity", "suspicious", "disruption", "avoid"]
    if any(signal in text_lower for signal in urgency_signals):
        score += 2
    
    # Financial intent
    financial_signals = ["bank", "account", "payment", "transfer", "refund", "upi", "credit", "debit"]
    if any(signal in text_lower for signal in financial_signals):
        score += 2
    
    # Action triggers
    action_signals = ["restore", "reactivate", "verify", "confirm", "submit", "update", "click", "login", "respond"]
    if any(signal in text_lower for signal in action_signals):
        score += 1
    
    # Rewards/prize language
    reward_signals = ["prize", "reward", "lottery", "cashback", "free", "offer", "won", "claim", "bonus"]
    if any(signal in text_lower for signal in reward_signals):
        score += 2
    
    # Links (phishing indicator)
    if contains_link(text):
        score += 3
    
    return score

# ===================== GROQ HELPER =====================

def _groq_chat(system: str, user_content: str, max_tokens: int = 50) -> str:
    """Call Groq chat completions. Uses free-tier model."""
    if not groq_client:
        return ""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=0.6,
            max_tokens=max_tokens,
            timeout=10,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[WARN] Groq chat failed: {e}")
        return ""


# ===================== AI SCAM DETECTION =====================

def ai_is_scam(message_text: str) -> bool:
    """Use Groq for semantic scam analysis."""
    if not ai_available or not groq_client:
        print("[WARN] Groq not available, using heuristics only")
        return False
    try:
        print("[INFO] Calling Groq for semantic analysis...")
        result = _groq_chat(
            "You are a fraud detection expert. Reply with only one word: SCAM or NOT_SCAM.",
            f"Classify this message: {message_text}",
            max_tokens=10
        ).upper()
        print(f"[OK] Groq result: {result}")
        return "SCAM" in result
    except Exception as e:
        print(f"[ERROR] Groq scam detection failed: {type(e).__name__}: {e}")
    return False

# ===================== CONVERSATION SCAM DETECTION =====================

def conversation_is_scam(current_text: str, history: List[Dict]) -> bool:
    """
    Tiered decision-making for scam classification:
    1. Score >= 4: Automatic SCAM
    2. Score 2-3: Check history for patterns + AI analysis
    3. Score < 2: Safe (NOT_SCAM)
    """
    score = scam_signal_score(current_text)
    print(f"[INFO] Signal score for message: {score}")
    
    # High confidence scam
    if score >= 4:
        print("[WARN] High confidence scam detected (score >= 4)")
        return True
    
    # Medium confidence: check history for scammer patterns
    if score >= 2:
        for msg in history:
            if msg.get("sender") == "scammer":
                hist_score = scam_signal_score(msg.get("text", ""))
                if hist_score >= 2:
                    print("[WARN] Scam pattern found in history")
                    return True
        
        # Invoke AI for semantic analysis
        print("[INFO] Score in medium range, asking AI for semantic analysis...")
        result = ai_is_scam(current_text)
        if result:
            print("[WARN] AI classified as SCAM")
            return True
    
    # Low signal -> safe
    print("[OK] Low signal - classified as safe")
    return False

# ===================== TEMPLATE FALLBACK (no API needed) =====================

# Multiple templates per intent for variety; used when no AI provider is available
_TEMPLATES = {
    "confused and worried": [
        "I'm confused and worried, what does this mean?",
        "This is worrying. Can you explain what's going on?",
        "I'm a bit worried. What exactly do you mean?",
    ],
    "needs explanation": [
        "Can you explain this more clearly?",
        "I didn't get that. Could you explain in simple terms?",
        "Can you tell me more about what I need to do?",
    ],
    "suspicious but polite": [
        "This sounds a bit suspicious, but let me understand better.",
        "I want to understand. Can you clarify the steps?",
        "Okay, but I need a bit more detail before I do anything.",
    ],
    "seeking confirmation": [
        "Is this really happening to my account?",
        "Are you sure this is from the bank?",
        "How do I know this is legitimate?",
    ],
    "asking for guidance": [
        "What should I do now?",
        "What are the exact steps I need to follow?",
        "I'm not sure what to do next. Can you guide me?",
    ],
}


def _template_reply(intent: str, last_scammer_text: str = "") -> str:
    """Pick a varied, context-appropriate reply from templates (no API)."""
    options = _TEMPLATES.get(intent, _TEMPLATES["asking for guidance"])
    # Optional: prefer templates that match keywords in scammer message
    text_lower = (last_scammer_text or "").lower()
    if "upi" in text_lower or "share" in text_lower:
        prefer = [o for o in options if "step" in o.lower() or "do" in o.lower() or "guide" in o.lower()]
        if prefer:
            options = prefer
    if "verify" in text_lower or "confirm" in text_lower:
        prefer = [o for o in options if "explain" in o.lower() or "clarify" in o.lower() or "detail" in o.lower()]
        if prefer:
            options = prefer
    return random.choice(options)


# ===================== AI AGENT REPLY =====================

def ai_agent_reply(intent: str, last_scammer_text: str = "") -> str:
    """Generate human-like replies using Groq or template fallback."""
    def _clean_reply(reply: str) -> str:
        reply = (reply or "").split("\n")[0].strip()
        reply = re.sub(r'[\"\*]', '', reply)
        words = reply.split()
        if len(words) > 15:
            reply = " ".join(words[:15])
        return reply

    if ai_available and groq_client:
        try:
            print(f"[INFO] Generating reply with intent: {intent}")
            reply = _groq_chat(
                "You are a worried bank customer. Reply in one short sentence (max 15 words). Be human-like and cautious. Do not use quotes or bullet points.",
                f"Respond as the customer expressing: {intent}",
                max_tokens=50
            )
            if reply and len(reply) >= 3:
                reply = _clean_reply(reply)
                if reply:
                    print(f"[OK] Generated reply: {reply}")
                    return reply
        except Exception as e:
            print(f"[WARN] Groq reply failed: {type(e).__name__}: {e}")

    print("[INFO] Using template fallback for reply")
    return _template_reply(intent, last_scammer_text)

# ===================== AGENT RESPONSE MAPPING =====================

def agent_reply(is_scam: bool, conversation_depth: int, last_scammer_text: str = "") -> str:
    """Map conversation depth to emotional intents for natural engagement"""
    
    if not is_scam:
        return "Thanks for letting me know, I appreciate the information."
    
    # Progressive intents based on conversation depth
    intents = {
        0: "confused and worried",
        1: "needs explanation",
        2: "suspicious but polite",
        3: "seeking confirmation",
        4: "asking for guidance",
    }
    
    intent = intents.get(min(conversation_depth, 4), "asking for guidance")
    print(f"[INFO] AI intent for depth {conversation_depth}: {intent}")
    
    return ai_agent_reply(intent, last_scammer_text)

# ===================== INTELLIGENCE EXTRACTION =====================

def extract_intelligence(history: List[Dict], current_message: str) -> Dict:
    """Extract actionable intelligence: UPI IDs, phone numbers, phishing links, accounts"""
    
    bank_accounts = []
    upi_ids = []
    phishing_links = []
    phone_numbers = []
    suspicious_keywords = []
    
    # Combine all scammer messages
    full_text = current_message
    for msg in history:
        if msg.get("sender") == "scammer":
            full_text += " " + msg.get("text", "")
    
    # Extract patterns
    if full_text:
        # Bank account numbers (4-4-4 format)
        bank_accounts += re.findall(r"\d{4}-\d{4}-\d{4}", full_text)
        
        # UPI IDs (word@word format)
        upi_ids += re.findall(r"\b[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\b", full_text)
        
        # Phishing links
        phishing_links += re.findall(r"https?://[^\s]+", full_text)
        
        # Phone numbers (+91XXXXXXXXXX format)
        phone_numbers += re.findall(r"\+91\d{10}", full_text)
    
    # Extract suspicious keywords
    suspicious_keywords_list = [
        "urgent", "immediately", "within", "blocked", "suspended", 
        "deactivated", "limited", "unusual activity", "suspicious", 
        "disruption", "avoid", "restore", "reactivate", "verify", 
        "confirm", "submit", "update", "click", "login", "respond",
        "upi", "bank", "account", "payment", "transfer", "refund",
        "prize", "reward", "lottery", "cashback", "free", "offer", "won"
    ]
    
    for keyword in suspicious_keywords_list:
        if keyword in full_text:
            suspicious_keywords.append(keyword)
    
    return {
        "bankAccounts": list(set(bank_accounts)),
        "upiIds": list(set(upi_ids)),
        "phishingLinks": list(set(phishing_links)),
        "phoneNumbers": list(set(phone_numbers)),
        "suspiciousKeywords": list(set(suspicious_keywords))
    }

# ===================== API ENDPOINT =====================
@app.route("/", methods=["GET", "POST", "HEAD", "OPTIONS"])
def root_health_check():
    return jsonify({
        "status": "success",
        "message": "Honeypot service is up and running"
    }), 200


@app.route("/api/honeypot", methods=["GET", "POST", "HEAD", "OPTIONS"])
def honeypot():
    """Main honeypot endpoint for scam detection and agentic engagement"""

    # API Key validation
    api_key = request.headers.get("x-api-key")
    if api_key != API_KEY:
        return jsonify({
            "status": "error",
            "message": "Invalid API key"
        }), 401

    # ✅ GUVI tester safety: handle non-JSON / empty / probe requests
    if not request.is_json:
        return jsonify({
            "status": "success",
            "message": "Honeypot API reachable and authenticated successfully"
        }), 200

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict) or "message" not in data:
            return jsonify({
                "status": "success",
                "message": "Honeypot API reachable and authenticated successfully"
            }), 200

        # -------- REAL HONEYPOT LOGIC (UNCHANGED) --------

        session_id = data.get("sessionId", "unknown")
        message = data.get("message", {})
        message_text = message.get("text", "")
        history = data.get("conversationHistory", [])

        print(f"\n[INFO] Processing message for session: {session_id}")
        print(f"    Sender: {message.get('sender', 'unknown')}")
        print(f"    History length: {len(history)}")

        start_time = time.time()
        scam_detected = conversation_is_scam(message_text, history)
        agent_response = agent_reply(scam_detected, len(history), message_text)

        engagement_duration = int(time.time() - start_time)
        total_messages = len(history) + 1

        response_payload = {
            "status": "success",
            "sessionId": session_id,
            "scamDetected": scam_detected,
            "engagementMetrics": {
                "engagementDurationSeconds": engagement_duration,
                "totalMessagesExchanged": total_messages
            },
            "agentReply": agent_response,
            "historyCount": len(history)
        }

        if scam_detected and total_messages >= 4:
            intelligence = extract_intelligence(history, message_text)

            response_payload["extractedIntelligence"] = intelligence
            response_payload["agentNotes"] = (
                "Detected using tiered signal scoring and Groq semantic analysis. "
                "Agent engaged scammer and extracted actionable intelligence."
            )

            try:
                requests.post(
                    "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
                    json={
                        "sessionId": session_id,
                        "scamDetected": True,
                        "totalMessagesExchanged": total_messages,
                        "extractedIntelligence": intelligence,
                        "agentNotes": response_payload["agentNotes"]
                    },
                    timeout=5
                )
            except Exception as e:
                print(f"[WARN] Callback issue: {e}")

        return jsonify(response_payload), 200

    except Exception as e:
        print(f"[ERROR] Honeypot endpoint error: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


# ===================== SERVER INITIALIZATION =====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("[HONEYPOT] GUVI Honeypot - Scam Detection & Intelligence Extraction")
    print("="*60)
    print(f"[OK] API Key: {API_KEY}")
    print(f"[INFO] AI (Groq): {'Yes' if ai_available else 'No (templates only)'}")
    print(f"[START] Starting Flask server on http://0.0.0.0:5000")
    print(f"[ENDPOINT] Endpoint: POST /api/honeypot")
    print("="*60 + "\n")
    
    app.run(host="0.0.0.0", port=5000, debug=False)
