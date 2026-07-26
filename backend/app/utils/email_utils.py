import requests
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def send_verification_email(to_email: str, full_name: str, token: str) -> bool:
    """Send verification email using Resend API."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email verification")
        return False

    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1E3A5F; padding: 30px; text-align: center; border-radius: 12px 12px 0 0;">
        <h1 style="color: white; margin: 0;">💰 Smart Expense Tracker</h1>
      </div>
      <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 12px 12px;">
        <h2 style="color: #1E3A5F;">Verify Your Email</h2>
        <p style="color: #555;">Hi <strong>{full_name}</strong>,</p>
        <p style="color: #555;">
          Thank you for registering! Please click the button below to verify
          your email address and activate your account.
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="{verify_url}"
             style="background: #1E3A5F; color: white; padding: 14px 32px;
                    border-radius: 8px; text-decoration: none; font-weight: bold;
                    font-size: 16px;">
            Verify Email Address
          </a>
        </div>
        <p style="color: #999; font-size: 13px;">
          This link expires in <strong>24 hours</strong>.<br>
          If you did not create an account, you can ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #bbb; font-size: 12px; text-align: center;">
          Smart Expense Tracker · AI-Powered Personal Finance
        </p>
      </div>
    </div>
    """

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from":    settings.FROM_EMAIL,
                "to":      [to_email],
                "subject": "Verify your Smart Expense Tracker account",
                "html":    html,
            },
            timeout=10,
        )
        if resp.ok:
            logger.info(f"Verification email sent to {to_email}")
            return True
        else:
            logger.error(f"Resend error: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False