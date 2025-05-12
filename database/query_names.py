def parse_pgn_details(pgn_text):
    """Extract additional details from PGN text including termination condition."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game:
            # First try to get opening from PGN headers
            opening_name = game.headers.get('Opening', '').strip()
            
            # If no opening in headers or it's just "?", infer from moves
            if not opening_name or opening_name == "?" or opening_name.lower() == "unknown":
                opening_name = infer_opening_from_moves(game)
            
            result = {
                'opening_name': opening_name,
                'eco': game.headers.get('ECO', 'Unknown'),
                'total_moves': len(list(game.mainline_moves())),
                'termination': game.headers.get('Termination', 'Unknown')
            }
            
            # Map common termination conditions for clarity
            termination_map = {
                'Normal': 'Normal game end',
                'Time forfeit': 'Time expired',
                'Resignation': 'Resignation'
            }
            
            if result['termination'] in termination_map:
                result['termination'] = termination_map[result['termination']]
            
            return result
    except Exception as e:
        logger.error(f"Error parsing PGN details: {e}")
    
    return {
        'opening_name': 'Unknown',
        'eco': 'Unknown',
        'total_moves': 0,
        'termination': 'Unknown'
    }

def infer_opening_from_moves(game):
    """
    Infer the opening name from the first few moves.
    This is a copy of utils.infer_opening() to avoid import issues.
    """
    board = game.board()
    moves = []
    for move in game.mainline_moves():
        moves.append(board.san(move))
        board.push(move)

    # Map common sequences to opening names
    openings = {
        ("e4", "c5", "Nf3"): "Sicilian Defense",
        ("d4", "d5", "c4"): "Queen's Gambit",
        ("e4", "e5"): "Open Game",
        ("d4", "Nf6"): "Indian Game",
        ("e4", "c6"): "Caro-Kann Defense",
        ("e4", "e6"): "French Defense",
        ("Nf3", "Nf6", "c4"): "English Opening",
        ("d4", "d5"): "Queen's Pawn Opening",
        ("e4", "e5", "Nf3", "Nc6", "Bb5"): "Ruy Lopez",
        ("e4", "e5", "Nf3", "Nc6", "Bc4"): "Italian Game",
        ("d4", "Nf6", "c4", "e6"): "Queen's Indian Defense",
        ("d4", "Nf6", "c4", "g6"): "King's Indian Defense",
        ("e4", "c5", "f4"): "Grand Prix Attack",
        ("d4", "f5"): "Dutch Defense",
    }
    
    for sequence, name in openings.items():
        if moves[:len(sequence)] == list(sequence):
            return name
            
    return "Unknown Opening"
