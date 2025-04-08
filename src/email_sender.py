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

# === CONFIGURATION ===
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

REPORTS_DIR = "../reports"
IMAGES_DIR = "../images"
DATA_DIR = "../data"
LOG_PATH = "../logs/email_sender.log"

# === LOGGING FUNCTION ===
def log(message):
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")

# === GPT: CREATE CLEVER TITLE ===
def generate_clever_title(summary_text):
    prompt = f"""
You are a witty chess coach and subject line writer.

Here’s a summary of a game:

\"\"\"{summary_text}\"\"\"

Generate a clever 5-word title that would grab attention in an email subject line.
Avoid generic words like \"game\" or \"match\"—make it vivid and specific.
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

# === MAIN EXECUTION ===
if __name__ == "__main__":
    analysis_path = os.path.join(REPORTS_DIR, "game_analysis.txt")
    blunder_image_path = os.path.join(IMAGES_DIR, "blunder_position.png")

    if not os.path.exists(analysis_path):
        log(f"No analysis file found at {analysis_path}")
        exit()

    # Load PGN text for footer
    pgn_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith('.pgn')],
        key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)),
        reverse=True
    )
    pgn_path = os.path.join(DATA_DIR, pgn_files[0]) if pgn_files else None
    pgn_text = open(pgn_path, "r", encoding="utf-8").read() if pgn_path else "(No PGN found)"

    # === LOAD AND PARSE GAME ANALYSIS ===
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_markdown = f.read()

    # Extract Game Summary
    summary_match = re.search(r"\*\*Game Summary\*\*\s+(.*?)\s+2\.", analysis_markdown, re.DOTALL)
    game_summary = summary_match.group(1).strip() if summary_match else "(No summary found.)"

    # Extract Metadata block
    metadata_match = re.search(r"\*\*Game Metadata\*\*\s+- Date:\s+(.*?)\s+- Opponent:\s+(.*?)\s+- Result:\s+(.*?)\s+- Moves:\s+(.*?)\s+- Time Control:\s+(.*?)\s+- Accuracy:[^\n]*\s+- Blunders:[^\n]*\s+- Mistakes:[^\n]*\s+- Inaccuracies:[^\n]*\s+- Opening:\s+(.*?)(\n|$)", analysis_markdown, re.DOTALL)
    metadata = metadata_match.groups() if metadata_match else ["N/A"] * 6
    date, opponent, result, moves, time_control, opening = metadata[:6]

    # Fix opponent name if it's the user
    if USERNAME.lower() in opponent.lower():
        opponent = "Unknown (You played against someone else)"

    # Extract Recommendations
    rec_match = re.search(r"\*\*Recommendations\*\*\s+(.*?)\s+4\.", analysis_markdown, re.DOTALL)
    recommendations = rec_match.group(1).strip() if rec_match else "(No recommendations found.)"

    clever_title = generate_clever_title(game_summary)
    subject = f"MAI: {clever_title}"

    # === COMPOSE HTML BODY ===
    html_body = f"""
    <html>
    <body style="font-family: 'Courier New', monospace; font-size: 16px; color: #EEE; background-color: #111; padding: 16px;">
        <div style="max-width: 720px; margin: auto; background: #222; padding: 16px; border-radius: 8px; border: 1px solid #444;">
            <div><strong>Date:</strong> {date}</div>
            <div><strong>Opponent:</strong> {opponent}</div>
            <div><strong>Color:</strong> {'White' if '1-0' in result else 'Black' if '0-1' in result else 'Unknown'}</div>
            <div><strong>Time:</strong> {time_control}</div>
            <div><strong>Opening:</strong> {opening}</div>
            <hr style="margin: 16px 0; border-color: #555;">
            <div><strong>Summary:</strong><br>{game_summary}</div>
            <hr style="margin: 16px 0; border-color: #555;">
            <div><strong>Recommendations:</strong><br>{recommendations}</div>
        </div>
        <pre style="margin-top: 20px; font-size: 12px; color: #888; background-color: #111; white-space: pre-wrap;">{pgn_text}</pre>
    </body>
    </html>
    """

    # === SEND EMAIL ===
    try:
        yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)
        yag.send(
            to=RECEIVER_EMAIL,
            subject=subject,
            contents=[html_body]
        )
        log(f"✅ Email sent with subject: {subject}")
    except Exception as e:
        log(f"❌ Failed to send email: {str(e)}")
