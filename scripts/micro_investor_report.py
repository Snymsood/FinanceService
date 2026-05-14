"""
J-Morgan Wealth Management — Monthly Micro-Investor Report Generator.

Fetches live market data via yfinance (free, no API key),
generates an investment memo via Gemini 2.5 Pro,
emails the report, and saves an audit copy to reports/.
"""

import os
import smtplib
import json
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import yfinance as yf
from google import genai


# ---------------------------------------------------------------------------
# 1. Live Market Data (yfinance — free, no key required)
# ---------------------------------------------------------------------------

# Watchlist of tickers aligned with our hardwired sectors & exchange constraint.
# These are all NYSE/NASDAQ listed.
WATCHLIST = {
    "Semiconductors": ["NVDA", "AMD", "INTC", "TSM", "AVGO"],
    "IT Services": ["INFY", "WIT", "ACN"],
    "Green Energy": ["ENPH", "FSLR", "ICLN", "TAN", "AZRE"],
    "Space": ["LMT", "RKLB", "BA", "LUNR"],
    "Defense": ["RTX", "LMT", "NOC", "GD", "LHX"],
    "Biotech": ["AMGN", "MRNA", "VRTX", "REGN", "IBB"],
    "Crypto / Bitcoin": ["IBIT", "FBTC", "COIN", "MSTR"],
    "India (ADRs/ETFs)": ["INDA", "SMIN", "PIN", "INFY", "WIT", "HDB"],
}


def fetch_market_snapshot() -> str:
    """Pull live price, 52-week range, and recent news for every watchlist ticker."""
    lines = []
    seen = set()

    for sector, tickers in WATCHLIST.items():
        lines.append(f"\n## {sector}")
        for sym in tickers:
            if sym in seen:
                continue
            seen.add(sym)
            try:
                tk = yf.Ticker(sym)
                info = tk.info or {}
                price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
                low52 = info.get("fiftyTwoWeekLow", "N/A")
                high52 = info.get("fiftyTwoWeekHigh", "N/A")
                mkt_cap = info.get("marketCap", "N/A")
                name = info.get("shortName", sym)
                exchange = info.get("exchange", "N/A")

                lines.append(
                    f"- **{sym}** ({name}) | Exchange: {exchange} | "
                    f"Price: ${price} | 52w: ${low52}–${high52} | "
                    f"MktCap: {mkt_cap}"
                )

                # Grab latest news headlines (up to 3)
                news = tk.news or []
                for article in news[:3]:
                    title = article.get("title", "")
                    if title:
                        lines.append(f"  - 📰 {title}")

            except Exception as e:
                lines.append(f"- **{sym}** — data unavailable ({e})")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. Report Generation (Gemini 2.5 Pro — free tier, ~1 call/month)
# ---------------------------------------------------------------------------

def generate_report() -> str:
    """Load agent + skill definitions, inject live data, call Gemini 2.5 Pro."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    root = Path(__file__).parent.parent
    agent_path = root / "plugins/agent-plugins/j-morgan-wealth/agents/j-morgan-wealth.md"
    skill_path = root / "plugins/agent-plugins/j-morgan-wealth/skills/monthly-report/SKILL.md"

    with open(agent_path, "r") as f:
        agent_def = f.read()
    with open(skill_path, "r") as f:
        skill_def = f.read()

    # Fetch live market data
    print("Fetching live market data via yfinance...")
    market_data = fetch_market_snapshot()

    prompt = f"""
You are the J-Morgan Wealth Management Agent defined below:

{agent_def}

Using the workflow in this skill:

{skill_def}

## LIVE MARKET DATA (as of {datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M UTC')})

The following is real-time market data for your watchlist. Use these actual prices,
52-week ranges, and recent news to ground your analysis. Do NOT invent prices.

{market_data}

## FRACTIONAL SHARE NOTICE
Robinhood supports fractional shares (as small as $1). The investor allocates
fixed dollar amounts ($30 / $12.50 / $7.50), NOT whole share counts.
Always frame recommendations in dollar terms, not share quantities.
A $7.50 Moonshot allocation into a $500/share stock is perfectly valid.

Please generate the "Top 3" investment report for {datetime.now().strftime('%B %Y')}.
IMPORTANT: Your output will be placed directly into an HTML email.
Use HTML tags for formatting (e.g., <h2>, <b>, <p>, <ul>, <li>).
Avoid Markdown like ** or #.
Make it look like a premium Private Banking memo from J-Morgan Wealth.
Include the current price and a brief note on recent catalysts from the live data above.
"""

    # Try Pro first; fall back to Flash if quota is exhausted (429)
    for model_name in ["gemini-2.5-pro", "gemini-2.5-flash"]:
        try:
            print(f"  Calling {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            print(f"  ✓ Success with {model_name}")
            return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"  ⚠ {model_name} quota exhausted, falling back...")
                continue
            raise  # Re-raise non-quota errors

    raise RuntimeError("Both gemini-2.5-pro and gemini-2.5-flash failed.")


# ---------------------------------------------------------------------------
# 3. Audit Trail — save report to reports/ directory
# ---------------------------------------------------------------------------

def save_audit_copy(html_content: str) -> Path:
    """Save the generated report to reports/YYYY-MM.html for audit trail."""
    root = Path(__file__).parent.parent
    reports_dir = root / "reports"
    reports_dir.mkdir(exist_ok=True)

    month_stamp = datetime.now().strftime("%Y-%m")
    report_path = reports_dir / f"{month_stamp}.html"

    # Wrap in full HTML for standalone viewing
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>J-Morgan Wealth Report — {month_stamp}</title>
    <style>
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; line-height: 1.6; margin: 0; padding: 0; background: #f5f5f5; }}
        .container {{ width: 90%; max-width: 600px; margin: 20px auto; border: 1px solid #e1e1e1; padding: 30px; background-color: #ffffff; }}
        .header {{ border-bottom: 2px solid #1a1a1a; padding-bottom: 10px; margin-bottom: 25px; }}
        .header h1 {{ font-size: 22px; text-transform: uppercase; letter-spacing: 2px; margin: 0; color: #1a1a1a; }}
        h2 {{ color: #1a1a1a; font-size: 18px; margin-top: 25px; border-left: 4px solid #1a1a1a; padding-left: 10px; }}
        .meta {{ font-size: 11px; color: #888; margin-bottom: 20px; }}
        .disclaimer {{ font-size: 11px; color: #888; margin-top: 40px; border-top: 1px solid #eee; padding-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>J-Morgan Wealth Management</h1>
            <p style="margin: 5px 0; color: #666;">Private Strategic Roadmap</p>
        </div>
        <div class="meta">Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}</div>
        {html_content}
        <div class="disclaimer">
            <b>Disclaimer:</b> This memorandum is for informational purposes only.
            J-Morgan Wealth Management does not provide investment, legal, or tax advice via automated systems.
        </div>
    </div>
</body>
</html>"""

    report_path.write_text(full_html, encoding="utf-8")

    # Also save a metadata JSON sidecar for programmatic access
    meta_path = reports_dir / f"{month_stamp}.meta.json"
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "gemini-2.5-pro",
        "budget": "$50",
        "allocation": {"anchor": "$30", "growth": "$12.50", "moonshot": "$7.50"},
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return report_path


# ---------------------------------------------------------------------------
# 4. Email Delivery
# ---------------------------------------------------------------------------

def send_email(html_content: str):
    """Send the styled HTML report via SMTP."""
    smtp_server = os.environ["SMTP_SERVER"]
    smtp_port = int(os.environ["SMTP_PORT"])
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    msg = MIMEMultipart('alternative')
    msg['From'] = f"J-Morgan Wealth Management <{smtp_user}>"
    msg['To'] = recipient
    msg['Subject'] = f"Private Wealth Memo: Your Strategic Roadmap — {datetime.now().strftime('%B %Y')}"

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("J-Morgan Wealth Management — Monthly Report Pipeline")
    print("=" * 60)

    print("\n[1/4] Generating premium report via Gemini 2.5 Pro...")
    report = generate_report()

    print("[2/4] Saving audit copy to reports/ ...")
    report_path = save_audit_copy(report)
    print(f"      → Saved: {report_path}")

    print("[3/4] Sending HTML email...")
    send_email(report)

    print("[4/4] Done! Report delivered and archived.")
