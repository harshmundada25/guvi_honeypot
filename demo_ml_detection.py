"""Offline demo for the ML-based scam detector."""
from models.scam_detector import ScamDetector

SAMPLES = [
    ("Transaction notification - SAFE", "INR 2,500 debited from A/C XXXX1234 on 02-Feb."),
    ("OTP message - SAFE", "Your OTP is 123456 for transaction at Amazon."),
    ("Maintenance notice - SAFE", "Scheduled maintenance on Feb 5 from 1AM-3AM."),
    ("Credit notification - SAFE", "Credit of Rs 1,000 received from payroll."),
    ("Account blocking threat - SCAM", "Your account will be blocked immediately. Verify now at https://fake-bank.com"),
    ("UPI sharing request - SCAM", "Share your UPI ID to verify your account and receive refund"),
    ("Prize/lottery scam - SCAM", "Congratulations! You won a lottery. Claim prize by sharing bank details"),
    ("Phishing link - SCAM", "Click this link to update KYC or your account will be suspended"),
]


def main():
    detector = ScamDetector()
    passed = 0
    for title, text in SAMPLES:
        result = detector.analyze(text)
        verdict = "SCAM" if result["is_scam"] else "SAFE"
        expected = "SCAM" if "SCAM" in title else "SAFE"
        ok = verdict == expected
        passed += 1 if ok else 0
        print(f"{title}: {verdict} (p={result['ml_probability']}, conf={result['confidence']}, legit={result['legitimacy_score']})")
    print(f"\nRESULTS: {passed}/{len(SAMPLES)} tests passed")


if __name__ == "__main__":
    main()
