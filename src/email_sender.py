import yagmail
import os
import datetime

# === CONFIGURATION ===
SENDER_EMAIL = "sean.r.oreilly87@gmail.com"  # ✅ Replace with your email
APP_PASSWORD = "trnn jeko nyyo pbbb"     # ✅ Replace with your app password
RECEIVER_EMAIL = "sean.r.oreilly87@gmail.com"  # ✅ Where the report goes (could be the same)

REPORTS_DIR = "../reports"
LOG_PATH = "../logs/email_sender.log"

# === LOGGING FUNCTION ===
def log(message):
    timestamp = datetime.datetime.now()
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(full_message + "\n")

def send_email(subject, body, attachment_path=None):
    try:
        yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)
        contents = [body]

        if attachment_path and os.path.exists(attachment_path):
            contents.append(attachment_path)
            log(f"Attaching file: {attachment_path}")

        yag.send(
            to=RECEIVER_EMAIL,
            subject=subject,
            contents=contents
        )
        log(f"✅ Email sent to {RECEIVER_EMAIL} with subject '{subject}'")
    except Exception as e:
        log(f"❌ Failed to send email: {str(e)}")

if __name__ == "__main__":
    # Example usage
    report_file = os.path.join(REPORTS_DIR, "game_analysis.txt")

    if not os.path.exists(report_file):
        log(f"No report file found at {report_file}")
        exit()

    with open(report_file, "r", encoding="utf-8") as f:
        analysis_content = f.read()

    subject = "MAIgnus_CAIrlsen: Game Review Report"
    body = "Hi Sean,\n\nHere's your latest game analysis from MAIgnus_CAIrlsen. See the attached report for details!\n\n---\n\n" + analysis_content

    send_email(subject, body, report_file)
