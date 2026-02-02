# Postman Test Cases – Honeypot API

**Base URL:** `http://localhost:5000`  
**Endpoint:** `POST /api/honeypot`  
**Headers (all requests):**
- `Content-Type`: `application/json`
- `x-api-key`: `guvi_secret_123`

Start the app with `python app.py` before testing.

---

## 1. Bank account block scam (first message)

**Expected:** `scamDetected: true`, agent reply like a worried customer.

```json
{
  "sessionId": "postman-bank-001",
  "message": {
    "sender": "scammer",
    "text": "Your bank account will be blocked today. Verify immediately to avoid suspension.",
    "timestamp": "2026-02-01T10:15:30Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

---

## 2. UPI / share details scam (first message)

**Expected:** `scamDetected: true`.

```json
{
  "sessionId": "postman-upi-001",
  "message": {
    "sender": "scammer",
    "text": "Share your UPI ID to avoid account suspension. Reply within 1 hour.",
    "timestamp": "2026-02-01T10:17:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "WhatsApp",
    "language": "English",
    "locale": "IN"
  }
}
```

---

## 3. Phishing link scam (first message)

**Expected:** `scamDetected: true` (link + urgency).

```json
{
  "sessionId": "postman-phish-001",
  "message": {
    "sender": "scammer",
    "text": "Urgent: Your card has been locked. Click here to restore: https://fake-bank-verify.com/secure",
    "timestamp": "2026-02-01T10:20:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "Email",
    "language": "English",
    "locale": "IN"
  }
}
```

---

## 4. Prize / lottery scam (first message)

**Expected:** `scamDetected: true`.

```json
{
  "sessionId": "postman-prize-001",
  "message": {
    "sender": "scammer",
    "text": "Congratulations! You have won 50,000 in our lottery. Claim your prize now by sending your bank details.",
    "timestamp": "2026-02-01T10:25:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

---

## 5. Safe / legitimate message (not scam)

**Expected:** `scamDetected: false`, agent reply like “Thanks for letting me know”.

```json
{
  "sessionId": "postman-safe-001",
  "message": {
    "sender": "user",
    "text": "Hi, just checking if my order #12345 has been shipped.",
    "timestamp": "2026-02-01T10:30:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "Chat",
    "language": "English",
    "locale": "IN"
  }
}
```

---

## 6. Multi-turn: follow-up message (with history)

**Expected:** `scamDetected: true`, reply fits “needs explanation” / follow-up.

```json
{
  "sessionId": "postman-multi-001",
  "message": {
    "sender": "scammer",
    "text": "Share your UPI ID to avoid account suspension.",
    "timestamp": "2026-02-01T10:17:10Z"
  },
  "conversationHistory": [
    {
      "sender": "scammer",
      "text": "Your bank account will be blocked today. Verify immediately.",
      "timestamp": "2026-02-01T10:15:30Z"
    },
    {
      "sender": "user",
      "text": "Why will my account be blocked?",
      "timestamp": "2026-02-01T10:16:10Z"
    }
  ],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

---

## 7. Scam with UPI / phone for intelligence extraction

**Expected:** `scamDetected: true`; if `totalMessagesExchanged >= 4`, response may include `extractedIntelligence` (e.g. UPI, phone).

```json
{
  "sessionId": "postman-intel-001",
  "message": {
    "sender": "scammer",
    "text": "Send payment to merchant@paytm or call +919876543210 to resolve. Your account will be deactivated in 24 hours.",
    "timestamp": "2026-02-01T10:35:00Z"
  },
  "conversationHistory": [
    {
      "sender": "scammer",
      "text": "Urgent: Your account has limited access.",
      "timestamp": "2026-02-01T10:33:00Z"
    },
    {
      "sender": "user",
      "text": "What do you mean?",
      "timestamp": "2026-02-01T10:34:00Z"
    },
    {
      "sender": "scammer",
      "text": "Verify your identity to restore access.",
      "timestamp": "2026-02-01T10:34:30Z"
    }
  ],
  "metadata": {
    "channel": "WhatsApp",
    "language": "English",
    "locale": "IN"
  }
}
```

---

## 8. Invalid API key (expect 401)

**Headers:** set `x-api-key` to `wrong_key` (or omit it).

**Body:** use any valid body, e.g. Test Case 1.

**Expected:** Status `401`, body like `{"status": "error", "message": "Invalid API key"}`.

---

## 9. Minimal body (only required fields)

**Expected:** `200` if message is handled; may be safe or scam depending on text.

```json
{
  "sessionId": "postman-minimal-001",
  "message": {
    "sender": "scammer",
    "text": "Hello, this is your bank.",
    "timestamp": "2026-02-01T12:00:00Z"
  },
  "conversationHistory": []
}
```

---

## 10. Refund / transfer scam

**Expected:** `scamDetected: true`.

```json
{
  "sessionId": "postman-refund-001",
  "message": {
    "sender": "scammer",
    "text": "We have processed your refund of Rs 5000. To receive it, confirm your account number and IFSC. Reply within 2 hours.",
    "timestamp": "2026-02-01T11:00:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

---

## Quick reference

| #  | Scenario           | scamDetected | Notes                    |
|----|--------------------|--------------|--------------------------|
| 1  | Bank block         | true         | First message            |
| 2  | UPI share          | true         | First message            |
| 3  | Phishing link      | true         | Link + urgency           |
| 4  | Prize/lottery      | true         | First message            |
| 5  | Safe message       | false        | Normal customer query    |
| 6  | Multi-turn         | true         | With conversationHistory |
| 7  | Intel extraction   | true         | UPI/phone in text        |
| 8  | Invalid API key   | -            | Expect 401               |
| 9  | Minimal body       | depends      | Only required fields     |
| 10 | Refund/transfer   | true         | First message            |
