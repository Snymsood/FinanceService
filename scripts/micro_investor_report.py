import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from google import genai

def generate_report():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    
    root = Path(__file__).parent.parent
    agent_path = root / "plugins/agent-plugins/j-morgan-wealth/agents/j-morgan-wealth.md"
    skill_path = root / "plugins/agent-plugins/j-morgan-wealth/skills/monthly-report/SKILL.md"
    
    with open(agent_path, "r") as f:
        agent_def = f.read()
    with open(skill_path, "r") as f:
        skill_def = f.read()
        
    prompt = f"""
You are the J-Morgan Wealth Management Agent defined below:

{agent_def}

Using the workflow in this skill:

{skill_def}

Please generate the "Top 3" investment report for the current month. 
IMPORTANT: Your output will be placed directly into an HTML email. 
Use HTML tags for formatting (e.g., <h2>, <b>, <p>, <ul>, <li>). 
Avoid Markdown like ** or #. 
Make it look like a premium Private Banking memo from J-Morgan Wealth.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def send_email(html_content):
    smtp_server = os.environ["SMTP_SERVER"]
    smtp_port = int(os.environ["SMTP_PORT"])
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]
    
    msg = MIMEMultipart('alternative')
    msg['From'] = f"J-Morgan Wealth Management <{smtp_user}>"
    msg['To'] = recipient
    msg['Subject'] = "Private Wealth Memo: Your Strategic Roadmap"
    
    styled_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; line-height: 1.6; margin: 0; padding: 0; }}
            .container {{ width: 90%; max-width: 600px; margin: 20px auto; border: 1px solid #e1e1e1; padding: 30px; background-color: #ffffff; }}
            .header {{ border-bottom: 2px solid #1a1a1a; padding-bottom: 10px; margin-bottom: 25px; }}
            .header h1 {{ font-size: 22px; text-transform: uppercase; letter-spacing: 2px; margin: 0; color: #1a1a1a; }}
            h2 {{ color: #1a1a1a; font-size: 18px; margin-top: 25px; border-left: 4px solid #1a1a1a; padding-left: 10px; }}
            .disclaimer {{ font-size: 11px; color: #888; margin-top: 40px; border-top: 1px solid #eee; padding-top: 10px; }}
            .footer {{ font-size: 12px; color: #666; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>J-Morgan Wealth Management</h1>
                <p style="margin: 5px 0; color: #666;">Private Strategic Roadmap</p>
            </div>
            {html_content}
            <div class="disclaimer">
                <b>Disclaimer:</b> This memorandum is for informational purposes only. J-Morgan Wealth Management does not provide investment, legal, or tax advice via automated systems.
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(styled_html, 'html'))
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

if __name__ == "__main__":
    print("Generating premium report from J-Morgan Wealth...")
    report = generate_report()
    print("Sending HTML email...")
    send_email(report)
    print("Done!")
