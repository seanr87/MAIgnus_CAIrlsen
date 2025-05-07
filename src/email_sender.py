"""
Email generation and sending module for chess analysis reports.
Simplified to work with the modular analysis output.
"""
import os
import re
import markdown
import os.path
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from board_visualizer import generate_board_image
from openai import OpenAI
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

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

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

def extract_stockfish_stats(content):
    """
    Extract Stockfish statistics from the analysis report.
    Handles player-specific sections.
    """
    section = extract_section(content, "Stockfish Evaluation Summary")
    
    # Find player-specific sections
    white_section_match = re.search(r"Your stats \(white\):(.*?)Opponent stats", section, re.DOTALL)
    black_section_match = re.search(r"Opponent stats \(black\):(.*?)(?=##|\Z)", section, re.DOTALL)
    
    # Alternative match for reversed colors
    if not white_section_match:
        white_section_match = re.search(r"Opponent stats \(white\):(.*?)(?=##|\Z)", section, re.DOTALL)
        black_section_match = re.search(r"Your stats \(black\):(.*?)Opponent stats", section, re.DOTALL)
    
    # Parse player-specific sections
    white_stats = {}
    black_stats = {}
    
    # Parse white player stats
    if white_section_match:
        white_section = white_section_match.group(1).strip()
        for line in white_section.splitlines():
            match = re.match(r"-\s*(.*?):\s*(.*)", line)
            if match:
                key, value = match.groups()
                white_stats[key.strip()] = value.strip()
    
    # Parse black player stats
    if black_section_match:
        black_section = black_section_match.group(1).strip()
        for line in black_section.splitlines():
            match = re.match(r"-\s*(.*?):\s*(.*)", line)
            if match:
                key, value = match.groups()
                black_stats[key.strip()] = value.strip()
    
    return {
        "white": white_stats,
        "black": black_stats
    }

def get_cpl_color(cpl):
    """
    Get color for CPL rating.
    """
    try:
        cpl_value = int(cpl) if isinstance(cpl, str) and cpl.isdigit() else cpl
        if cpl_value < 10:
            return "00ff00"  # Green
        elif cpl_value < 25:
            return "88ff00"  # Light green
        elif cpl_value < 50:
            return "ffff00"  # Yellow
        elif cpl_value < 100:
            return "ffaa00"  # Orange
        else:
            return "ff0000"  # Red
    except (ValueError, TypeError):
        return "aaaaaa"  # Gray for N/A

def get_cpl_rating(cpl):
    """
    Get text rating for CPL.
    """
    try:
        cpl_value = int(cpl) if isinstance(cpl, str) and cpl.isdigit() else cpl
        if cpl_value < 10:
            return "Excellent"
        elif cpl_value < 25:
            return "Good"
        elif cpl_value < 50:
            return "Decent"
        elif cpl_value < 100:
            return "Fair"
        else:
            return "Needs Work"
    except (ValueError, TypeError):
        return "N/A"

def create_stockfish_chart(stockfish_stats, metadata):
    """
    Create an HTML-based visualization of Stockfish analysis results.
    """
    try:
        # Extract player metadata
        opponent_name = metadata.get("Opponent", "Opponent").split(" ")[0]  # Get just the name, not the rating
        player_color = metadata.get("Color", "White").lower()
        
        # Get the correct stats based on player color
        if player_color == "white":
            player_stats = stockfish_stats.get("white", {})
            opponent_stats = stockfish_stats.get("black", {})
        else:
            player_stats = stockfish_stats.get("black", {})
            opponent_stats = stockfish_stats.get("white", {})
        
        # Extract player stats (convert to integers if they're strings)
        player_cpl = int(player_stats.get("Average CPL", 0)) if player_stats.get("Average CPL", "N/A") != "N/A" else 0
        player_blunders = int(player_stats.get("Blunders", 0)) if player_stats.get("Blunders", "N/A") != "N/A" else 0
        player_mistakes = int(player_stats.get("Mistakes", 0)) if player_stats.get("Mistakes", "N/A") != "N/A" else 0
        player_inaccuracies = int(player_stats.get("Inaccuracies", 0)) if player_stats.get("Inaccuracies", "N/A") != "N/A" else 0
        
        # Extract opponent stats
        opp_cpl = int(opponent_stats.get("Average CPL", 0)) if opponent_stats.get("Average CPL", "N/A") != "N/A" else 0
        opp_blunders = int(opponent_stats.get("Blunders", 0)) if opponent_stats.get("Blunders", "N/A") != "N/A" else 0
        opp_mistakes = int(opponent_stats.get("Mistakes", 0)) if opponent_stats.get("Mistakes", "N/A") != "N/A" else 0
        opp_inaccuracies = int(opponent_stats.get("Inaccuracies", 0)) if opponent_stats.get("Inaccuracies", "N/A") != "N/A" else 0
        
        # Get the rating text for each player
        player_rating_text = get_cpl_rating(player_cpl)
        player_rating_color = get_cpl_color(player_cpl)
        
        opp_rating_text = get_cpl_rating(opp_cpl)
        opp_rating_color = get_cpl_color(opp_cpl)
        
        # Create HTML chart
        html = f'''
        <table cellspacing="0" cellpadding="0" border="0" width="100%" style="border-collapse: collapse; font-family: 'Courier New', monospace; background-color: #0a0a2a;">
            <tr>
                <th colspan="3" style="font-size: 20px; padding: 15px 0; color: #FF00FF; text-align: center;">
                    <span style="display: inline-block; margin-right: 10px;">📊</span> Stockfish Analysis
                </th>
            </tr>
            
            <tr>
                <th width="50%" style="color: #FF00FF; text-align: center; padding: 10px 0; font-size: 16px; border-top: 1px solid #444; border-bottom: 1px solid #444;">
                    YOU
                </th>
                <th width="50%" style="color: #FF00FF; text-align: center; padding: 10px 0; font-size: 16px; border-top: 1px solid #444; border-bottom: 1px solid #444;">
                    {opponent_name.upper()}
                </th>
            </tr>
            
            <!-- CPL Ratings Row -->
            <tr>
                <td style="padding: 15px 0; text-align: center;">
                    <div style="font-size: 16px; margin-bottom: 5px; color: #00FFFF;">Average CPL: {player_cpl}</div>
                    <div style="display: inline-block; padding: 6px 15px; border-radius: 15px; background-color: #{player_rating_color}; color: #000;">
                        {player_rating_text}
                    </div>
                </td>
                <td style="padding: 15px 0; text-align: center;">
                    <div style="font-size: 16px; margin-bottom: 5px; color: #00FFFF;">Average CPL: {opp_cpl}</div>
                    <div style="display: inline-block; padding: 6px 15px; border-radius: 15px; background-color: #{opp_rating_color}; color: #000;">
                        {opp_rating_text}
                    </div>
                </td>
            </tr>
            
            <!-- Headers for error types -->
            <tr>
                <td style="padding: 10px 0 5px 0;">
                    <table cellspacing="0" cellpadding="0" border="0" width="100%">
                        <tr>
                            <td width="33%" style="color: #00FFFF; text-align: center; font-size: 14px;">Blunders:</td>
                            <td width="33%" style="color: #00FFFF; text-align: center; font-size: 14px;">Mistakes:</td>
                            <td width="33%" style="color: #00FFFF; text-align: center; font-size: 14px;">Inaccuracies:</td>
                        </tr>
                        <tr>
                            <td style="color: #00FFFF; text-align: center; font-size: 14px;">{player_blunders}</td>
                            <td style="color: #00FFFF; text-align: center; font-size: 14px;">{player_mistakes}</td>
                            <td style="color: #00FFFF; text-align: center; font-size: 14px;">{player_inaccuracies}</td>
                        </tr>
                    </table>
                </td>
                <td style="padding: 10px 0 5px 0;">
                    <table cellspacing="0" cellpadding="0" border="0" width="100%">
                        <tr>
                            <td width="33%" style="color: #00FFFF; text-align: center; font-size: 14px;">Blunders:</td>
                            <td width="33%" style="color: #00FFFF; text-align: center; font-size: 14px;">Mistakes:</td>
                            <td width="33%" style="color: #00FFFF; text-align: center; font-size: 14px;">Inaccuracies:</td>
                        </tr>
                        <tr>
                            <td style="color: #00FFFF; text-align: center; font-size: 14px;">{opp_blunders}</td>
                            <td style="color: #00FFFF; text-align: center; font-size: 14px;">{opp_mistakes}</td>
                            <td style="color: #00FFFF; text-align: center; font-size: 14px;">{opp_inaccuracies}</td>
                        </tr>
                    </table>
                </td>
            </tr>
            
            <!-- Visual bars for errors -->
            <tr>
                <td style="padding: 5px 10px 20px 10px; vertical-align: bottom;">
                    <table cellspacing="0" cellpadding="0" border="0" width="100%" style="height: 100px;">
                        <tr valign="bottom">
                            <td width="33%" align="center" style="vertical-align: bottom;">
                                <div style="width: 30px; height: {min(100, player_blunders * 25)}px; background-color: #ff0000; margin: 0 auto;"></div>
                            </td>
                            <td width="33%" align="center" style="vertical-align: bottom;">
                                <div style="width: 30px; height: {min(100, player_mistakes * 25)}px; background-color: #ffaa00; margin: 0 auto;"></div>
                            </td>
                            <td width="33%" align="center" style="vertical-align: bottom;">
                                <div style="width: 30px; height: {min(100, player_inaccuracies * 10)}px; background-color: #ffff00; margin: 0 auto;"></div>
                            </td>
                        </tr>
                    </table>
                </td>
                <td style="padding: 5px 10px 20px 10px; vertical-align: bottom;">
                    <table cellspacing="0" cellpadding="0" border="0" width="100%" style="height: 100px;">
                        <tr valign="bottom">
                            <td width="33%" align="center" style="vertical-align: bottom;">
                                <div style="width: 30px; height: {min(100, opp_blunders * 25)}px; background-color: #ff0000; margin: 0 auto;"></div>
                            </td>
                            <td width="33%" align="center" style="vertical-align: bottom;">
                                <div style="width: 30px; height: {min(100, opp_mistakes * 25)}px; background-color: #ffaa00; margin: 0 auto;"></div>
                            </td>
                            <td width="33%" align="center" style="vertical-align: bottom;">
                                <div style="width: 30px; height: {min(100, opp_inaccuracies * 10)}px; background-color: #ffff00; margin: 0 auto;"></div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        '''
        
        return html
        
    except Exception as e:
        log(f"Chart generation error: {str(e)}", EMAIL_LOG)
        return None

def create_critical_moment_visuals():
    """
    Create HTML visualizations for critical moments using the FEN positions and attach images.
    """
    try:
        critical_path = os.path.join(REPORTS_DIR, "critical_moments.json")
        if not os.path.exists(critical_path):
            log("No critical moments data found.", EMAIL_LOG)
            return "", []

        with open(critical_path, "r", encoding="utf-8") as f:
            critical_data = json.load(f)

        critical_moments = critical_data.get("critical_moments", [])
        if not critical_moments:
            return "", []

        html = ""
        attachments = []

        for i, moment in enumerate(critical_moments, 1):
            fen = moment.get("fen", "")
            move_num = moment.get("move_num", "?")
            player = moment.get("player", "").title()
            move = moment.get("move", "")
            cp_loss = moment.get("cp_loss", "")
            analysis_text = moment.get("analysis", "").strip()

            img_filename = f"board_{i}.png"
            img_path = os.path.join(REPORTS_DIR, "boards", img_filename)
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            generate_board_image(fen, output_path=img_path)
            attachments.append((img_filename, img_path))

            board_html = f"""
            <div style=\"margin: 20px 0; padding: 10px; background-color: #111133; border-radius: 8px; border: 1px solid #444;\">
                <h3 style=\"color: #FF00FF; margin-top: 0;\">Critical Moment {i}: {player}'s Move {move_num} ({move})</h3>
                <div style=\"text-align: center; margin: 15px 0;\">
                    <img src="cid:{img_filename}" alt="Chess Position">
                </div>
                <div style=\"color: #ff6600; font-weight: bold; text-align: center; margin-bottom: 10px;\">
                    Centipawn Loss: {cp_loss}
                </div>
                <div style="color: #00ccff; padding: 10px 20px; font-size: 14px; font-style: italic; border-top: 1px solid #444;">
                    {analysis_text}
                </div>
            </div>
            """
            html += board_html

        return html, attachments

    except Exception as e:
        log(f"Critical moment visualization error: {str(e)}", EMAIL_LOG)
        return "", []

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
    Format and send the chess analysis email with modular analysis results using smtplib.
    """
    analysis_path = os.path.join(REPORTS_DIR, "game_analysis.txt")
    if not os.path.exists(analysis_path):
        log(f"No analysis file found at {analysis_path}", EMAIL_LOG)
        return False

    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_markdown = f.read()

    game_summary = extract_section(analysis_markdown, "Game Narrative Summary")
    metadata_block = extract_section(analysis_markdown, "Game Metadata")
    highlights_lowlights = extract_section(analysis_markdown, "Highlights and Lowlights")
    coaching_point = extract_section(analysis_markdown, "Coaching Point")
    stockfish_stats = extract_stockfish_stats(analysis_markdown)
    meta = parse_metadata(metadata_block)

    chart_html = create_stockfish_chart(stockfish_stats, meta)
    critical_moments_html, attachments = create_critical_moment_visuals()

    # Extract PGN and convert sections
    pgn_match = re.search(r"## PGN\s+(.*)", analysis_markdown, re.DOTALL)
    pgn_text = pgn_match.group(1).strip() if pgn_match else "(No PGN found.)"

    summary_html = markdown.markdown(game_summary)
    highlights_html = markdown.markdown(highlights_lowlights)
    coaching_html = markdown.markdown(coaching_point)
    clever_title = generate_clever_title(game_summary)
    subject = f"MAI: {clever_title}"

    # Build HTML email body
    html_body = f"""
    <html><body style="background-color:#000033;color:#00FFFF;font-family:'Courier New';padding:24px">
    <h2>📀 MAIgnus: Game Breakdown</h2>
    <div><b>Date:</b> {meta.get('Date')}</div>
    <div><b>Opponent:</b> {meta.get('Opponent')}</div>
    <div><b>Color:</b> {meta.get('Color')}</div>
    <div><b>Time:</b> {meta.get('Time Control')}</div>
    <div><b>Opening:</b> {meta.get('Opening')}</div>
    <hr><h3>🧠 Game Summary</h3>{summary_html}
    <hr><h3>⚡ Critical Moments</h3>{critical_moments_html}
    <hr><h3>📊 Stockfish Analysis</h3>{chart_html}
    <hr><h3>🔍 Highlights and Lowlights</h3>{highlights_html}
    <hr><h3>🎯 Coaching Point</h3>{coaching_html}
    <pre style="color:#ccc;background:#000;padding:12px">{pgn_text}</pre>
    </body></html>
    """

    try:
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText("Chess analysis report attached as HTML.", "plain"))
        alt_part.attach(MIMEText(html_body, "html"))
        msg.attach(alt_part)

        for cid, path in attachments:
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
                img.add_header("Content-ID", f"<{cid}>")
                img.add_header("Content-Disposition", "inline", filename=cid)
                msg.attach(img)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, EMAIL_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

        log(f"✅ Email sent with subject: {subject}", EMAIL_LOG)
        return True

    except Exception as e:
        log(f"❌ Failed to send email: {str(e)}", EMAIL_LOG)
        return False
