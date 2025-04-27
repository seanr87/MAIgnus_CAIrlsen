"""
Email generation and sending module for chess analysis reports.
"""
import os
import re
import yagmail
import openai
import markdown
from config import (
    OPENAI_API_KEY, 
    SENDER_EMAIL, 
    EMAIL_APP_PASSWORD, 
    RECEIVER_EMAIL,
    REPORTS_DIR, 
    EMAIL_LOG, 
    FAILURES_LOG
)
from utils import log, get_latest_pgn_path

openai.api_key = OPENAI_API_KEY

def extract_section(content, heading):
    """
    Extract a section from the analysis report by heading.
    """
    match = re.search(rf"## {heading}\s+(.*?)(?=\s+##|\Z)", content, re.DOTALL)
    return match.group(1).strip() if match else f"(No {heading} found.)"

def parse_metadata(metadata_block):
    """
    Parse metadata fields from lines like "- Field: Value"
    """
    meta = {}
    for line in metadata_block.splitlines():
        match = re.match(r"-\s*(.*?):\s*(.*)", line)
        if match:
            key, value = match.groups()
            meta[key.strip()] = value.strip()
    return meta

def generate_clever_title(summary_text):
    """
    Use GPT to generate a clever email subject line.
    """
    prompt = f"""
You are a witty chess coach and subject line writer.

Here's a summary of a game:

\"\"\"{summary_text}\"\"\"

Generate a clever 5-word title that would grab attention in an email subject line.
Avoid generic words like "game" or "match"—make it vivid and specific.
"""
    try:
        client = openai.Client(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You write clever, catchy email titles."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=30,
            temperature=0.8
        )
        return response.choices[0].message.content.strip('" \n')
    except Exception as e:
        log(f"❌ GPT error: {str(e)}", EMAIL_LOG)
        return "Epic Chess Analysis Awaits You"

def send_analysis_email():
    """
    Format and send the chess analysis email.
    """
    analysis_path = os.path.join(REPORTS_DIR, "game_analysis.txt")
    if not os.path.exists(analysis_path):
        log(f"No analysis file found at {analysis_path}", EMAIL_LOG)
        return False

    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_markdown = f.read()

    # Extract sections from analysis
    game_summary = extract_section(analysis_markdown, "Game Summary")
    metadata_block = extract_section(analysis_markdown, "Game Metadata")
    recommendations = extract_section(analysis_markdown, "Recommendations")
    
    # Parse metadata 
    meta = parse_metadata(metadata_block)
    
    # Get values with defaults
    date = meta.get("Date", "N/A")
    opponent = meta.get("Opponent", "N/A")
    color = meta.get("Color", "N/A")
    result = meta.get("Result", "N/A")
    time_control = meta.get("Time Control", "N/A")
    opening = meta.get("Opening", "N/A")

    # Validate required fields
    required_fields = {
        "Date": date,
        "Opponent": opponent,
        "Color": color,
        "Time Control": time_control,
        "Opening": opening
    }

    missing = [k for k, v in required_fields.items() if v == "N/A" or "No " in v]

    if missing:
        latest_pgn = os.path.basename(get_latest_pgn_path() or "(Unknown PGN)")
        
        error_msg = (
            f"❌ Aborting send — missing metadata: {', '.join(missing)} "
            f"(from PGN: {latest_pgn})"
        )
        log(error_msg, EMAIL_LOG)

        # Log to a dedicated failures log
        with open(FAILURES_LOG, "a", encoding="utf-8") as fail_log:
            fail_log.write(f"{error_msg}\n")

        return False

    # Extract PGN
    pgn_match = re.search(r"## PGN\s+(.*)", analysis_markdown, re.DOTALL)
    pgn_text = pgn_match.group(1).strip() if pgn_match else "(No PGN found.)"

    # Convert markdown sections to HTML
    summary_html = markdown.markdown(game_summary)
    recommendations_html = markdown.markdown(recommendations)

    # Generate email subject
    clever_title = generate_clever_title(game_summary)
    subject = f"MAI: {clever_title}"

    # Compose HTML email body
# Find the html_body section in email_sender.py and replace it with this:

    html_body = f"""
    <html>
    <head>
    <style>
    body {{
        font-family: 'Courier New', monospace;
        font-size: 16px;
        color: #00FFFF;
        background-color: #000033;
        padding: 24px;
    }}
    .container {{
        max-width: 720px;
        margin: auto;
        background-color: #111133;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 0 20px #0ff;
        border: 1px solid #444;
    }}
    h1, h2, h3 {{
        color: #FF00FF;
        text-shadow: 0 0 5px #FF00FF;
        margin-top: 0;
    }}
    hr {{
        border: none;
        border-top: 1px solid #444;
        margin: 24px 0;
    }}
    pre {{
        font-size: 12px;
        color: #ccc;
        background-color: #000000;
        padding: 12px;
        border-radius: 6px;
        overflow-x: auto;
    }}
    </style>
    </head>
    <body>
    <div class="container">
        <h2>📀 MAIgnus: Game Breakdown</h2>
        <div><strong style="color:#0ff">Date:</strong> {date}</div>
        <div><strong style="color:#0ff">Opponent:</strong> {opponent}</div>
        <div><strong style="color:#0ff">Color:</strong> {color}</div>
        <div><strong style="color:#0ff">Time:</strong> {time_control}</div>
        <div><strong style="color:#0ff">Opening:</strong> {opening}</div>

        <hr>
        <h3>🧠 Summary</h3>
        <div>{summary_html}</div>

        <hr>
        <h3>⚙️ Recommendations</h3>
        <div>{recommendations_html}</div>
    </div>

    <pre>{pgn_text}</pre>
    </body>
    </html>
    """

    # Optional: suppress CSS log noise
    html_body = html_body.replace("\n", "")

    try:
        yag = yagmail.SMTP(SENDER_EMAIL, EMAIL_APP_PASSWORD)
        yag.send(to=RECEIVER_EMAIL, subject=subject, contents=[html_body])
        log(f"✅ Email sent with subject: {subject}", EMAIL_LOG)
        return True
    except Exception as e:
        log(f"❌ Failed to send email: {str(e)}", EMAIL_LOG)
        return False