import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp-relay.brevo.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "noreply@statiq.com")
SMTP_FROM_NAME = "StatIQ Admin"

def send_otp_email(to_email: str, otp: str):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning(f"SMTP credentials missing! Mocking OTP for {to_email}. OTP is: {otp}")
        return

    subject = "StatIQ - Registration OTP Verification"
    html_content = f"""
    <html>
    <body style="font-family: sans-serif; padding: 20px;">
        <h2>StatIQ Registration Approved</h2>
        <p>Your registration request has been approved by the administrator.</p>
        <p>Please use the following One-Time Password (OTP) to complete your registration:</p>
        <h3 style="background-color: #f0f4f8; padding: 10px; display: inline-block; letter-spacing: 2px;">{otp}</h3>
        <p>This OTP will expire in 15 minutes.</p>
        <p>Best regards,<br>The StatIQ Team</p>
    </body>
    </html>
    """

    _send_email(to_email, subject, html_content)

def send_rejection_email(to_email: str):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning(f"SMTP credentials missing! Mocking Rejection for {to_email}.")
        return

    subject = "StatIQ - Registration Status Update"
    html_content = """
    <html>
    <body style="font-family: sans-serif; padding: 20px;">
        <h2>StatIQ Registration Update</h2>
        <p>We regret to inform you that your registration request for StatIQ has been declined by the administrator.</p>
        <p>If you believe this is a mistake, please contact support.</p>
        <p>Best regards,<br>The StatIQ Team</p>
    </body>
    </html>
    """

    _send_email(to_email, subject, html_content)

def _send_email(to_email: str, subject: str, html_content: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
        server.quit()
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
