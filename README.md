# GUVI Honeypot v2.0 (ML + Agentic Response)

Production-ready honeypot that detects scams with an ML model, engages scammers with a human-like agent, extracts intelligence, and sends GUVI callbacks automatically.

## Highlights
- ML-based detection (RandomForest + TF-IDF + 11 custom features) with legitimacy guard rails to avoid false positives on real bank alerts.
- Modular architecture: models/, gents/, utils/, pp.py.
- Human-like agent responses via Groq (llama-3.1-8b-instant) with template fallback when offline.
- Intelligence extraction (UPI, phone, links, bank accounts, keywords) and mandatory callback after 4+ messages.
- CORS enabled, API key auth, health checks, Docker + Gunicorn ready.

## Architecture
`
app.py
+-- models.scam_detector      # ML model + heuristic guard
+-- agents.response_agent     # AI replies with Groq fallback
+-- utils.intelligence        # Regex-based intelligence extraction
+-- utils.callback            # Non-blocking GUVI callback
`

Detection flow:
`
Message + history
   ?
TF-IDF + custom features ? RandomForest ? scam probability
   ?
Heuristic score + legitimacy score guard
   ?
Scam decision + confidence
`

## API
- POST /api/honeypot
- Headers: Content-Type: application/json, x-api-key: <API_KEY>
- Health: GET /health or GET /

### Request
`json
{
  "sessionId": "abc-123",
  "message": {"sender": "scammer", "text": "Your account will be blocked. Verify at http://bad.link"},
  "conversationHistory": [{"sender": "scammer", "text": "Previous attempt"}],
  "metadata": {"channel": "SMS", "language": "English"}
}
`

### Success Response
`json
{
  "status": "success",
  "sessionId": "abc-123",
  "scamDetected": true,
  "detectionConfidence": 0.81,
  "detectionSignals": {
    "mlProbability": 0.82,
    "heuristicScore": 6,
    "legitimacyScore": 0.0
  },
  "engagementMetrics": {
    "engagementDurationSeconds": 1,
    "totalMessagesExchanged": 5
  },
  "agentReply": "Is this really from the bank?",
  "historyCount": 4,
  "extractedIntelligence": {
    "bankAccounts": ["1234-5678-9012"],
    "upiIds": ["attacker@upi"],
    "phishingLinks": ["https://bad.link"],
    "phoneNumbers": ["+919876543210"],
    "suspiciousKeywords": ["blocked", "verify"]
  },
  "agentNotes": "Scam confirmed via ML probability and heuristic signals. Agent engaged scammer to extract intelligence."
}
`

### Error Response
`json
{"status": "error", "message": "Invalid API key"}
`

## Quickstart
1) Install deps: pip install -r requirements.txt
2) Copy .env.example to .env and set API_KEY, GROQ_API_KEY (optional), PORT.
3) Run locally: python app.py ? POST to http://localhost:5000/api/honeypot.
4) Run demo: python demo_ml_detection.py (no network needed).
5) Run tests (server running): python test_comprehensive.py.

## Deployment
- Gunicorn: gunicorn app:app --bind 0.0.0.0: --timeout 60
- Docker: see DEPLOYMENT.md for Dockerfile usage and cloud notes (Render, Railway, Heroku, AWS EC2).

## Files
- pp.py – Flask API + wiring
- models/scam_detector.py – ML model + training bootstrap
- gents/response_agent.py – Groq + templates
- utils/intelligence.py – extraction helpers
- utils/callback.py – async callback sender
- demo_ml_detection.py – offline demo of ML classifier
- 	est_comprehensive.py – end-to-end tests
- QUICKSTART.md, DEPLOYMENT.md – concise guides

## Verification Checklist
- Dependencies install
- ML model trains/loads on first request
- Legitimate bank notifications stay safe
- Scam messages flagged with confidence
- Callback fires after 4+ messages when scam=true
- Structured JSON matches contract
- Agent replies sound human
- CORS + API key enforced

## Support
Check logs first, then run demo_ml_detection.py, then consult DEPLOYMENT.md for cloud tips.
