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

    if not os.path.exists(blunder_image_path):
        log(f"No blunder image found at {blunder_image_path}")
        exit()

    # === LOAD AND PARSE GAME ANALYSIS ===
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_markdown = f.read()

    # Extract Game Summary
    match = re.search(r"\*\*Game Summary\*\*\s+(.*?)\s+2\.", analysis_markdown, re.DOTALL)
    game_summary = match.group(1).strip() if match else "No summary found."

    # Extract Metadata block
    metadata_match = re.search(r"\*\*Game Metadata\*\*\s+- Date:\s+(.*?)\s+- Opponent:\s+(.*?)\s+- Result:\s+(.*?)\s+- Moves:\s+(.*?)\s+- Time Control:\s+(.*?)\s+- Accuracy:\s+(.*?)\s+- Blunders:\s+(.*?)\s+- Mistakes:\s+(.*?)\s+- Inaccuracies:\s+(.*?)\s+- Opening:\s+(.*?)(\n|$)", analysis_markdown, re.DOTALL)

    metadata = metadata_match.groups() if metadata_match else ["N/A"] * 10

    clever_title = generate_clever_title(game_summary)
    subject = f"MAI: {clever_title}"

    # Convert analysis to HTML
    analysis_html = markdown.markdown(analysis_markdown)

    # === COMPOSE HTML BODY ===
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #fafafa; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.05);">
            <h2 style="color: #333;">Hi Sean,</h2>
            <p>Here's your latest game review from <strong>MAIgnus_CAIrlsen</strong>.</p>

            <h3 style="color: #0056b3;">🔑 Key Insight</h3>
            <p><strong>Your most significant mistake was on move 7.</strong> Review the board position below and consider alternative strategies.</p>

            <img src="cid:{os.path.basename(blunder_image_path)}" alt="Blunder Position" style="width: 100%; max-width: 400px; margin: 20px 0; display: block; border-radius: 5px;">

            <h3 style="color: #0056b3;">📊 Game Overview</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td>Date</td><td>{metadata[0]}</td></tr>
                <tr><td>Opponent</td><td>{metadata[1]}</td></tr>
                <tr><td>Result</td><td>{metadata[2]}</td></tr>
                <tr><td>Moves</td><td>{metadata[3]}</td></tr>
                <tr><td>Time Control</td><td>{metadata[4]}</td></tr>
                <tr><td>Accuracy</td><td>{metadata[5]}</td></tr>
                <tr><td>Blunders</td><td>{metadata[6]}</td></tr>
                <tr><td>Mistakes</td><td>{metadata[7]}</td></tr>
                <tr><td>Inaccuracies</td><td>{metadata[8]}</td></tr>
                <tr><td>Opening</td><td>{metadata[9]}</td></tr>
            </table>

            <hr style="margin: 40px 0; border: none; border-top: 1px solid #eee;">
            <h3 style="color: #0056b3;">📝 Full Analysis</h3>
            <div style="background: #f9f9f9; padding: 15px; border-radius: 5px;">
                {analysis_html}
            </div>

            <hr style="margin: 40px 0; border: none; border-top: 1px solid #eee;">
            <p style="font-size: 0.85em; color: #999;">Generated by MAIgnus_CAIrlsen | Your AI Chess Coach</p>
        </div>
    </body>
    </html>
    """

    # === SEND EMAIL ===
    try:
        yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)
        yag.send(
            to=RECEIVER_EMAIL,
            subject=subject,
            contents=[
                yagmail.inline(blunder_image_path),
                html_body
            ]
        )
        log(f"✅ Email sent with subject: {subject}")
    except Exception as e:
        log(f"❌ Failed to send email: {str(e)}")
