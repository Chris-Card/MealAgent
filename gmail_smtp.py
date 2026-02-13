"""Gmail SMTP email sending."""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from config import Config


def send_email(
    config: type[Config],
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str,
    max_retries: int = 3
) -> None:
    """
    Send email via Gmail SMTP.
    
    Args:
        config: Configuration class
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text email body
        max_retries: Maximum number of retry attempts
        
    Raises:
        Exception: If email sending fails after retries
    """
    if not config.GMAIL_USERNAME or not config.GMAIL_APP_PASSWORD:
        raise ValueError("Gmail credentials not configured")
    
    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = config.GMAIL_USERNAME
    message["To"] = to_email
    
    # Attach both plain text and HTML versions
    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")
    
    message.attach(part1)
    if config.INCLUDE_HTML_EMAIL:
        message.attach(part2)
    
    # Try to send with retries
    last_error = None
    for attempt in range(max_retries):
        try:
            # Create secure connection
            context = ssl.create_default_context()
            
            with smtplib.SMTP(config.GMAIL_SMTP_HOST, config.GMAIL_SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(config.GMAIL_USERNAME, config.GMAIL_APP_PASSWORD)
                server.send_message(message)
            
            return  # Success
            
        except smtplib.SMTPAuthenticationError as e:
            raise ValueError(f"Gmail authentication failed. Check your username and app password: {e}")
        except smtplib.SMTPException as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"SMTP error (attempt {attempt + 1}/{max_retries}): {e}")
                import time
                time.sleep(2)  # Brief delay before retry
                continue
            else:
                raise RuntimeError(f"Failed to send email after {max_retries} attempts: {e}")
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"Error sending email (attempt {attempt + 1}/{max_retries}): {e}")
                import time
                time.sleep(2)
                continue
            else:
                raise
    
    if last_error:
        raise last_error
