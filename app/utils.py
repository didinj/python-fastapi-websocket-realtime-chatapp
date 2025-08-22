import os
from itsdangerous import URLSafeSerializer


SECRET = os.getenv("CHAT_SECRET", "change-me")
signer = URLSafeSerializer(SECRET, salt="chat")


def issue_token(username: str) -> str:
    return signer.dumps({"u": username})


def verify_token(token: str) -> str | None:
    try:
        data = signer.loads(token)
        return data.get("u")
    except Exception:
        return None