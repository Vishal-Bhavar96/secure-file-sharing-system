import html
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from app.config.settings import settings

logger = logging.getLogger(__name__)

def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Sends a 6-digit Security OTP email to the user's official email address.
    Uses SMTP (e.g., Gmail smtp.gmail.com:587) if SMTP_USER and SMTP_PASSWORD are configured.
    """
    safe_email = html.escape(to_email or "")
    safe_otp = html.escape(str(otp_code or ""))
    subject = f"[{settings.PROJECT_NAME}] Your Password Reset OTP Code"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; color: #0F172A; padding: 24px; margin: 0;">
        <div style="max-width: 520px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; padding: 36px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
            <div style="text-align: center; margin-bottom: 28px;">
                <h1 style="color: #1E3A5F; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;">SECURESHARE</h1>
                <p style="color: #64748B; font-size: 13px; margin-top: 4px; font-weight: 500;">Security Verification Code</p>
            </div>
            
            <p style="font-size: 15px; line-height: 1.6; color: #0F172A; margin-bottom: 12px;">Hello,</p>
            <p style="font-size: 14px; line-height: 1.6; color: #475569; margin-bottom: 20px;">You requested a password reset for your account associated with <strong>{safe_email}</strong>.</p>
            
            <div style="background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 8px; padding: 20px; text-align: center; margin: 24px 0;">
                <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1E3A5F; font-family: monospace;">{safe_otp}</span>
            </div>
            
            <p style="color: #64748B; font-size: 13px; text-align: center; margin-bottom: 20px;">⏱️ This security code is valid for <strong>10 minutes</strong>.</p>
            
            <div style="background: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 4px; margin-top: 24px;">
                <p style="color: #991B1B; font-size: 12px; margin: 0; line-height: 1.5;">🔒 <strong>Security Notice:</strong> If you did not request this code, please ignore this email. Never share your security code with anyone.</p>
            </div>

            <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 28px 0 16px 0;" />
            <p style="color: #94A3B8; font-size: 12px; text-align: center; margin: 0;">© SecureShare File-Sharing System. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    try:
        logger.info(f"OTP email dispatch attempted for recipient: {to_email}")

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                sender_email = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
                sender_name = settings.EMAILS_FROM_NAME or "SecureShare"

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = formataddr((sender_name, sender_email))
                msg["To"] = to_email

                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=12) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(sender_email, [to_email], msg.as_string())

                logger.info(f"Successfully sent OTP email to {to_email}")
                return True
            except smtplib.SMTPAuthenticationError as auth_err:
                logger.error(f"SMTP authentication failed for {to_email}: {auth_err}")
                return False
            except smtplib.SMTPException as smtp_err:
                logger.error(f"SMTP protocol error for {to_email}: {smtp_err}")
                return False
            except TimeoutError as timeout_err:
                logger.error(f"SMTP connection timeout for {to_email}: {timeout_err}")
                return False
            except Exception as e:
                logger.error(f"Failed to send OTP email to {to_email}: {e}")
                return False
        else:
            logger.info("SMTP credentials not configured. Skipping real inbox delivery.")
            return False
    except Exception as exc:
        logger.error(f"Unexpected error in send_otp_email: {exc}")
        return False


def send_file_share_email(
    to_email: str,
    sender_name: str,
    sender_email: str,
    filename: str,
    share_url: str,
    permission: str,
    expiry_at=None,
    has_password: bool = False,
    requires_otp: bool = True
) -> bool:
    """
    Sends a production-ready, enterprise-styled HTML email notification to the file share recipient.
    Features light design (#F8FAFC, #FFFFFF, #1E3A5F, #2563EB) and full user-input HTML escaping.
    Does NOT contain share password, raw token in logs, server paths, or encryption keys.
    """
    try:
        safe_to_email = html.escape(to_email or "")
        safe_sender_name = html.escape(sender_name or "A SecureShare User")
        safe_sender_email = html.escape(sender_email or "")
        safe_filename = html.escape(filename or "Shared File")
        safe_permission = html.escape(str(permission or "DOWNLOAD").upper())
        safe_share_url = html.escape(share_url or "")

        expiry_desc = expiry_at.strftime("%d %b %Y, %I:%M %p") if expiry_at else "Never"
        safe_expiry = html.escape(expiry_desc)

        subject = f"[{settings.PROJECT_NAME}] {safe_sender_name} shared a file with you: {safe_filename}"

        sec_indicators = []
        if requires_otp:
            sec_indicators.append("OTP verification required")
        if has_password:
            sec_indicators.append("Password protected")
        
        security_text = "<br/>".join(sec_indicators) if sec_indicators else "Standard Link Protection"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; color: #0F172A; padding: 24px; margin: 0;">
            <div style="max-width: 560px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; padding: 36px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                
                <!-- Brand Header -->
                <div style="margin-bottom: 28px;">
                    <span style="color: #1E3A5F; font-size: 20px; font-weight: 800; letter-spacing: -0.5px;">SECURESHARE</span>
                    <p style="color: #64748B; font-size: 13px; margin: 4px 0 0 0; font-weight: 500;">Secure File Sharing Notification</p>
                </div>

                <!-- Greeting -->
                <p style="font-size: 15px; color: #0F172A; margin: 0 0 12px 0;">Hello,</p>
                <p style="font-size: 15px; color: #475569; margin: 0 0 24px 0; line-height: 1.5;">
                    <strong>{safe_sender_name}</strong> has securely shared a file with you.
                </p>

                <!-- File Summary Card -->
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 20px; margin-bottom: 28px;">
                    <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin-bottom: 12px; word-break: break-all;">
                        📄 File: {safe_filename}
                    </div>
                    <div style="font-size: 13px; color: #475569; margin-bottom: 6px;">
                        <strong>Permission:</strong> <span style="color: #2563EB; font-weight: 600;">{safe_permission}</span>
                    </div>
                    <div style="font-size: 13px; color: #475569; margin-bottom: 6px;">
                        <strong>Expires:</strong> {safe_expiry}
                    </div>
                    <div style="font-size: 13px; color: #475569;">
                        <strong>Security:</strong><br/>
                        <span style="color: #15803D; font-weight: 500;">{security_text}</span>
                    </div>
                </div>

                <!-- Access Action Button -->
                <div style="text-align: center; margin-bottom: 28px;">
                    <a href="{safe_share_url}" style="background-color: #2563EB; color: #FFFFFF; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; display: inline-block; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);">ACCESS SHARED FILE</a>
                </div>

                <!-- Security Notice -->
                <div style="background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 16px; border-radius: 4px; margin-bottom: 24px;">
                    <p style="color: #1E40AF; font-size: 12px; margin: 0; line-height: 1.5;">
                        🛡️ <strong>Security Notice:</strong> Never share your verification code or share password.
                    </p>
                </div>

                <!-- Direct Link Backup -->
                <p style="color: #94A3B8; font-size: 12px; word-break: break-all; margin: 0 0 20px 0;">
                    If the button does not work, copy and paste this secure link into your browser:<br/>
                    <a href="{safe_share_url}" style="color: #2563EB;">{safe_share_url}</a>
                </p>

                <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 24px 0 16px 0;" />
                <p style="color: #94A3B8; font-size: 12px; text-align: center; margin: 0;">
                    © SecureShare File-Sharing System. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """

        logger.info(f"File share notification email dispatch attempted for recipient: {to_email}")

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                sender = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
                from_header = formataddr((f"{sender_name} via SecureShare", sender))

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

                logger.info(f"Successfully sent file share email notification to {to_email}")
                return True
            except Exception as e:
                logger.error(f"Failed to send file share email to {to_email}: {e}")
                return False
        else:
            logger.info("SMTP credentials not configured. Skipping real inbox delivery.")
            return False
    except Exception as exc:
        logger.error(f"Unexpected error in send_file_share_email: {exc}")
        return False


def send_share_otp_email(to_email: str, otp_code: str, filename: str = "Shared File") -> bool:
    """
    Sends a 6-digit access verification OTP code to the recipient email address for shared file verification.
    """
    safe_to_email = html.escape(to_email or "")
    safe_otp = html.escape(str(otp_code or ""))
    safe_filename = html.escape(filename or "Shared File")
    subject = f"[{settings.PROJECT_NAME}] Your File Verification Code: {safe_otp}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; color: #0F172A; padding: 24px; margin: 0;">
        <div style="max-width: 520px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; padding: 36px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
            <div style="text-align: center; margin-bottom: 28px;">
                <h1 style="color: #1E3A5F; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;">SECURESHARE</h1>
                <p style="color: #64748B; font-size: 13px; margin-top: 4px; font-weight: 500;">File Access Verification Code</p>
            </div>
            
            <p style="font-size: 15px; line-height: 1.6; color: #0F172A; margin-bottom: 12px;">Hello,</p>
            <p style="font-size: 14px; line-height: 1.6; color: #475569; margin-bottom: 20px;">Use the verification code below to access the shared file <strong>{safe_filename}</strong>:</p>
            
            <div style="background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 8px; padding: 20px; text-align: center; margin: 24px 0;">
                <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1E3A5F; font-family: monospace;">{safe_otp}</span>
            </div>
            
            <p style="color: #64748B; font-size: 13px; text-align: center; margin-bottom: 20px;">⏱️ This security code is valid for <strong>10 minutes</strong>.</p>
            
            <div style="background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 16px; border-radius: 4px; margin-top: 24px;">
                <p style="color: #1E40AF; font-size: 12px; margin: 0; line-height: 1.5;">🛡️ <strong>Security Notice:</strong> Never share your verification code or share password with anyone.</p>
            </div>

            <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 28px 0 16px 0;" />
            <p style="color: #94A3B8; font-size: 12px; text-align: center; margin: 0;">© SecureShare File-Sharing System. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    try:
        logger.info(f"Share OTP email dispatch attempted for recipient: {to_email}")

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                sender_email = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
                sender_name = settings.EMAILS_FROM_NAME or "SecureShare"

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = formataddr((sender_name, sender_email))
                msg["To"] = to_email

                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=12) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(sender_email, [to_email], msg.as_string())

                logger.info(f"Successfully sent share OTP email to {to_email}")
                return True
            except Exception as e:
                logger.error(f"Failed to send share OTP email to {to_email}: {e}")
                return False
        else:
            logger.info("SMTP credentials not configured. Skipping real inbox delivery.")
            return False
    except Exception as exc:
        logger.error(f"Unexpected error in send_share_otp_email: {exc}")
        return False

