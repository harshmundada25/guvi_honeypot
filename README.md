# GUVI Honeypot - Agentic Scam Detection System

A production-ready AI-powered honeypot system that detects scam/fraudulent messages, autonomously engages scammers while maintaining a human-like persona, and extracts actionable intelligence.

## 🎯 Key Features

- **Multi-Tier Scam Detection**: Combines heuristic signal scoring, conversation context analysis, and AI semantic analysis
- **Autonomous AI Agent**: Generates human-like responses using GPT-4o-mini with emotional intents
- **Intelligence Extraction**: Automatically extracts UPI IDs, phone numbers, phishing links, bank accounts, and suspicious keywords
- **Mandatory Callback**: Sends extracted intelligence to GUVI evaluation endpoint for scoring
- **Graceful Degradation**: Falls back to heuristics if OpenAI API is unavailable
- **Production-Ready**: Comprehensive error handling, logging, and API security

## 🏗️ Architecture

### Detection Pipeline (Tiered Approach)

```
Message Input
    ↓
Signal Scoring (Heuristics)
    ↓
    ├─ Score ≥ 4 → SCAM ✓
    ├─ Score 2-3 → Check History + AI Analysis
    └─ Score < 2 → NOT_SCAM ✓
```

### Agent Response Generation

```
Scam Detected?
    ├─ Yes: Map turn count to emotional intent
    │       └─ Turn 0-4: confused → seeking confirmation → asking for guidance
    │           └─ Generate response using GPT-4o-mini (temp 0.6)
    └─ No: Generic safe response
```

### Intelligence Extraction & Callback

```
Scam Detected ≥ 4 Messages?
    ├─ Extract: UPI IDs, Phone Numbers, Links, Bank Accounts, Keywords
    └─ POST to https://hackathon.guvi.in/api/updateHoneyPotFinalResult
```

## 📋 API Contract

### Endpoint
```
POST /api/honeypot
Host: your-server:5000
```

### Authentication
```
Header: x-api-key: guvi_secret_123
```

### Request Format

```json
{
  "sessionId": "unique-session-id",
  "message": {
    "sender": "scammer",
    "text": "Your bank account will be blocked today. Verify immediately.",
    "timestamp": "2026-01-21T10:15:30Z"
  },
  "conversationHistory": [
    {
      "sender": "scammer",
      "text": "Previous message...",
      "timestamp": "2026-01-21T10:10:00Z"
    }
  ],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

### Response Format (Success)

```json
{
  "status": "success",
  "sessionId": "unique-session-id",
  "scamDetected": true,
  "engagementMetrics": {
    "engagementDurationSeconds": 42,
    "totalMessagesExchanged": 5
  },
  "extractedIntelligence": {
    "bankAccounts": ["XXXX-XXXX-XXXX"],
    "upiIds": ["attacker@okhdfcbank"],
    "phishingLinks": ["http://malicious-link.example"],
    "phoneNumbers": ["+919876543210"],
    "suspiciousKeywords": ["urgent", "verify", "blocked"]
  },
  "agentReply": "Is this really happening to my account?",
  "agentNotes": "Detected using tiered signal scoring and AI semantic analysis...",
  "historyCount": 4
}
```

### Response Format (Error)

```json
{
  "status": "error",
  "message": "Invalid API key"
}
```

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- OpenAI API key (set as environment variable `OPENAI_API_KEY`)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set OpenAI API Key
```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="your-api-key-here"

# Windows (CMD)
set OPENAI_API_KEY=your-api-key-here

# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"
```

### Step 3: Run the Server
```bash
python app.py
```

You should see:
```
============================================================
🔐 GUVI Honeypot - Scam Detection & Intelligence Extraction
============================================================
✅ API Key: guvi_secret_123
🤖 AI Available: Yes (OpenAI GPT-4o-mini)
🚀 Starting Flask server on http://0.0.0.0:5000
📍 Endpoint: POST /api/honeypot
============================================================
```

## 🧪 Testing

### Test with cURL
```bash
curl -X POST http://localhost:5000/api/honeypot \
  -H "Content-Type: application/json" \
  -H "x-api-key: guvi_secret_123" \
  -d '{
    "sessionId": "test-001",
    "message": {
      "sender": "scammer",
      "text": "Your bank account will be blocked today. Verify immediately."
    },
    "conversationHistory": []
  }'
```

### Test with Python Script
```bash
python test_honeypot.py
```

## 📊 Signal Scoring Weights

| Category | Keywords | Score |
|----------|----------|-------|
| **Urgency/Threat** | urgent, blocked, suspended, deactivated | +2 |
| **Financial Intent** | bank, account, payment, UPI, transfer, refund | +2 |
| **Action Triggers** | click, verify, confirm, submit, login | +1 |
| **Rewards/Lures** | prize, reward, lottery, cashback, free, won | +3 |
| **Phishing Links** | http://, https:// | +3 |

### Decision Rules
- **Score ≥ 4**: Automatic SCAM classification ✓
- **Score 2-3**: Check conversation history + AI semantic analysis
- **Score < 2**: Safe (NOT_SCAM) ✓

## 🧠 AI Semantic Analysis

- **Model**: GPT-4o-mini
- **Temperature**: 0 (deterministic for detection)
- **Context**: System prompt identifies as fraud detection expert
- **Fallback**: Returns False (safe) if OpenAI API fails

## 🎭 Agent Behavior

The autonomous AI Agent maintains a believable persona:

| Conversation Turn | Emotional Intent | Example Response |
|-------------------|------------------|------------------|
| 0 | Confused & worried | "This is confusing, can you explain?" |
| 1 | Needs explanation | "Can you explain this more clearly?" |
| 2 | Suspicious but polite | "This sounds suspicious, but let me understand better." |
| 3 | Seeking confirmation | "Is this really happening to my account?" |
| 4+ | Asking for guidance | "What should I do now?" |

**Temperature**: 0.6 (natural variation for human-like responses)

## 🔍 Intelligence Extraction

### Patterns Detected

| Type | Regex Pattern | Example |
|------|---------------|---------|
| **UPI IDs** | `\b[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\b` | attacker@okhdfcbank |
| **Phone Numbers** | `\+91\d{10}` | +919876543210 |
| **Phishing Links** | `https?://[^\s]+` | http://malicious-link.example |
| **Bank Accounts** | `\d{4}-\d{4}-\d{4}` | XXXX-XXXX-XXXX |
| **Suspicious Keywords** | Hardcoded list | urgent, verify, blocked |

### Extraction Trigger
- Automatically extracted when `scamDetected=true` AND `totalMessages≥4`
- Deduplicated across entire conversation history

## 📤 Mandatory Callback

After sufficient engagement (≥4 messages), the system sends structured intelligence to:

```
POST https://hackathon.guvi.in/api/updateHoneyPotFinalResult
```

**Payload Structure**:
```json
{
  "sessionId": "unique-session-id",
  "scamDetected": true,
  "totalMessagesExchanged": 18,
  "extractedIntelligence": {
    "bankAccounts": ["XXXX-XXXX-XXXX"],
    "upiIds": ["scammer@upi"],
    "phishingLinks": ["http://malicious-link.example"],
    "phoneNumbers": ["+91XXXXXXXXXX"],
    "suspiciousKeywords": ["urgent", "verify", "account blocked"]
  },
  "agentNotes": "Scammer used urgency tactics and payment redirection"
}
```

**Callback Behavior**:
- ✅ Sent after scam confirmation + sufficient engagement
- ✅ Non-blocking (API returns immediately)
- ✅ Logged on success/failure
- ✅ Graceful degradation (doesn't fail main response)

## 🛡️ Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid API Key | Return 401 with error message |
| OpenAI API Down | Fall back to heuristics for detection |
| Callback Timeout | Log warning, continue serving response |
| Malformed Request | Return 500 with error details |

## 🔐 Security

- **API Key Validation**: Required header `x-api-key: guvi_secret_123`
- **Input Sanitization**: Regex patterns prevent injection attacks
- **Rate Limiting**: Not implemented (add if needed)
- **HTTPS**: Use in production with proper SSL certificates

## 📈 Performance

- **Detection Latency**: ~100-500ms (depending on AI invocation)
- **Agent Response Time**: ~500-1000ms (GPT-4o-mini generation)
- **Callback Time**: ~1-5s (non-blocking, async)
- **Memory**: ~50MB base + model weights

## 🎓 Example Workflow

```
1. Platform sends initial scam message
   → Signal score: 6 (urgent + financial + link)
   → SCAM detected immediately
   → Agent responds: "This is confusing, can you explain?"

2. Platform sends follow-up from "scammer"
   → Agent engages: "Can you explain this more clearly?"

3-4. Multi-turn engagement continues

5. After 4+ messages → Extract intelligence
   → Send callback to GUVI with:
      - UPI IDs found
      - Phone numbers found
      - Phishing links found
      - Bank account numbers
      - Suspicious keywords used

6. System continues engagement or waits for new message
```

## 🚨 Constraints & Ethics

✅ **Allowed**:
- Engaging scammers to extract intelligence
- Deceptive responses that don't reveal detection
- Intelligence gathering from conversations
- Autonomous agent behavior

❌ **Forbidden**:
- Impersonation of real individuals
- Illegal instructions to scammers
- Harassment or abuse
- Illegal data collection

## 📝 Logging

The system logs important events to console:

```
📨 Processing message for session: xyz
   Sender: scammer
   History length: 2
📊 Signal score for message: 5
🚨 High confidence scam detected (score >= 4)
💬 Generating reply with intent: seeking confirmation
✅ Generated reply: Is this really happening to my account?
📤 Sending callback to GUVI for session xyz...
✅ Callback sent successfully (Status: 200)
```

## 🔧 Configuration

Edit `app.py` to customize:

```python
API_KEY = "guvi_secret_123"  # Change this for security
CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"  # Or your endpoint
MIN_MESSAGES_FOR_CALLBACK = 4  # Minimum messages before sending callback
```

## 📞 Support

For issues or questions:
1. Check console logs for detailed error messages
2. Verify OpenAI API key is set correctly
3. Ensure Flask server is running on port 5000
4. Test with the provided test script

## 📄 License

This project is built for the GUVI Hackathon.
