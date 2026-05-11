import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import anthropic

def generate_report():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    # Read agent and skill definitions
    root = Path(__file__).parent.parent
    agent_path = root / "plugins/agent-plugins/micro-investor-agent/agents/micro-investor-agent.md"
    skill_path = root / "plugins/agent-plugins/micro-investor-agent/skills/monthly-report/SKILL.md"
    
    with open(agent_path, "r") as f:
        agent_def = f.read()
    with open(skill_path, "r") as f:
        skill_def = f.read()
        
    prompt = f"""
You are the Micro-Investor Agent defined below:

{agent_def}

Using the workflow in this skill:

{skill_def}

Please generate the "Top 3" investment report for May 2026. 
Perform necessary research (simulate current market conditions based on your knowledge if tools are not available) 
and output ONLY the email content.
"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return message.content[0].text

def send_email(content):
    smtp_server = os.environ["SMTP_SERVER"]
    smtp_port = int(os.environ["SMTP_PORT"])
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = recipient
    msg['Subject'] = "Your Monthly $50 Investment Roadmap"
    
    msg.attach(MIMEText(content, 'plain'))
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

if __name__ == "__main__":
    print("Generating report...")
    report = generate_report()
    print("Report generated. Sending email...")
    send_email(report)
    print("Done!")
