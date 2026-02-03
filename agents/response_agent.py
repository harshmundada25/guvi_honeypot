import os
import random
import re
from typing import Optional

try:
    from groq import Groq
except Exception:
    Groq = None


class ResponseAgent:
    """Generates human-like engagement responses using Groq with graceful fallback."""

    GROQ_MODEL = "llama-3.1-8b-instant"

    def __init__(self) -> None:
        api_key = (os.getenv("GROQ_API_KEY") or "").strip()
        self.client: Optional[Groq] = None
        if api_key and Groq:
            try:
                self.client = Groq(api_key=api_key)
            except Exception:
                self.client = None

        self.intents = {
            0: "confused and worried",
            1: "needs explanation",
            2: "suspicious but polite",
            3: "seeking confirmation",
            4: "asking for guidance",
            5: "requesting more details",
            6: "expressing concern",
            7: "asking for verification",
        }

        self.templates = {
            "confused and worried": [
                "I'm confused and worried—what does this mean?",
                "This is worrying. Can you explain what's happening?",
                "I'm a bit concerned. What exactly do you need from me?",
            ],
            "needs explanation": [
                "Can you explain this more clearly?",
                "I didn't get that. Please explain in simple terms.",
                "What exactly do you want me to do?",
            ],
            "suspicious but polite": [
                "This sounds a bit suspicious; can you clarify why?",
                "I'm trying to understand—why is this required?",
                "Okay, but I need more detail before I proceed.",
            ],
            "seeking confirmation": [
                "Is this really from the bank?",
                "How can I know this is legitimate?",
                "Is my account actually affected?",
            ],
            "asking for guidance": [
                "What should I do next?",
                "Please guide me step by step.",
                "I'm not sure what to do—can you guide me?",
            ],
            "requesting more details": [
                "Can you share the exact steps you want me to follow?",
                "What details do you need from me?",
                "Which information do you expect me to provide?",
            ],
            "expressing concern": [
                "I'm concerned—why is this so urgent?",
                "This feels risky. Can you reassure me?",
                "I'm worried about sharing anything without proof.",
            ],
            "asking for verification": [
                "How do I verify you are from the bank?",
                "Do you have an official contact I can call?",
                "Can you prove this request is genuine?",
            ],
        }

    def _clean(self, reply: str) -> str:
        reply = (reply or "").split("\n")[0].strip()
        reply = re.sub(r'[\"*]', "", reply)
        words = reply.split()
        if len(words) > 18:
            reply = " ".join(words[:18])
        return reply

    def _groq_reply(self, intent: str) -> str:
        if not self.client:
            return ""
        try:
            resp = self.client.chat.completions.create(
                model=self.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a cautious bank customer. Reply with one short sentence (<=18 words), "
                            "natural and human-like. Stay polite and curious."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Respond with the emotional intent: {intent}",
                    },
                ],
                temperature=0.6,
                max_tokens=60,
                timeout=10,
            )
            return self._clean(resp.choices[0].message.content or "")
        except Exception:
            return ""

    def _template_reply(self, intent: str, last_scammer_text: str) -> str:
        options = self.templates.get(intent, self.templates["asking for guidance"])
        text_l = (last_scammer_text or "").lower()
        if "verify" in text_l or "confirm" in text_l:
            options = [o for o in options if "verify" in o.lower() or "confirm" in o.lower()] or options
        if "upi" in text_l or "pay" in text_l:
            options = [o for o in options if "step" in o.lower() or "guide" in o.lower()] or options
        return random.choice(options)

    def intent_for_depth(self, depth: int) -> str:
        return self.intents.get(min(depth, max(self.intents)), "asking for guidance")

    def generate_reply(self, is_scam: bool, conversation_depth: int, last_scammer_text: str = "") -> str:
        if not is_scam:
            return "Thanks for the update."

        intent = self.intent_for_depth(conversation_depth)

        reply = self._groq_reply(intent)
        if reply and len(reply) >= 3:
            return reply
        return self._template_reply(intent, last_scammer_text)

