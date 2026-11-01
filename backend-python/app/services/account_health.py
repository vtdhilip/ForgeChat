from typing import Optional
from app.core.database import db

async def mark_account_health(account_id: int, status: str, message: Optional[str] = None):
    if not account_id:
        return
    try:
        if status == "healthy":
            await db.execute(
                """
                UPDATE coexistence.whatsapp_accounts
                SET health_status = 'healthy',
                    last_success_at = NOW(),
                    last_error_message = NULL
                WHERE id = $1
                """,
                account_id
            )
        else:
            msg = (message or "")[:500]
            await db.execute(
                """
                UPDATE coexistence.whatsapp_accounts
                SET health_status = $1,
                    last_error_at = NOW(),
                    last_error_message = $2
                WHERE id = $3
                """,
                status, msg, account_id
            )
    except Exception as e:
        print(f"[accountHealth] update failed: {e}")

def classify_meta_error(err: Exception) -> str:
    msg = str(err).lower()
    if "401" in msg or "190" in msg or "token" in msg or "session has expired" in msg:
        return "invalid_token"
    if "429" in msg or "rate" in msg or "limit" in msg:
        return "rate_limited"
    return "unknown_error"
