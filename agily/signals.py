# agily/signals.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from typing import List, Set
import datetime

from .models import Issue

# --------------------------------------------------------------------------- #
# Helper utilities
# --------------------------------------------------------------------------- #
def _add(recipients: Set[str], user) -> None:
    """Add user's e-mail to the set if it is non-empty."""
    if user and getattr(user, "email", ""):
        recipients.add(user.email)

def get_notification_recipients(issue) -> List[str]:
    """Return a UNIQUE list of e-mail addresses for issue notifications."""
    User = get_user_model()
    recipients: Set[str] = set()

    # 1. Testers
    tester_groups = Group.objects.filter(name__iregex=r"^testers?$")
    testers = User.objects.filter(groups__in=tester_groups, is_active=True).distinct()
    for u in testers:
        _add(recipients, u)

    # 2. Super-admins
    superadmins = User.objects.filter(is_superuser=True, is_active=True)
    for u in superadmins:
        _add(recipients, u)

    # 3. Project admin
    _add(recipients, getattr(issue.project, "project_admin", None))

    # 4. Assignee
    _add(recipients, getattr(issue, "assignee", None))

    return list(recipients)

def send_styled_email(subject: str, issue, template_name: str, issue_url: str):
    """Send a styled HTML email with fallback to plain text."""
    
    # Create the HTML content with embedded styles
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        body {{
            background-color: #f4f6f8;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            -webkit-font-smoothing: antialiased;
            color: #333333;
        }}
        .email-wrapper {{
            width: 100%;
            background: #f4f6f8;
            padding: 20px 0;
        }}
        .email-container {{
            max-width: 600px;
            background: #ffffff;
            margin: 0 auto;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
            overflow: hidden;
            border: 1px solid #e1e4e8;
        }}
        .email-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 30px;
            text-align: center;
            color: #ffffff;
        }}
        .email-header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .email-header p {{
            margin: 10px 0 0 0;
            font-size: 16px;
            opacity: 0.9;
        }}
        .email-body {{
            padding: 40px 30px;
        }}
        .email-body p {{
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 20px;
            color: #444444;
        }}
        .issue-card {{
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border-radius: 12px;
            padding: 25px;
            margin: 25px 0;
            border-left: 5px solid #10b981;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .issue-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .issue-id {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
        }}
        .issue-title {{
            font-size: 22px;
            font-weight: 700;
            color: #1f2937;
            margin: 15px 0;
            line-height: 1.3;
        }}
        .details-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 25px 0;
        }}
        .detail-item {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }}
        .detail-label {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6b7280;
            margin-bottom: 6px;
            letter-spacing: 0.5px;
        }}
        .detail-value {{
            font-size: 15px;
            font-weight: 600;
            color: #1f2937;
        }}
        .severity-high {{ color: #dc2626; }}
        .severity-medium {{ color: #d97706; }}
        .severity-low {{ color: #059669; }}
        .status-open {{ color: #2563eb; }}
        .status-in-progress {{ color: #d97706; }}
        .status-resolved {{ color: #059669; }}
        .status-closed {{ color: #059669; }}
        .description-section {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 25px 0;
            border: 1px solid #e5e7eb;
        }}
        .description-section h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 12px;
        }}
        .description-content {{
            color: #4b5563;
            line-height: 1.7;
            font-size: 15px;
        }}
        .cta-section {{
            text-align: center;
            margin: 30px 0;
        }}
        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white !important;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
            transition: all 0.3s ease;
        }}
        .cta-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        }}
        .footer {{
            background: #f8fafc;
            text-align: center;
            padding: 30px;
            border-top: 1px solid #e5e7eb;
        }}
        .footer p {{
            color: #6b7280;
            font-size: 14px;
            margin: 5px 0;
        }}
        .footer .brand {{
            font-weight: 700;
            color: #667eea;
            font-size: 18px;
        }}
        @media only screen and (max-width: 620px) {{
            .email-container {{ width: 95% !important; margin: 10px auto; }}
            .email-header, .email-body, .footer {{ padding: 25px 20px; }}
            .details-grid {{ grid-template-columns: 1fr; gap: 15px; }}
            .issue-header {{ flex-direction: column; align-items: flex-start; }}
            .issue-id {{ margin-bottom: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            <div class="email-header">
                <h1>{'🆕 New Issue Created' if 'created' in template_name else '📝 Issue Updated'}</h1>
                <p>Agily Project Management System</p>
            </div>
            
            <div class="email-body">
                <p>Hello,</p>
                <p>{'A new issue has been created and requires your attention:' if 'created' in template_name else 'An issue has been updated:'}</p>
                
                <div class="issue-card">
                    <div class="issue-header">
                        <div class="issue-id">Issue #{issue.id}</div>
                    </div>
                    
                    <h2 class="issue-title">{issue.title}</h2>
                    
                    <div class="details-grid">
                        <div class="detail-item">
                            <div class="detail-label">Project</div>
                            <div class="detail-value">{issue.project.name}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Severity</div>
                            <div class="detail-value severity-{issue.severity.lower() if issue.severity else 'low'}">{issue.get_severity_display()}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Status</div>
                            <div class="detail-value status-{issue.status.lower().replace(' ', '-') if issue.status else 'open'}">{issue.get_status_display()}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Assigned To</div>
                            <div class="detail-value">{issue.assignee.username if issue.assignee else 'Unassigned'}</div>
                        </div>
                    </div>
                </div>
                
                <div class="description-section">
                    <h3>📋 Description</h3>
                    <div class="description-content">{issue.description.replace(chr(10), '<br>')}</div>
                </div>
                
                <div class="cta-section">
                    <a href="{issue_url}" class="cta-button" target="_blank" rel="noopener">
                        🔗 View Issue in Agily
                    </a>
                </div>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>The Agily Team</strong>
                </p>
            </div>
            
            <div class="footer">
                <p class="brand">Agily</p>
                <p>© {datetime.datetime.now().year} Agily Project Management. All rights reserved.</p>
                <p>This is an automated notification from your project management system.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    # Create plain text version (fallback)
    plain_text = f"""
{subject}

Hello,

{'A new issue has been created:' if 'created' in template_name else 'An issue has been updated:'}

Issue ID: {issue.id}
Title: {issue.title}
Project: {issue.project.name}
Severity: {issue.get_severity_display()}
Status: {issue.get_status_display()}
Assigned to: {issue.assignee.username if issue.assignee else 'Unassigned'}

Description:
{issue.description}

View the issue: {issue_url}

Best regards,
The Agily Team
"""

    recipient_list = get_notification_recipients(issue)
    if recipient_list:
        # Create EmailMultiAlternatives for HTML + text
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

# --------------------------------------------------------------------------- #
# Issue created
# --------------------------------------------------------------------------- #
@receiver(post_save, sender=Issue)
def issue_creation_notification(sender, instance: Issue, created: bool, **kwargs):
    """Send styled email notification when a new issue is created."""
    if not created:
        return

    subject = f"[Agily] Issue #{instance.id} has been created"
    issue_url = f"http://localhost:8000/issues/{instance.id}/"  # Update with your actual URL
    
    send_styled_email(subject, instance, "created", issue_url)

# --------------------------------------------------------------------------- #
# Issue updated
# --------------------------------------------------------------------------- #
@receiver(pre_save, sender=Issue)
def issue_update_notification(sender, instance: Issue, **kwargs):
    """Send styled email notification when an existing issue is updated."""
    if instance.id is None:
        return

    try:
        old_issue = Issue.objects.get(id=instance.id)
    except Issue.DoesNotExist:
        return

    # Detect meaningful changes
    changed = any([
        instance.title != old_issue.title,
        instance.description != old_issue.description,
        instance.status != old_issue.status,
        instance.severity != old_issue.severity,
        instance.assignee != old_issue.assignee,
        instance.solution != old_issue.solution,
    ])
    
    if not changed:
        return

    subject = f"[Agily] Issue #{instance.id} has been updated"
    issue_url = f"http://localhost:8000/issues/{instance.id}/"  # Update with your actual URL
    
    send_styled_email(subject, instance, "updated", issue_url)
