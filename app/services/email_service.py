import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.settings import settings

logger = logging.getLogger(__name__)

def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Sends a 6-digit Security OTP email to the user's official email address.
    Uses SMTP (e.g., Gmail smtp.gmail.com:587) if SMTP_USER and SMTP_PASSWORD are configured.
    """
    subject = f"[{settings.PROJECT_NAME}] Your Password Reset OTP Code: {otp_code}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; margin: 0;">
        <div style="max-width: 520px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 30px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            <div style="text-align: center; margin-bottom: 24px;">
                <h2 style="color: #38bdf8; margin: 0; font-size: 22px;">🛡️ SecureShare Password Reset</h2>
                <p style="color: #94a3b8; font-size: 14px; margin-top: 6px;">End-to-End Encrypted Vault Verification</p>
            </div>
            
            <p style="font-size: 15px; line-height: 1.5; color: #e2e8f0;">Hello,</p>
            <p style="font-size: 15px; line-height: 1.5; color: #cbd5e1;">You recently requested a password reset for your <strong>SecureShare</strong> account associated with <span style="color: #38bdf8;">{to_email}</span>.</p>
            
            <p style="font-size: 15px; color: #cbd5e1;">Please use the 6-digit One-Time Security OTP Code below to proceed:</p>
            
            <div style="background: #090d16; border: 2px dashed #0284c7; border-radius: 10px; padding: 20px; text-align: center; margin: 25px 0;">
                <span style="font-size: 34px; font-weight: bold; letter-spacing: 8px; color: #4ade80; font-family: monospace;">{otp_code}</span>
            </div>
            
            <p style="color: #94a3b8; font-size: 13px; text-align: center;">⏱️ This security code is valid for <strong>10 minutes</strong> only.</p>
            
            <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 12px; border-radius: 4px; margin-top: 20px;">
                <p style="color: #fca5a5; font-size: 12px; margin: 0;">⚠️ <strong>Security Notice:</strong> If you did not request this password reset, please ignore this email. Never share your OTP code with anyone.</p>
            </div>

            <hr style="border: 0; border-top: 1px solid #334155; margin: 25px 0 15px 0;" />
            <p style="color: #64748b; font-size: 12px; text-align: center; margin: 0;">© SecureShare File-Sharing System. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    print("\n=========================================================================")
    print(f"📩 [SMTP EMAIL DISPATCH] Attempting to send OTP to recipient: {to_email}")
    print(f"🔑 Security OTP Code: {otp_code}")
    print("=========================================================================\n")

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            sender_email = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
            sender_name = settings.EMAILS_FROM_NAME or "SecureShare Vault"

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = to_email

            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=12) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender_email, [to_email], msg.as_string())

            logger.info(f"Successfully sent OTP email to {to_email} via SMTP ({settings.SMTP_SERVER})")
            print(f"✅ [SMTP SUCCESS] OTP email successfully delivered to inbox: {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMTP email to {to_email}: {e}")
            print(f"❌ [SMTP ERROR] Could not deliver email via SMTP: {e}")
            return False
    else:
        print(f"ℹ️ [SMTP INFO] SMTP_USER is not configured in .env. To send real emails to Gmail, add SMTP_USER and SMTP_PASSWORD to your .env file.")
        return False

def send_file_share_email(
    to_email: str,
    sender_name: str,
    sender_email: str,
    filename: str,
    share_url: str,
    permission: str,
    expiry_at = None,
    has_password: bool = False
) -> bool:
    """
    Sends an official HTML email notification to the file share recipient when a file is shared with them.
    Uses SMTP (e.g. Gmail smtp.gmail.com:587) if SMTP_USER and SMTP_PASSWORD are configured.
    """
    subject = f"[{settings.PROJECT_NAME}] {sender_name} shared a file with you: {filename}"

    expiry_desc = expiry_at.strftime("%Y-%m-%d %H:%M UTC") if expiry_at else "Never"
    pwd_notice = '<p style="color: #f59e0b; font-size: 13px; margin: 4px 0;">🔒 <strong>Password Protected:</strong> Password required to open</p>' if has_password else ''

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; margin: 0;">
        <div style="max-width: 540px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 30px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            <div style="text-align: center; margin-bottom: 24px;">
                <h2 style="color: #38bdf8; margin: 0; font-size: 22px;">📁 SecureShare File Access</h2>
                <p style="color: #94a3b8; font-size: 14px; margin-top: 6px;">End-to-End Encrypted File Sharing</p>
            </div>

            <p style="font-size: 15px; color: #cbd5e1;">Hello,</p>
            <p style="font-size: 15px; color: #cbd5e1;"><strong>{sender_name}</strong> (<span style="color: #38bdf8;">{sender_email}</span>) has shared a secure file with you on <strong>SecureShare</strong>.</p>

            <div style="background: #090d16; border: 1px solid #0284c7; border-radius: 10px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #ffffff; margin: 0 0 10px 0; font-size: 18px;">📄 {filename}</h3>
                <p style="font-size: 13px; color: #94a3b8; margin: 4px 0;"><strong>Permission:</strong> <span style="color: #38bdf8;">{permission}</span></p>
                <p style="font-size: 13px; color: #94a3b8; margin: 4px 0;"><strong>Expiration:</strong> {expiry_desc}</p>
                {pwd_notice}
            </div>

            <div style="text-align: center; margin: 25px 0;">
                <a href="{share_url}" style="background: #0284c7; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);">📥 Access & Download File</a>
            </div>

            <p style="color: #94a3b8; font-size: 12px; text-align: center; word-break: break-all; margin-top: 20px;">Direct Link: <a href="{share_url}" style="color: #38bdf8;">{share_url}</a></p>

            <hr style="border: 0; border-top: 1px solid #334155; margin: 25px 0 15px 0;" />
            <p style="color: #64748b; font-size: 12px; text-align: center; margin: 0;">© SecureShare File-Sharing System. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    print("\n=========================================================================")
    print(f"📩 [FILE SHARE EMAIL DISPATCH] Sending notification to recipient: {to_email}")
    print(f"📄 File: '{filename}' | Shared by: {sender_name} ({sender_email})")
    print(f"🔗 Access Link: {share_url}")
    print("=========================================================================\n")

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            sender = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
            from_header = f"{sender_name} via SecureShare <{sender}>"

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_header
            msg["To"] = to_email

            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=12) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender, [to_email], msg.as_string())

            logger.info(f"Successfully sent file share email notification to {to_email} via SMTP ({settings.SMTP_SERVER})")
            print(f"✅ [SMTP SUCCESS] File share email successfully delivered to recipient inbox: {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send file share email via SMTP to {to_email}: {e}")
            print(f"❌ [SMTP ERROR] Could not deliver file share email via SMTP: {e}")
            return False
    else:
        print(f"ℹ️ [SMTP INFO] SMTP_USER is not configured in .env. Configure SMTP_USER and SMTP_PASSWORD to deliver real emails to {to_email}.")
        return False

