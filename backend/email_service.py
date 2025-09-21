import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Use Gmail SMTP for simplicity - can be changed to other providers
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.environ.get('SENDER_EMAIL', 'portfolio@seunolawepo.com')
        self.sender_password = os.environ.get('SENDER_PASSWORD', '')
        self.recipient_email = "seunolawepo2010@gmail.com"
    
    def create_contact_notification_email(self, contact_data: dict) -> MIMEMultipart:
        """Create email notification for new contact form submission"""
        
        message = MIMEMultipart("alternative")
        message["Subject"] = f"🔔 New Portfolio Contact: {contact_data.get('subject', 'No Subject')}"
        message["From"] = self.sender_email
        message["To"] = self.recipient_email
        
        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1f2937; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
                .footer {{ background: #374151; color: white; padding: 15px; border-radius: 0 0 8px 8px; text-align: center; }}
                .field {{ margin-bottom: 15px; }}
                .label {{ font-weight: bold; color: #374151; }}
                .value {{ background: white; padding: 10px; border-radius: 4px; margin-top: 5px; }}
                .priority {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 10px; border-radius: 4px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🎯 New Portfolio Contact Submission</h2>
                <p>Someone is interested in your Agile & Cloud leadership services!</p>
            </div>
            
            <div class="content">
                <div class="priority">
                    <strong>⚡ Action Required:</strong> New contact form submission received at {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                </div>
                
                <div class="field">
                    <div class="label">👤 Name:</div>
                    <div class="value">{contact_data.get('name', 'N/A')}</div>
                </div>
                
                <div class="field">
                    <div class="label">📧 Email:</div>
                    <div class="value">{contact_data.get('email', 'N/A')}</div>
                </div>
                
                <div class="field">
                    <div class="label">📋 Subject:</div>
                    <div class="value">{contact_data.get('subject', 'N/A')}</div>
                </div>
                
                <div class="field">
                    <div class="label">🕐 Availability Preference:</div>
                    <div class="value">{contact_data.get('availability_preference', 'No preference specified')}</div>
                </div>
                
                <div class="field">
                    <div class="label">💬 Message:</div>
                    <div class="value" style="white-space: pre-wrap;">{contact_data.get('message', 'N/A')}</div>
                </div>
                
                <div class="field">
                    <div class="label">📍 IP Address:</div>
                    <div class="value">{contact_data.get('ip_address', 'N/A')}</div>
                </div>
                
                <div class="field">
                    <div class="label">⏰ Submitted At:</div>
                    <div class="value">{contact_data.get('submitted_at', 'N/A')}</div>
                </div>
            </div>
            
            <div class="footer">
                <p>📱 <strong>Next Steps:</strong></p>
                <p>1. Reply directly to this person at: <strong>{contact_data.get('email', 'N/A')}</strong></p>
                <p>2. Check your admin dashboard for more details</p>
                <p>3. Schedule meeting during their preferred time: <strong>{contact_data.get('availability_preference', 'Flexible')}</strong></p>
            </div>
        </body>
        </html>
        """
        
        # Create plain text version
        text_content = f"""
        NEW PORTFOLIO CONTACT SUBMISSION
        ================================
        
        Name: {contact_data.get('name', 'N/A')}
        Email: {contact_data.get('email', 'N/A')}
        Subject: {contact_data.get('subject', 'N/A')}
        Availability: {contact_data.get('availability_preference', 'No preference')}
        
        Message:
        {contact_data.get('message', 'N/A')}
        
        Submitted: {contact_data.get('submitted_at', 'N/A')}
        IP Address: {contact_data.get('ip_address', 'N/A')}
        
        Reply directly to: {contact_data.get('email', 'N/A')}
        """
        
        # Attach both versions
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(html_content, "html")
        
        message.attach(text_part)
        message.attach(html_part)
        
        return message
    
    async def send_contact_notification(self, contact_data: dict) -> bool:
        """Send email notification for new contact form submission"""
        try:
            # For development/testing, we'll just log the email instead of sending
            # In production, you would configure actual SMTP credentials
            
            logger.info(f"📧 EMAIL NOTIFICATION (Development Mode)")
            logger.info(f"To: {self.recipient_email}")
            logger.info(f"Subject: New Portfolio Contact: {contact_data.get('subject', 'No Subject')}")
            logger.info(f"From: {contact_data.get('name')} <{contact_data.get('email')}>")
            logger.info(f"Message Preview: {contact_data.get('message', '')[:100]}...")
            logger.info(f"Availability: {contact_data.get('availability_preference', 'No preference')}")
            
            # In production, uncomment this section and configure SMTP:
            """
            message = self.create_contact_notification_email(contact_data)
            
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipient_email, message.as_string())
            """
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    def get_email_setup_instructions(self) -> dict:
        """Get instructions for setting up email in production"""
        return {
            "status": "development_mode",
            "message": "Email notifications are logged to console in development mode",
            "production_setup": {
                "step_1": "Set SENDER_EMAIL environment variable",
                "step_2": "Set SENDER_PASSWORD environment variable (use app password for Gmail)",
                "step_3": "Uncomment SMTP code in send_contact_notification method",
                "gmail_app_password": "https://support.google.com/accounts/answer/185833",
                "alternative_services": ["SendGrid", "Mailgun", "Resend", "AWS SES"]
            }
        }