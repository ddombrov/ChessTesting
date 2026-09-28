#!/usr/bin/env python3
import sys

import regular_chess as engine

SEARCH_DEPTH = 2
transposition_table = {}

OPENING_BOOK = {
    0: ('P', (1, 4), (2, 0)),      #white: king's pawn two-square advance
    1: ('p', (6, 4), (-2, 0)),     #black: king's pawn two-square advance
    2: ('N', (0, 1), (2, 1)),      #white: develop queenside knight
    3: ('n', (7, 6), (-2, -1)),    #black: develop kingside knight
}

PIECE_WORTH = {
    'P': 1, 'p': 1,   #pawn worth 1 in regular chess
    'N': 3, 'n': 3,   #knight worth 3 in regular chess
    'B': 3, 'b': 3,   #bishop worth 3 in regular chess
    'R': 5, 'r': 5,   #rook worth 5 in regular chess
    'Q': 9, 'q': 9,   #queen worth 9 in regular chess
    'K': 200, 'k': 200, #king worth effectively infinite
}

#score for a position where the side to move has been checkmated
CHECKMATE_SCORE = 100000.0

def get_state_id(board_state):

    #convert board state (list of lists) to hashable tuple of tuples
    return tuple(tuple(row) for row in board_state)

def find_edges_from_state(board_state):

    #generate all possible moves's board states from the current board state
    legal_moves = engine.get_legal_moves(board_state)
    edges = []
    for piece_status, move_delta in legal_moves:
        child_state = engine.apply_move(board_state, piece_status, move_delta)
        edges.append(((piece_status, move_delta), child_state))
    return edges

def is_leaf_position(board_state, depth):

    #if the depth is 0 (meaning we have reached the max depth) or there are no legal moves, it is a leaf position
    return depth <= 0 or not engine.get_legal_moves(board_state)

def evaluate_board(board_state):

    #evaluate the board state
    board = engine.get_board(board_state)
    current_is_white = board_state[0][0] == 'W'

    #checkmate/stalemate: the side to move has no legal moves
    if not engine.get_legal_moves(board_state):
        if engine.is_in_check(board, current_is_white):
            return -CHECKMATE_SCORE  # the side to move has been checkmated
        return 0.0  # stalemate: draw

    total = 0

    #count total pieces on the board to detect endgame (fewer than 12 pieces left)
    total_piece_count = sum(1 for row in board for cell in row if cell.isalpha())
    is_endgame = total_piece_count < 12

    center_row = (len(board) - 1) / 2
    max_distance = center_row * 2

    for row_index, row in enumerate(board):
        center_col = (len(row) - 1) / 2
        for col_index, cell in enumerate(row):
            worth = PIECE_WORTH.get(cell, 0)
            if worth == 0:
                continue

            #endgame adjustments
            if is_endgame:
                if cell in ("P", "p"):
                    worth *= 1.5
                if cell in ("K", "k"):
                    distance_to_center = abs(row_index - center_row) + abs(col_index - center_col)
                    worth += (max_distance - distance_to_center) * 0.3

            # add the worth of the piece if it is mine, otherwise subtract it
            is_mine = (current_is_white and cell.isupper()) or (not current_is_white and cell.islower())
            total += worth if is_mine else -worth

    return total


def dfs_with_alpha_beta(board_state, depth, alpha, beta):

    #if the depth is 0 or there are no legal moves, return the evaluated board state
    if depth <= 0 or is_leaf_position(board_state, depth):
        return evaluate_board(board_state)

    #transposition table
    #a cached result from a deeper search is more accurate
    state_id = get_state_id(board_state)
    if state_id in transposition_table:
        cached_depth, cached_score = transposition_table[state_id]
        if cached_depth >= depth:
            return cached_score

    best_score = None

    #examine captures first
    moves_with_scores = []
    board = engine.get_board(board_state)
    for (piece_status, move_delta), destination_state in find_edges_from_state(board_state):
        from_row, from_col = piece_status[1]

        #estimate capture value for ordering
        capture_value = 0.0
        target_row = from_row + move_delta[0]
        target_col = from_col + move_delta[1]
        if 0 <= target_row < len(board) and 0 <= target_col < len(board[target_row]):
            target_piece = board[target_row][target_col]
            if target_piece.isalpha():
                capture_value = PIECE_WORTH.get(target_piece, 0)
        moves_with_scores.append((capture_value, destination_state))

    moves_with_scores.sort(key=lambda item: item[0], reverse=True)

    for _capture_val, destination_state in moves_with_scores:

        child_alpha = None if beta is None else -beta
        child_beta = None if alpha is None else -alpha
        child_score = dfs_with_alpha_beta(destination_state, depth - 1, child_alpha, child_beta)
        if child_score is None:
            continue
        score = -child_score

        if best_score is None or score > best_score:
            best_score = score

        if alpha is None or score > alpha:
            alpha = score

        if beta is not None and alpha is not None and alpha >= beta:
            break

    #if we didn't find any children, evaluate this position
    if best_score is None:
        return evaluate_board(board_state)

    #store the result in the transposition table for future lookups
    transposition_table[state_id] = (depth, best_score)
    return best_score

def choose_best_move(board_state):

    #initialize the transposition table
    global transposition_table
    transposition_table = {}

    #get the legal moves
    legal_moves = engine.get_legal_moves(board_state)
    if not legal_moves:
        return None

    #immediate checkmate detection: a move that mates right now is always the best move
    for piece_status, move_delta in legal_moves:
        destination_state = engine.apply_move(board_state, piece_status, move_delta)
        if engine.is_checkmate(destination_state):
            return piece_status, move_delta

    #note: every move in legal_moves is already guaranteed not to leave our own king in
    #check (engine.get_legal_moves filters that out), so there's no separate "avoid losing
    #the king" pass needed here the way there would be without real check detection.

    #sort root moves so captures are searched first (high value captures before low)
    #this sets a strong best_score early so alpha-beta prunes later moves faster
    board = engine.get_board(board_state)
    root_scored = []
    for piece_status, move_delta in legal_moves:
        capture_value = 0.0
        from_row, from_col = piece_status[1]
        target_row = from_row + move_delta[0]
        target_col = from_col + move_delta[1]
        if 0 <= target_row < len(board) and 0 <= target_col < len(board[target_row]):
            target_piece = board[target_row][target_col]
            if target_piece.isalpha():
                capture_value = PIECE_WORTH.get(target_piece, 0)
        root_scored.append((capture_value, piece_status, move_delta))
    root_scored.sort(key=lambda item: item[0], reverse=True)
    candidate_moves = [(ps, md) for _, ps, md in root_scored]

    #find the best move using alpha-beta pruning
    best_move = None
    best_score = None
    for piece_status, move_delta in candidate_moves:
        destination_state = engine.apply_move(board_state, piece_status, move_delta)

        #evaluate_board is defined relative, so dfs_with_alpha_beta returns the value from the opponent's perspective (since destination_state flips the turn)
        #pass our running best score so the child can prune branches that cant beat it
        child_beta = None if best_score is None else -best_score
        score = -dfs_with_alpha_beta(destination_state, SEARCH_DEPTH - 1, None, child_beta)
        if score is not None:
            if best_score is None or score > best_score:
                best_score = score
                best_move = (piece_status, move_delta)

    return best_move


def choose_first_legal_move(board_state):

    legal_moves = engine.get_legal_moves(board_state)
    if not legal_moves:
        return None
    return legal_moves[0]


def choose_best_move_under_100ms(board_state):

    legal_moves = engine.get_legal_moves(board_state)
    if not legal_moves:
        return None

    #immediate checkmate detection (must simulate, but we only do it for this move list)
    for piece_status, move_delta in legal_moves:
        destination_state = engine.apply_move(board_state, piece_status, move_delta)
        if engine.is_checkmate(destination_state):
            return piece_status, move_delta

    #every legal move is already check-safe for us, so any of them is a reasonable panic move
    return legal_moves[0]


def get_piece_worth(piece_type):
    return PIECE_WORTH.get(piece_type, 0)

def choose_opening_move(board_state):

    #check if we have a hardcoded opening move for this move number
    #uses move_no as index so it plays the right move each turn (not always move 0)
    move_no = engine.get_move_no(board_state)

    if move_no not in OPENING_BOOK:
        return None

    target_piece, target_pos, target_delta = OPENING_BOOK[move_no]
    legal_moves = engine.get_legal_moves(board_state)

    for piece_status, move_delta in legal_moves:
        piece_type, pos = piece_status
        if piece_type == target_piece and pos == target_pos and move_delta == target_delta:
            return piece_status, move_delta

    return None


def choose_move(board_state):

    #time-based SEARCH_DEPTH adjustment
    #small opening move
    #fallback
    used_time_ms = engine.get_used_time_ms(board_state)
    total_time_ms = engine.get_total_time_ms(board_state)

    #reduce search depth when remaining time is low.
    remaining_ms = max(0, total_time_ms - used_time_ms)

    # opening moves
    opening = choose_opening_move(board_state)
    if opening is not None:
        return opening

    # ultra-low time
    if remaining_ms < 50:
        return choose_first_legal_move(board_state)

    # low time
    if remaining_ms < 100:
        return choose_best_move_under_100ms(board_state)

    # normal time
    global SEARCH_DEPTH
    if remaining_ms < 500:
        SEARCH_DEPTH = 1
    else:
        SEARCH_DEPTH = 2

    return choose_best_move(board_state)

def main():

    #read the input from stdin
    contents = sys.stdin.read()
    if not contents.strip():
        return

    #get the board state from the input
    board_state = engine.get_board_state(contents)
    move = choose_move(board_state)

    if move is None:
        new_board_status = board_state

    #if there is a move, apply it to the board
    else:
        piece_status, move_delta = move
        new_board_status = engine.apply_move(board_state, piece_status, move_delta)

    for row in new_board_status:
        sys.stdout.write(''.join(row) + '\n')


if __name__ == "__main__":
    main()
