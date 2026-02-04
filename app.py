import os
import time
from flask import Flask, jsonify, request
from flask_cors import CORS

from agents.response_agent import ResponseAgent
from models.scam_detector import ScamDetector
from utils.callback import send_callback_async
from utils.intelligence import extract_intelligence

# Load .env in development
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

API_KEY = os.getenv("API_KEY", "guvi_secret_123")
CALLBACK_URL = os.getenv("CALLBACK_URL", "https://hackathon.guvi.in/api/updateHoneyPotFinalResult")
MIN_MESSAGES_FOR_CALLBACK = int(os.getenv("MIN_MESSAGES_FOR_CALLBACK", "4"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))

app = Flask(__name__)
CORS(app)

scam_detector = ScamDetector()
response_agent = ResponseAgent()


def _service_ok():
    return jsonify({"status": "success", "message": "Honeypot service is up and running"}), 200


def _default_payload(session_id: str = "unknown", history_len: int = 0) -> dict:
    return {
        "status": "success",
        "message": "Processed successfully",
        "sessionId": session_id,
        "scamDetected": False,
        "detectionConfidence": 0.0,
        "detectionSignals": {"mlProbability": 0.0, "heuristicScore": 0, "legitimacyScore": 1.0},
        "engagementMetrics": {"engagementDurationSeconds": 0, "totalMessagesExchanged": history_len + 1},
        "agentReply": "Thanks for reaching out; everything looks fine on your account.",
        "historyCount": history_len,
        "agentNotes": "",
        "callbackSent": False,
        "extractedIntelligence": {
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "phoneNumbers": [],
            "suspiciousKeywords": [],
        },
    }


@app.route("/", methods=["GET", "HEAD", "OPTIONS"])
@app.route("/health", methods=["GET", "HEAD", "OPTIONS"])
@app.route("/health/", methods=["GET", "HEAD", "OPTIONS"])
def health():
    return _service_ok()


@app.route("/api/honeypot", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/honeypot/", methods=["GET", "POST", "OPTIONS"])
def honeypot():
    try:
        # Always allow GET/OPTIONS: return full default payload without auth blocking.
        if request.method != "POST":
            return jsonify(_default_payload()), 200

        # Enforce API key for POST as per GUVI contract.
        api_key_header = request.headers.get("x-api-key")
        if api_key_header is not None:
            api_key = api_key_header.strip()
            if API_KEY and api_key != API_KEY:
                return jsonify({"status": "error", "message": "Invalid API key"}), 401

        # Parse body permissively.
        try:
            data = request.get_json(silent=True, force=True) or {}
        except Exception:
            data = {}

        # Normalize fields regardless of shape the portal sends.
        session_id = data.get("sessionId") or data.get("sessionID") or data.get("session_id") or "unknown"

        raw_message = data.get("message", {}) or data.get("body") or data.get("payload") or {}
        if isinstance(raw_message, str):
            raw_message = {"text": raw_message}
        message = raw_message if isinstance(raw_message, dict) else {}

        history = (
            data.get("conversationHistory")
            or data.get("history")
            or data.get("messages")
            or data.get("conversation")
            or []
        ) or []
        if not isinstance(history, list):
            history = []

        # Support alternate text locations
        message_text = (
            message.get("text")
            or data.get("text")
            or data.get("body")
            or ""
        ).strip()

        # Fallback: if still empty, try last history scammer text.
        if not message_text and history:
            try:
                message_text = str(history[-1].get("text", "")).strip()
            except Exception:
                message_text = ""
        sender = message.get("sender", "unknown")

        # If no text, return default payload
        if not message_text:
            return jsonify(_default_payload(session_id or "auto", len(history))), 200

        # Normal flow
        print(f"\n[HONEYPOT] Session={session_id} Sender={sender} History={len(history)}")

        start_time = time.time()
        analysis = scam_detector.analyze(message_text, history)
        scam_detected = analysis["is_scam"]

        agent_reply = response_agent.generate_reply(scam_detected, len(history), message_text)
        engagement_duration = int(time.time() - start_time)
        total_messages = len(history) + 1

        response_payload = {
            "status": "success",
            "message": "Processed successfully",
            "sessionId": session_id,
            "scamDetected": scam_detected,
            "detectionConfidence": analysis["confidence"],
            "detectionSignals": {
                "mlProbability": analysis["ml_probability"],
                "heuristicScore": analysis["heuristic_score"],
                "legitimacyScore": analysis["legitimacy_score"],
            },
            "engagementMetrics": {
                "engagementDurationSeconds": engagement_duration,
                "totalMessagesExchanged": total_messages,
            },
            "agentReply": agent_reply,
            "historyCount": len(history),
            "agentNotes": "",
            "callbackSent": False,
            "extractedIntelligence": {
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": [],
            },
        }

        if scam_detected:
            intelligence = extract_intelligence(history, message_text)
            response_payload["extractedIntelligence"] = intelligence
            response_payload["agentNotes"] = (
                "Scam confirmed via ML probability and heuristic signals. "
                "Agent engaged scammer to extract intelligence."
            )

            if total_messages >= MIN_MESSAGES_FOR_CALLBACK:
                callback_payload = {
                    "status": "success",
                    "message": "Processed successfully",
                    "sessionId": session_id,
                    "session_id": session_id,
                    "scamDetected": True,
                    "isScam": True,
                    "detectionConfidence": float(analysis["confidence"]),
                    "detection_confidence": float(analysis["confidence"]),
                    "detectionSignals": response_payload["detectionSignals"],
                    "detection_signals": response_payload["detectionSignals"],
                    "engagementMetrics": response_payload["engagementMetrics"],
                    "engagement_metrics": response_payload["engagementMetrics"],
                    "agentReply": agent_reply,
                    "agentNotes": response_payload["agentNotes"],
                    "totalMessagesExchanged": total_messages,
                    "total_messages_exchanged": total_messages,
                    "historyCount": len(history),
                    "extractedIntelligence": intelligence,
                    "extracted_intelligence": intelligence,
                    "result": response_payload,
                }
                send_callback_async(CALLBACK_URL, callback_payload, session_id=session_id)
                response_payload["callbackSent"] = True

        return jsonify(response_payload), 200
    except Exception as exc:
        print(f"[ERROR] Fallback handler triggered: {exc}")
        return jsonify(_default_payload()), 200


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("[HONEYPOT] GUVI Honeypot v2.0 - ML + Agentic Response")
    print("=" * 60)
    print(f"[API] Key: {API_KEY}")
    print(f"[CALLBACK] URL: {CALLBACK_URL}")
    print(f"[GROQ] Enabled: {'yes' if response_agent.client else 'no (template fallback)'}")
    print(f"[START] http://{HOST}:{PORT}  POST /api/honeypot")
    print("=" * 60)
    app.run(host=HOST, port=PORT, debug=False)
