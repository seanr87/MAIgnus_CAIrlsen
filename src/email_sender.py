"""
Email generation and sending module for chess analysis reports.
"""
import os
import re
import yagmail
import openai
import markdown
import os.path
import numpy as np
import json
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

def extract_stockfish_stats(content):
    """
    Extract Stockfish statistics from the analysis report.
    Properly handles both old and new format stats.
    """
    section = extract_section(content, "Stockfish Evaluation Summary")
    
    # Check if the new format with player-specific sections exists
    white_section_match = re.search(r"Your stats \(white\):(.*?)Opponent stats", section, re.DOTALL)
    black_section_match = re.search(r"Opponent stats \(black\):(.*?)(?=##|\Z)", section, re.DOTALL)
    
    # Alternative match for reversed colors
    if not white_section_match:
        white_section_match = re.search(r"Opponent stats \(white\):(.*?)(?=##|\Z)", section, re.DOTALL)
        black_section_match = re.search(r"Your stats \(black\):(.*?)Opponent stats", section, re.DOTALL)
    
    # If we found player-specific sections, parse them separately
    if white_section_match and black_section_match:
        white_stats = {}
        black_stats = {}
        
        # Parse white player stats
        white_section = white_section_match.group(1).strip()
        for line in white_section.splitlines():
            match = re.match(r"-\s*(.*?):\s*(.*)", line)
            if match:
                key, value = match.groups()
                white_stats[key.strip()] = value.strip()
        
        # Parse black player stats
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
    else:
        # Handle the old flat format
        stats = {}
        for line in section.splitlines():
            match = re.match(r"-\s*(.*?):\s*(.*)", line)
            if match:
                key, value = match.groups()
                stats[key.strip()] = value.strip()
        
        # Determine player color from metadata section
        metadata_section = extract_section(content, "Game Metadata")
        player_color = "white"  # Default
        for line in metadata_section.splitlines():
            if "Color:" in line:
                color_match = re.match(r"-\s*Color:\s*(.*)", line)
                if color_match and color_match.group(1).strip().lower() == "black":
                    player_color = "black"
                break
        
        # Create structured stats based on player color
        if player_color == "white":
            # If you're white, your stats first, opponent is black
            return {
                "white": {
                    "Average CPL": stats.get("Average CPL", "N/A"),
                    "Blunders": stats.get("Blunders", "N/A"),
                    "Mistakes": stats.get("Mistakes", "N/A"),
                    "Inaccuracies": stats.get("Inaccuracies", "N/A")
                },
                "black": {
                    # Use actual opponent stats if available or N/A
                    "Average CPL": stats.get("Opponent Average CPL", stats.get("Average CPL", "N/A")),
                    "Blunders": stats.get("Opponent Blunders", stats.get("Blunders", "N/A")),
                    "Mistakes": stats.get("Opponent Mistakes", stats.get("Mistakes", "N/A")),
                    "Inaccuracies": stats.get("Opponent Inaccuracies", stats.get("Inaccuracies", "N/A"))
                }
            }
        else:
            # If you're black, your stats second, opponent is white
            return {
                "black": {
                    "Average CPL": stats.get("Average CPL", "N/A"),
                    "Blunders": stats.get("Blunders", "N/A"),
                    "Mistakes": stats.get("Mistakes", "N/A"),
                    "Inaccuracies": stats.get("Inaccuracies", "N/A")
                },
                "white": {
                    # Use actual opponent stats if available or N/A
                    "Average CPL": stats.get("Opponent Average CPL", stats.get("Average CPL", "N/A")),
                    "Blunders": stats.get("Opponent Blunders", stats.get("Blunders", "N/A")),
                    "Mistakes": stats.get("Opponent Mistakes", stats.get("Mistakes", "N/A")),
                    "Inaccuracies": stats.get("Opponent Inaccuracies", stats.get("Inaccuracies", "N/A"))
                }
            }

def get_cpl_color(cpl):
    """
    Get color for CPL rating.
    """
    if cpl < 10:
        return "00ff00"  # Green
    elif cpl < 25:
        return "88ff00"  # Light green
    elif cpl < 50:
        return "ffff00"  # Yellow
    elif cpl < 100:
        return "ffaa00"  # Orange
    else:
        return "ff0000"  # Red

def get_cpl_rating(cpl):
    """
    Get text rating for CPL.
    """
    if cpl < 10:
        return "Excellent"
    elif cpl < 25:
        return "Good"
    elif cpl < 50:
        return "Decent"
    elif cpl < 100:
        return "Fair"
    else:
        return "Needs Work"

def create_stockfish_chart(stockfish_stats, metadata):
    """
    Create an HTML-based visualization of Stockfish analysis results.
    Uses player-specific data for both players.
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
        player_cpl = int(player_stats.get("Average CPL", 0)) if player_stats.get("Average CPL") != "N/A" else 0
        player_blunders = int(player_stats.get("Blunders", 0)) if player_stats.get("Blunders") != "N/A" else 0
        player_mistakes = int(player_stats.get("Mistakes", 0)) if player_stats.get("Mistakes") != "N/A" else 0
        player_inaccuracies = int(player_stats.get("Inaccuracies", 0)) if player_stats.get("Inaccuracies") != "N/A" else 0
        
        # Extract opponent stats
        opp_cpl = int(opponent_stats.get("Average CPL", 0)) if opponent_stats.get("Average CPL") != "N/A" else 0
        opp_blunders = int(opponent_stats.get("Blunders", 0)) if opponent_stats.get("Blunders") != "N/A" else 0
        opp_mistakes = int(opponent_stats.get("Mistakes", 0)) if opponent_stats.get("Mistakes") != "N/A" else 0
        opp_inaccuracies = int(opponent_stats.get("Inaccuracies", 0)) if opponent_stats.get("Inaccuracies") != "N/A" else 0
        
        # Get the rating text for each player
        player_rating_text = get_cpl_rating(player_cpl)
        player_rating_color = get_cpl_color(player_cpl)
        
        opp_rating_text = get_cpl_rating(opp_cpl)
        opp_rating_color = get_cpl_color(opp_cpl)
        
        # Rest of the function remains the same...
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

def setup_yagmail():
    """
    Configure yagmail with necessary credentials file.
    """
    try:
        # Check if .yagmail file exists
        yagmail_path = os.path.expanduser('~/.yagmail')
        if not os.path.exists(yagmail_path):
            # Create the .yagmail file with credentials
            with open(yagmail_path, 'w') as f:
                f.write(SENDER_EMAIL)
                
        return True
    except Exception as e:
        log(f"Failed to setup yagmail: {str(e)}", EMAIL_LOG)
        return False

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
    stockfish_stats = extract_stockfish_stats(analysis_markdown)

    # Parse metadata 
    meta = parse_metadata(metadata_block)

    # Generate chart
    chart_html = create_stockfish_chart(stockfish_stats, meta)
    

    
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
    
    # Create a simple HTML table for Stockfish stats as fallback
    stockfish_html = "<table style='width:100%; border-collapse: collapse;'>"
    for key, value in stockfish_stats.items():
        stockfish_html += f"<tr><td style='color:#0ff; padding:4px;'>{key}</td><td style='padding:4px;'>{value}</td></tr>"
    stockfish_html += "</table>"

    # Generate email subject
    clever_title = generate_clever_title(game_summary)
    subject = f"MAI: {clever_title}"

    # Compose HTML email body
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
        max-width: 800px;
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
        <h3>📊 Stockfish Analysis</h3>
        {chart_html if chart_html else stockfish_html}
        
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
        setup_yagmail()
        yag = yagmail.SMTP(SENDER_EMAIL, EMAIL_APP_PASSWORD)
        yag.send(to=RECEIVER_EMAIL, subject=subject, contents=[html_body])
        log(f"✅ Email sent with subject: {subject}", EMAIL_LOG)
        return True
    except Exception as e:
        log(f"❌ Failed to send email: {str(e)}", EMAIL_LOG)
        return False