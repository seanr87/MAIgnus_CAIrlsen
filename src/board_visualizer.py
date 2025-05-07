"""
Chess board visualization utility for critical moments.
"""
import os
import io
import json
import chess
import chess.svg
import cairosvg
from PIL import Image
from config import REPORTS_DIR


def generate_board_image(fen, move=None, output_path=None):
    """
    Generate a chess board image from a FEN string.

    Args:
        fen (str): FEN string representing the board position
        move (chess.Move, optional): Move to highlight (if provided)
        output_path (str, optional): Path to save the image. If None, returns the image data.

    Returns:
        PIL.Image or str: Image object or path where the image was saved
    """
    try:
        board = chess.Board(fen)

        if move:
            if isinstance(move, str):
                try:
                    move = board.parse_san(move)
                except ValueError:
                    move = None
        svg_data = chess.svg.board(board, lastmove=move, size=400) if move else chess.svg.board(board, size=400)

        png_data = cairosvg.svg2png(bytestring=svg_data.encode('utf-8'))
        img = Image.open(io.BytesIO(png_data))

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            img.save(output_path, format='PNG')
            return output_path

        return img

    except Exception as e:
        print(f"Error generating board image: {e}")
        return None
