import yagmail
import os
import datetime
from dotenv import load_dotenv
import markdown

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

def send_email(subject, body_html, blunder_image):
    try:
        yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)

        yag.send(
            to=RECEIVER_EMAIL,
            subject=subject,
            contents=[
                yagmail.inline(blunder_image),
                body_html
            ]
        )

        log(f"✅ Inline email sent to {RECEIVER_EMAIL} with subject '{subject}'")
    except Exception as e:
        log(f"❌ Failed to send inline email: {str(e)}")

if __name__ == "__main__":
    # === PATHS ===
    analysis_path = os.path.join(REPORTS_DIR, "game_analysis.txt")
    blunder_image_path = os.path.join(IMAGES_DIR, "blunder_position.png")

    if not os.path.exists(analysis_path):
        log(f"No analysis file found at {analysis_path}")
        exit()

    if not os.path.exists(blunder_image_path):
        log(f"No blunder image found at {blunder_image_path}")
        exit()

    # === LOAD AND CONVERT ANALYSIS ===
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_markdown = f.read()

    # For now, assume that the LLM returns:
    # - Game Summary
    # - Key Insight
    # - Game Metadata (structured list)
    # - Recommendations (max 2)
    # - Call to Action

    analysis_html = markdown.markdown(analysis_markdown)

    subject = "MAIgnus_CAIrlsen: Game Review + Key Insight"

    # === COMPOSE HTML BODY ===
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #fafafa; padding: 20px;">

        <div style="max-width: 600px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.05);">

            <h2 style="color: #333;">Hi Sean,</h2>

            <p>Here's your latest game review from <strong>MAIgnus_CAIrlsen</strong>.</p>

            <!-- 🔑 KEY INSIGHT -->
            <h3 style="color: #0056b3;">🔑 Key Insight</h3>
            <p><strong>Your most significant mistake was on move 7.</strong> Review the board position below and consider alternative strategies.</p>

            <img src="cid:{os.path.basename(blunder_image_path)}" alt="Blunder Position" style="width: 100%; max-width: 400px; margin: 20px 0; display: block; border-radius: 5px;">

            <!-- 📊 GAME METADATA -->
            <h3 style="color: #0056b3;">📊 Game Overview</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Date</td>
                    <td style="padding: 8px; border: 1px solid #eee;">March 17, 2025</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Opponent</td>
                    <td style="padding: 8px; border: 1px solid #eee;">ChessMaster99</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Result</td>
                    <td style="padding: 8px; border: 1px solid #eee;">Loss</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Moves</td>
                    <td style="padding: 8px; border: 1px solid #eee;">28</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Time Control</td>
                    <td style="padding: 8px; border: 1px solid #eee;">10|0</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Accuracy</td>
                    <td style="padding: 8px; border: 1px solid #eee;">82%</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Blunders</td>
                    <td style="padding: 8px; border: 1px solid #eee;">1</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Mistakes</td>
                    <td style="padding: 8px; border: 1px solid #eee;">2</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Inaccuracies</td>
                    <td style="padding: 8px; border: 1px solid #eee;">3</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #eee;">Opening</td>
                    <td style="padding: 8px; border: 1px solid #eee;">Ruy Lopez, Morphy Defense (C78)</td>
                </tr>
            </table>

            <!-- 📝 FULL ANALYSIS (Game Summary + Rec + CTA from LLM) -->
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
    send_email(subject, html_body, blunder_image_path)
