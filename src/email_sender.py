import yagmail
import os
import datetime
import openai
import markdown
import re
from dotenv import load_dotenv

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
USERNAME = os.getenv("CHESS_USERNAME")

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

REPORTS_DIR = "../reports"
DATA_DIR = "../data"
LOG_PATH = "../logs/email_sender.log"

def log(message):
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")

def generate_clever_title(summary_text):
    prompt = f"""
You are a witty chess coach and subject line writer.

Here’s a summary of a game:

\"\"\"{summary_text}\"\"\"

Generate a clever 5-word title that would grab attention in an email subject line.
Avoid generic words like "game" or "match"—make it vivid and specific.
"""
    try:
        client = openai.Client(api_key=openai.api_key)
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
        log(f"❌ GPT error: {str(e)}")
        return "Epic Takedown in Five Moves"

if __name__ == "__main__":
    analysis_path = os.path.join(REPORTS_DIR, "game_analysis.txt")
    if not os.path.exists(analysis_path):
        log(f"No analysis file found at {analysis_path}")
        exit()

    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_markdown = f.read()

    # === Extract sections ===
    def extract_section(heading):
        match = re.search(rf"## {heading}\s+(.*?)\s+##", analysis_markdown, re.DOTALL)
        return match.group(1).strip() if match else f"(No {heading} found.)"

    game_summary = extract_section("Game Summary")
    metadata_block = extract_section("Game Metadata")
    recommendations = extract_section("Recommendations")

    # Parse metadata fields from lines like "- Field: Value"
    meta = {}
    for line in metadata_block.splitlines():
        match = re.match(r"-\s*(.*?):\s*(.*)", line)
        if match:
            key, value = match.groups()
            meta[key.strip()] = value.strip()

    date = meta.get("Date", "N/A")
    opponent = meta.get("Opponent", "N/A")
    color = meta.get("Color", "N/A")
    result = meta.get("Result", "N/A")
    time_control = meta.get("Time Control", "N/A")
    opening = meta.get("Opening", "N/A")

    # === Validate metadata before sending ===
    required_fields = {
        "Date": date,
        "Opponent": opponent,
        "Color": color,
        "Time Control": time_control,
        "Opening": opening
    }

    missing = [k for k, v in required_fields.items() if v == "N/A" or "No " in v]

    if missing:
        pgn_files = sorted(
            [f for f in os.listdir(DATA_DIR) if f.endswith('.pgn')],
            key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)),
            reverse=True
        )
        latest_pgn = pgn_files[0] if pgn_files else "(Unknown PGN)"

        error_msg = (
            f"❌ Aborting send — missing metadata: {', '.join(missing)} "
            f"(from PGN: {latest_pgn})"
        )
        log(error_msg)

        # Log to a dedicated failures log
        failure_path = "../logs/send_failures.log"
        with open(failure_path, "a", encoding="utf-8") as fail_log:
            timestamp = datetime.datetime.now()
            fail_log.write(f"[{timestamp}] {error_msg}\n")

        exit()



    if USERNAME.lower() in opponent.lower():
        opponent = "Unknown (You played against someone else)"

    # Extract PGN
    pgn_match = re.search(r"## PGN\s+(.*)", analysis_markdown, re.DOTALL)
    pgn_text = pgn_match.group(1).strip() if pgn_match else "(No PGN found.)"

    # Convert markdown sections to HTML
    summary_html = markdown.markdown(game_summary)
    recommendations_html = markdown.markdown(recommendations)

    clever_title = generate_clever_title(game_summary)
    subject = f"MAI: {clever_title}"

    # === Compose HTML ===
    html_body = f"""
    <html>
    <head>
    <style>
    body {{
        font-family: 'Courier New', monospace;
        font-size: 16px;
        color: #00FFFF;
        background: radial-gradient(circle at top, #000010, #0a001a);
        padding: 24px;
    }}
    .container {{
        max-width: 720px;
        margin: auto;
        background: #111122;
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
        background: #000000;
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
        yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)
        yag.send(to=RECEIVER_EMAIL, subject=subject, contents=[html_body])
        log(f"✅ Email sent with subject: {subject}")
    except Exception as e:
        log(f"❌ Failed to send email: {str(e)}")
