#!/usr/bin/env python3
import sys
import argparse

import regular_chess as engine
import chess_ai as ai_player

PIECE_DISPLAY = {
    'K': '♔', 'k': '♚',
    'Q': '♕', 'q': '♛',
    'R': '♖', 'r': '♜',
    'B': '♗', 'b': '♝',
    'N': '♘', 'n': '♞',
    'P': '♙', 'p': '♟',
    '.': '.',
}


def print_board(board_state):
    board = engine.get_board(board_state)
    board_length = len(board)
    turn = board_state[0][0]

    sys.stdout.write("    ")
    for col in range(board_length):
        sys.stdout.write(f" {col:2d} ")
    sys.stdout.write("\n")
    sys.stdout.write("   +" + "---+" * board_length + "\n")

    # whosever turn it is appears at the bottom
    row_range = range(board_length - 1, -1, -1) if turn == 'W' else range(0, board_length)
    for row_index in row_range:
        sys.stdout.write(f"{row_index:2d} |")
        for col_index in range(len(board[row_index])):
            char = board[row_index][col_index]
            display_char = PIECE_DISPLAY.get(char, char)

            is_dark_square = (row_index + col_index) % 2 == 1
            if display_char == '.' and is_dark_square:
                display_char = '·'

            sys.stdout.write(f" {display_char} |")
        sys.stdout.write("\n")
        sys.stdout.write("   +" + "---+" * board_length + "\n")


def choose_piece(legal_moves):
    piece_to_moves = {}
    for piece_status, move_delta in legal_moves:
        piece_to_moves.setdefault(piece_status, []).append(move_delta)

    pieces = list(piece_to_moves.keys())
    while True:
        sys.stdout.write("Choose a piece to move (or 'q' to quit):\n")
        for index, (piece_type, (row, col)) in enumerate(pieces):
            sys.stdout.write(f"  {index + 1}) {piece_type} at ({row}, {col})\n")
        sys.stdout.flush()

        choice = input("> ").strip()
        if choice.lower() == 'q':
            return None, None
        if not choice.isdigit():
            continue
        index = int(choice) - 1
        if 0 <= index < len(pieces):
            piece_status = pieces[index]
            return piece_status, piece_to_moves[piece_status]


def choose_move(piece_status, move_deltas):
    piece_type, (row, col) = piece_status
    while True:
        sys.stdout.write(f"Choose how to move {piece_type} at ({row}, {col}) (or 'q' to quit):\n")
        for index, (delta_row, delta_col) in enumerate(move_deltas):
            sys.stdout.write(f"  {index + 1}) to ({row + delta_row}, {col + delta_col})\n")
        sys.stdout.flush()

        choice = input("> ").strip()
        if choice.lower() == 'q':
            return None
        if not choice.isdigit():
            continue
        index = int(choice) - 1
        if 0 <= index < len(move_deltas):
            return move_deltas[index]


def format_move_log_line(mover_side, piece_char, from_sq, to_sq):
    side_name = "White" if mover_side == "W" else "Black"
    piece_display = PIECE_DISPLAY.get(piece_char, piece_char)
    from_row, from_col = from_sq
    to_row, to_col = to_sq
    return f"{side_name} moved {piece_display} from ({from_row}, {from_col}) to ({to_row}, {to_col})"


def apply_move_and_log(board_state, piece_status, move_delta, move_log):
    mover_side = board_state[0][0]
    piece_char, (from_row, from_col) = piece_status
    delta_row, delta_col = move_delta
    from_sq = (from_row, from_col)
    to_sq = (from_row + delta_row, from_col + delta_col)

    new_state = engine.apply_move(board_state, piece_status, move_delta)

    move_log.append(format_move_log_line(mover_side, piece_char, from_sq, to_sq))
    return new_state


def parse_args():
    parser = argparse.ArgumentParser(description="Play regular chess in the terminal.")
    parser.add_argument("board", nargs="?", default="starting_board.txt",
                         help="board file to start from (default: starting_board.txt)")
    parser.add_argument("--mode", choices=["1v1", "ai"], default="ai",
                         help="'1v1' for local two-player, 'ai' to play chess_ai.py (default: ai)")
    parser.add_argument("--side", choices=["W", "B"], default="W",
                         help="which side you play in ai mode (default: W)")
    return parser.parse_args()


def main():
    #force UTF-8 stdout regardless of the console's codepage, since piped/redirected
    #output on Windows otherwise defaults to something like cp1252, which can't
    #encode the chess piece glyphs in PIECE_DISPLAY
    sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    vs_ai = args.mode == "ai"
    human_side = args.side if vs_ai else None

    with open(args.board, "r") as board_file:
        contents = board_file.read()
    board_state = engine.get_board_state(contents)

    move_log = []

    while True:
        sys.stdout.write("\nCurrent board:\n")
        print_board(board_state)
        sys.stdout.write(f"Turn: {board_state[0][0]}\n")

        legal_moves = engine.get_legal_moves(board_state)
        if not legal_moves:
            turn_is_white = board_state[0][0] == 'W'
            if engine.is_in_check(engine.get_board(board_state), turn_is_white):
                winner = "Black" if turn_is_white else "White"
                sys.stdout.write(f"Checkmate! {winner} wins.\n")
            else:
                sys.stdout.write("Stalemate. Draw.\n")
            break

        turn_side = board_state[0][0]
        is_human_turn = (not vs_ai) or (turn_side == human_side)

        if is_human_turn:
            piece_status, move_deltas = choose_piece(legal_moves)
            if piece_status is None:
                sys.stdout.write("Quit.\n")
                break

            move_delta = choose_move(piece_status, move_deltas)
            if move_delta is None:
                sys.stdout.write("Quit.\n")
                break

            board_state = apply_move_and_log(board_state, piece_status, move_delta, move_log)
        else:
            sys.stdout.write("AI is thinking...\n")
            sys.stdout.flush()
            move = ai_player.choose_move(board_state)
            piece_status, move_delta = move
            board_state = apply_move_and_log(board_state, piece_status, move_delta, move_log)

    sys.stdout.write("\n=== Move log ===\n")
    if move_log:
        for line in move_log:
            sys.stdout.write(line + "\n")
    else:
        sys.stdout.write("(no moves)\n")


if __name__ == "__main__":
    main()
