import re
from typing import Dict, List


def _collect_text(history: List[Dict], current_message: str) -> str:
    full_text = current_message or ""
    for msg in history:
        if msg.get("sender") == "scammer":
            full_text += f" {msg.get('text', '')}"
    return full_text


def extract_intelligence(history: List[Dict], current_message: str) -> Dict:
    """Extract UPI IDs, phone numbers, links, bank accounts, and suspicious keywords."""
    history = history or []
    full_text = _collect_text(history, current_message)
    text_l = full_text.lower()

    # Accounts: prefer 12-18 digit spans or 4-4-4/4-4-5 grouped forms; avoid 10-digit phones.
    bank_accounts = re.findall(r"\b\d{4}-\d{4}-\d{4,5}\b|\b\d{12,18}\b", full_text)
    upi_ids = re.findall(r"\b[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\b", full_text)
    phishing_links = re.findall(r"https?://[^\s]+", full_text)
    # Phones: allow +91 with optional separators and bare 10-digit Indian numbers.
    phone_numbers = re.findall(r"\+?91[- ]?\d{10}|\b[6-9]\d{9}\b", full_text)

    suspicious_keywords_list = [
        "urgent",
        "immediately",
        "blocked",
        "suspended",
        "deactivated",
        "limited",
        "unusual activity",
        "verify",
        "confirm",
        "update",
        "click",
        "login",
        "respond",
        "upi",
        "payment",
        "transfer",
        "refund",
        "reward",
        "prize",
        "lottery",
    ]
    suspicious_keywords = [kw for kw in suspicious_keywords_list if kw in text_l]

    return {
        "bankAccounts": sorted(set(bank_accounts)),
        "upiIds": sorted(set(upi_ids)),
        "phishingLinks": sorted(set(phishing_links)),
        "phoneNumbers": sorted(set(phone_numbers)),
        "suspiciousKeywords": sorted(set(suspicious_keywords)),
    }
