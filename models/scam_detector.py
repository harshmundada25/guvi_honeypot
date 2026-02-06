import os
import re
import joblib
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer

# Paths
BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
MODEL_FILE = ARTIFACTS_DIR / "scam_model.joblib"
MODEL_VERSION = "v3"


def _ensure_artifacts_dir() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _contains(patterns: List[str], text: str) -> bool:
    return any(p in text for p in patterns)


def _heuristic_score(text: str) -> int:
    """Simple signal scoring kept for interpretability and guarding the ML output."""
    text_l = text.lower()
    score = 0
    if _contains(
        [
            "urgent",
            "immediately",
            "within",
            "blocked",
            "suspended",
            "deactivated",
            "limited",
            "unusual activity",
            "suspicious",
            "avoid",
        ],
        text_l,
    ):
        score += 2
    if _contains(
        ["bank", "account", "payment", "transfer", "refund", "upi", "credit", "debit"],
        text_l,
    ):
        score += 2
    if _contains(
        ["restore", "reactivate", "verify", "confirm", "submit", "update", "click", "login", "respond"],
        text_l,
    ):
        score += 1
    if _contains(["otp", "pin", "upi pin"], text_l):
        score += 2
    if _contains(["prize", "reward", "lottery", "cashback", "free", "offer", "won", "bonus"], text_l):
        score += 3
    if re.search(r"https?://", text_l):
        score += 3
    return score


def _custom_feature_row(text: str) -> List[float]:
    """Compute 11 lightweight custom features to complement TF-IDF."""
    text_l = text.lower()

    urgency_words = ["urgent", "immediately", "asap", "within", "hurry", "now", "today"]
    financial_words = ["bank", "account", "payment", "transfer", "refund", "upi", "credit", "debit"]
    action_words = ["restore", "reactivate", "verify", "confirm", "submit", "update", "click", "login", "respond"]
    reward_words = ["prize", "reward", "lottery", "cashback", "free", "offer", "won", "bonus"]
    threat_words = ["blocked", "suspended", "deactivated", "limited", "closing", "blacklist", "otp", "pin"]
    legitimacy_words = [
        "otp",
        "one time password",
        "debited",
        "credited",
        "txn",
        "transaction",
        "statement",
        "maintenance",
        "account ending",
        "available balance",
        "avl bal",
        "emi",
    ]

    def _binary(words: List[str]) -> int:
        return int(_contains(words, text_l))

    urgency = _binary(urgency_words)
    financial = _binary(financial_words)
    action = _binary(action_words)
    reward = _binary(reward_words)
    threat = _binary(threat_words)
    link_present = int(bool(re.search(r"https?://", text_l)))
    phone_present = int(bool(re.search(r"\+91\d{10}", text_l)))
    upi_or_email_present = int(bool(re.search(r"\b[a-z0-9._-]+@[a-z0-9.-]+\b", text_l)))

    word_count_norm = min(len(text.split()) / 50.0, 1.0)
    char_count_norm = min(len(text) / 280.0, 1.0)
    present = sum(1 for w in legitimacy_words if w in text_l)
    # Make legitimacy resilient: one legit term yields >=0.25
    legitimacy_score = round(min(1.0, present / 3.0), 3)

    return [
        urgency,
        financial,
        action,
        reward,
        threat,
        link_present,
        phone_present,
        upi_or_email_present,
        word_count_norm,
        char_count_norm,
        legitimacy_score,
    ]


def _training_data() -> Tuple[List[str], List[int]]:
    """Compact in-memory dataset (20 samples) to bootstrap the model."""
    scam_messages = [
        "Your bank account will be blocked immediately. Verify now at https://fake-bank.com",
        "Congratulations! You won a lottery. Claim your prize by sharing bank details",
        "Share your UPI ID to verify your account and receive refund",
        "Click this link to update KYC or your account will be suspended",
        "Confirm debit card number and CVV to avoid account suspension",
        "You have been selected for cash reward. Provide account number now",
        "We detected unusual activity. Reactivate account by sending payment to scam@upi",
        "Pay processing fee within 10 minutes to release your reward",
        "Final notice: account limited due to suspicious activity. Login immediately",
        "Claim bonus by transferring 500 INR to winner@oksbi",
    ]

    legitimate_messages = [
        "INR 2,500 debited from A/C XXXX1234 on 02-Feb. If not you, call bank immediately.",
        "Your OTP is 123456 for transaction at Amazon. Do not share with anyone.",
        "Scheduled maintenance: NetBanking will be unavailable on Feb 5 from 1AM-3AM.",
        "Payment of Rs 600 completed using UPI at ZOMATO. If not you, contact bank.",
        "Monthly account statement is ready. Login to internet banking to view.",
        "Credit of Rs 1,000 received from ACME PAYROLL. Available balance updated.",
        "Thanks for using NetBanking. Your transaction reference is TXN12345.",
        "Dear customer, your card ending 4455 has been shipped. Track in app.",
        "Reminder: EMI of Rs 1,200 will be auto-debited on 10 Feb.",
        "Security alert: login from new device detected. If not you, please reset password via app.",
    ]

    texts = scam_messages + legitimate_messages
    labels = [1] * len(scam_messages) + [0] * len(legitimate_messages)
    return texts, labels


class ScamDetector:
    """RandomForest + TF-IDF + handcrafted features with legitimacy guard rails."""

    def __init__(self) -> None:
        self.vectorizer: TfidfVectorizer | None = None
        self.model: RandomForestClassifier | None = None
        _ensure_artifacts_dir()
        self._load_or_train()

    def _load_or_train(self) -> None:
        if MODEL_FILE.exists():
            try:
                artifact = joblib.load(MODEL_FILE)
                if artifact.get("version") == MODEL_VERSION:
                    self.vectorizer = artifact["vectorizer"]
                    self.model = artifact["model"]
                    return
            except Exception:
                pass
        self._train_model()

    def _train_model(self) -> None:
        texts, labels = _training_data()
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            ngram_range=(1, 2),
            lowercase=True,
            stop_words="english",
        )
        tfidf_features = self.vectorizer.fit_transform(texts).toarray()
        custom_features = np.array([_custom_feature_row(t) for t in texts])
        training_matrix = np.hstack([tfidf_features, custom_features])

        self.model = RandomForestClassifier(
            n_estimators=120,
            max_depth=10,
            random_state=42,
        )
        self.model.fit(training_matrix, labels)

        joblib.dump({"vectorizer": self.vectorizer, "model": self.model, "version": MODEL_VERSION}, MODEL_FILE)

    def _vectorize(self, text: str) -> np.ndarray:
        if not self.vectorizer:
            raise RuntimeError("Vectorizer not initialized")
        tfidf_vec = self.vectorizer.transform([text]).toarray()
        custom_vec = np.array([_custom_feature_row(text)])
        return np.hstack([tfidf_vec, custom_vec])

    def analyze(self, message_text: str, history: Optional[List[Dict]] = None) -> Dict:
        """Return detailed analysis with ML probability, heuristics, and legitimacy guard."""
        history = history or []
        last_scammer_msgs = " ".join(
            m.get("text", "") for m in history[-3:] if m.get("sender") == "scammer"
        )
        combined_text = f"{message_text.strip()} {last_scammer_msgs}".strip()
        text_l = combined_text.lower()

        # Hard safety overrides for clearly legitimate bank notifications.
        safe_patterns = [
            "scheduled maintenance",
            "maintenance",
            "debited",
            "credited",
            "available balance",
            "avl bal",
        ]
        if any(p in text_l for p in safe_patterns):
            legitimacy_score = 1.0 if "maintenance" in text_l else 0.667
            return {
                "is_scam": False,
                "confidence": 0.05,
                "ml_probability": 0.0,
                "heuristic_score": 0,
                "legitimacy_score": legitimacy_score,
                "combined_text_used": combined_text,
            }

        heuristic = _heuristic_score(combined_text)
        legitimacy_score = _custom_feature_row(combined_text)[-1]

        if not self.model or not self.vectorizer:
            self._load_or_train()
        features = self._vectorize(combined_text)
        ml_proba = float(self.model.predict_proba(features)[0][1])

        # Whitelist-style legitimate patterns to avoid false positives on bank alerts/maintenance.
        legit_patterns = [
            r"inr\s+[\d,.]+\s+(debited|credited)\s+from\s+a/c",
            r"credit of rs",
            r"credited to your account",
            r"your otp is \d{4,6}",
            r"scheduled maintenance",
            r"available balance",
            r"monthly account statement",
            r"emi .* auto-debited",
        ]
        legit_override = any(re.search(p, combined_text.lower()) for p in legit_patterns)

        scam_confidence = max(ml_proba, heuristic / 6.0)
        scam_confidence = scam_confidence * (1 - (legitimacy_score * 0.4))
        scam_confidence = round(min(max(scam_confidence, 0.0), 0.99), 3)

        safe_override = (legitimacy_score >= 0.3 and heuristic <= 1) or legit_override

        is_scam = (
            not safe_override
            and (ml_proba >= 0.55 or (ml_proba >= 0.45 and heuristic >= 3))
            and legitimacy_score < 0.7
        )

        if safe_override:
            scam_confidence = round(min(scam_confidence, 0.15), 3)
            is_scam = False

        # Extra guard: low-signal messages (no heuristics) need higher ML probability to be scams.
        if heuristic <= 1 and ml_proba < 0.65:
            is_scam = False
            scam_confidence = round(min(scam_confidence, 0.2), 3)

        return {
            "is_scam": bool(is_scam),
            "confidence": scam_confidence,
            "ml_probability": round(ml_proba, 3),
            "heuristic_score": heuristic,
            "legitimacy_score": legitimacy_score,
            "combined_text_used": combined_text,
        }
