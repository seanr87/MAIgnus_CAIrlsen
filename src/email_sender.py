import yagmail
import os
import datetime
from dotenv import load_dotenv

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()

# === CONFIGURATION ===
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

REPORTS_DIR = "../reports"
IMAGES_DIR = "../images"
LOG_PATH = "../logs/email_sender.log"

# === LOGGING FUNCTION ===
def log(message):
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")

# === SEND EMAIL FUNCTION ===
def send_email(subject, html_body, text_body, attachments, inline_image):
    try:
        yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)

        # Compose the email contents
        contents = [
            text_body,  # Plaintext body (optional for fallback)
            yagmail.inline(inline_image),
            html_body,
            *attachments
        ]

        # Send the email
        yag.send(
            to=RECEIVER_EMAIL,
            subject=subject,
            contents=contents
        )

        log(f"✅ Email sent to {RECEIVER_EMAIL} with subject '{subject}'")

    except Exception as e:
        log(f"❌ Failed to send email: {str(e)}")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    # File paths
    analysis_path = os.path.join(REPORTS_DIR, "game_analysis.txt")
    blunder_image_path = os.path.join(IMAGES_DIR, "blunder_position.png")

    # Validate files exist
    if not os.path.exists(analysis_path):
        log(f"No analysis file found at {analysis_path}")
        exit()

    if not os.path.exists(blunder_image_path):
        log(f"No blunder image found at {blunder_image_path}")
        exit()

    # Load the game analysis text
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_content = f.read()

    # Email subject
    subject = "MAIgnus_CAIrlsen: Game Review + Blunder Insight"

    # Text body fallback
    text_body = (
        "Hi Sean,\n\n"
        "Here's your latest game analysis from MAIgnus_CAIrlsen!\n\n"
        "---\n\n"
        "**Key Insight:**\n"
        "Attached is the board position before your biggest mistake.\n"
        "Review the diagram and recommended improvements below:\n\n"
        "---\n\n"
        + analysis_content
    )

    # HTML body (includes embedded blunder image)
    html_body = f"""
    <h2>Hi Sean,</h2>
    <p>Here's your latest game analysis from <strong>MAIgnus_CAIrlsen</strong>!</p>
    <hr>
    <h3>🔑 Key Insight</h3>
    <p>Below is the board position before your biggest mistake. Review the position and think about alternative moves.</p>
    <img src="cid:{os.path.basename(blunder_image_path)}">
    <hr>
    <pre>{analysis_content}</pre>
    """

    # Send the email
    send_email(
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        attachments=[analysis_path],
        inline_image=blunder_image_path
    )
