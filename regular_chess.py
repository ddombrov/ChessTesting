#!/usr/bin/env python3
import sys

# board_state layout: [turn] + [8 board rows] + [used_time_ms, total_time_ms,
# move_no, en_passant_target, castling_rights]
TRAILING_METADATA_LINES = 5

def is_piece(char):
    return char.isalpha()

def is_opponent(piece_one, piece_two):
    return (piece_one.isupper() and piece_two.islower()) or (piece_one.islower() and piece_two.isupper())

def in_bounds(row_index, col_index, board):
    return 0 <= row_index < len(board) and 0 <= col_index < len(board[row_index])

def parse_int_line(line):
    if line is None:
        return 0
    text = ''.join(line) if isinstance(line, list) else str(line)
    text = text.strip()
    return int(text) if text else 0

def parse_text_line(line, default="-"):
    if line is None:
        return default
    text = ''.join(line) if isinstance(line, list) else str(line)
    text = text.strip()
    return text if text else default

def get_board(board_state):
    return board_state[1:-TRAILING_METADATA_LINES]

def get_used_time_ms(board_state):
    return parse_int_line(board_state[-5])

def get_total_time_ms(board_state):
    return parse_int_line(board_state[-4])

def get_move_no(board_state):
    return parse_int_line(board_state[-3])

def get_en_passant_target(board_state):
    text = parse_text_line(board_state[-2])
    if text == "-":
        return None
    row_text, col_text = text.split(",")
    return (int(row_text), int(col_text))

def get_castling_rights(board_state):
    return parse_text_line(board_state[-1])

def apply_promotion(new_board):
    #Pawn on opposite end promotes to Queen.

    board_length = len(new_board)
    for row in range(board_length):
        for col in range(len(new_board[row])):
            cell = new_board[row][col]
            if cell == 'P' and row == board_length - 1:
                new_board[row][col] = 'Q'
            elif cell == 'p' and row == 0:
                new_board[row][col] = 'q'
    return new_board

def get_board_state(contents):

    #split contents into lines
    lines = contents.splitlines()

    #initialize board as list of lists
    board = []

    #go through lines and add to board
    for line in lines:
        board.append(list(line))

    return board

def get_pieces_of_current_player(board_state):

    #read whose turn it is from board
    turn = board_state[0][0]

    #set pieces to check for based on whose turn it is
    if turn == "W":
        pieces=["P", "R", "N", "B", "Q", "K"]
    else:
        pieces=["p", "r", "n", "b", "q", "k"]

    return pieces

def get_pieces_on_board(potential_pieces_list, board):

    pieces_statuses = []

    #go through rows of board
    for row in range(len(board)):

        #go through columns of board
        for col in range(len(board[row])):

            square=board[row][col]

            #if a potential piece is on the board, add piece and location to list of pieces
            if square in potential_pieces_list:

                #get location of piece and add to list of pieces
                location = (row, col)
                pieces_statuses.append((square, location))

    return pieces_statuses

def find_piece(board, piece_char):
    for row_index, row in enumerate(board):
        for col_index, cell in enumerate(row):
            if cell == piece_char:
                return (row_index, col_index)
    return None

def is_square_attacked(board, target_row, target_col, by_white):

    board_length = len(board)

    def on_board(row, col):
        return 0 <= row < board_length and 0 <= col < len(board[row])

    #pawns: attacked from the two squares diagonally behind the target, relative to the attacker's direction
    pawn_char = 'P' if by_white else 'p'
    pawn_dir = 1 if by_white else -1
    for source_col in (target_col - 1, target_col + 1):
        source_row = target_row - pawn_dir
        if on_board(source_row, source_col) and board[source_row][source_col] == pawn_char:
            return True

    knight_char = 'N' if by_white else 'n'
    for delta_row, delta_col in [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]:
        row, col = target_row + delta_row, target_col + delta_col
        if on_board(row, col) and board[row][col] == knight_char:
            return True

    king_char = 'K' if by_white else 'k'
    for delta_row in (-1, 0, 1):
        for delta_col in (-1, 0, 1):
            if delta_row == 0 and delta_col == 0:
                continue
            row, col = target_row + delta_row, target_col + delta_col
            if on_board(row, col) and board[row][col] == king_char:
                return True

    rook_like = ('R', 'Q') if by_white else ('r', 'q')
    for delta_row, delta_col in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        row, col = target_row + delta_row, target_col + delta_col
        while on_board(row, col):
            cell = board[row][col]
            if cell.isalpha():
                if cell in rook_like:
                    return True
                break
            row += delta_row
            col += delta_col

    bishop_like = ('B', 'Q') if by_white else ('b', 'q')
    for delta_row, delta_col in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
        row, col = target_row + delta_row, target_col + delta_col
        while on_board(row, col):
            cell = board[row][col]
            if cell.isalpha():
                if cell in bishop_like:
                    return True
                break
            row += delta_row
            col += delta_col

    return False

def is_in_check(board, white):
    king_char = 'K' if white else 'k'
    king_position = find_piece(board, king_char)
    if king_position is None:
        return False
    return is_square_attacked(board, king_position[0], king_position[1], by_white=not white)

def get_castling_moves(piece_status, board, castling_rights):

    piece_char, (row, col) = piece_status
    if piece_char not in ("K", "k") or castling_rights in (None, "-"):
        return []

    is_white = piece_char == "K"
    board_length = len(board)
    home_row = 0 if is_white else board_length - 1
    if row != home_row or col != 4:
        return []

    #can't castle out of check
    if is_in_check(board, is_white):
        return []

    rook_char = "R" if is_white else "r"
    king_flag = "K" if is_white else "k"
    queen_flag = "Q" if is_white else "q"
    opponent_is_white = not is_white

    moves = []

    #kingside: rook still on its home square, squares between are empty, king doesn't pass through or land on an attacked square
    if king_flag in castling_rights and board[home_row][7] == rook_char:
        if board[home_row][5] == '.' and board[home_row][6] == '.':
            if not is_square_attacked(board, home_row, 5, opponent_is_white) and \
               not is_square_attacked(board, home_row, 6, opponent_is_white):
                moves.append((0, 2))

    #queenside
    if queen_flag in castling_rights and board[home_row][0] == rook_char:
        if board[home_row][1] == '.' and board[home_row][2] == '.' and board[home_row][3] == '.':
            if not is_square_attacked(board, home_row, 3, opponent_is_white) and \
               not is_square_attacked(board, home_row, 2, opponent_is_white):
                moves.append((0, -2))

    return moves

def get_all_moves(current_pieces_statuses, board, castling_rights="-"):

    all_moves = []

    #go through pieces
    for piece_type, location in current_pieces_statuses:

        #get all moves for piece and add to list of all moves
        piece_status = (piece_type, location)
        potential_moves_for_this_piece = get_potential_moves_of_a_piece(piece_type, board)

        for move in potential_moves_for_this_piece:
            all_moves.append((piece_status, move))

        if piece_type in ("K", "k"):
            for move in get_castling_moves(piece_status, board, castling_rights):
                all_moves.append((piece_status, move))

    return all_moves

def get_potential_moves_of_a_piece(piece_type, board):

    #define potential moves for each piece type
    board_length = len(board)

    #pawn
    if piece_type == "P":
        return [(1, 0), (2, 0), (1, 1), (1, -1)]
    elif piece_type == "p":
        return [(-1, 0), (-2, 0), (-1, 1), (-1, -1)]

    #rook
    elif piece_type in ["R", "r"]:
        return [(offset, 0) for offset in range(-board_length, board_length) if offset != 0] + [(0, offset) for offset in range(-board_length, board_length) if offset != 0]

    #knight
    elif piece_type in ["N", "n"]:
        return [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]

    #bishop
    elif piece_type in ["B", "b"]:
        return [(offset, offset) for offset in range(-board_length, board_length) if offset != 0] + [(offset, -offset) for offset in range(-board_length, board_length) if offset != 0]

    #queen
    elif piece_type in ["Q", "q"]:
        return [(offset, 0) for offset in range(-board_length, board_length) if offset != 0] + [(0, offset) for offset in range(-board_length, board_length) if offset != 0] + [(offset, offset) for offset in range(-board_length, board_length) if offset != 0] + [(offset, -offset) for offset in range(-board_length, board_length) if offset != 0]

    #king
    elif piece_type in ["K", "k"]:
        return [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]

def get_moves_within_bounds(moves, board):

    within_bounds_moves = []
    for piece_status, move_delta in moves:

        piece_location = piece_status[1]
        new_location = (piece_location[0] + move_delta[0], piece_location[1] + move_delta[1])

        if in_bounds(new_location[0], new_location[1], board):
            within_bounds_moves.append((piece_status, move_delta))

    return within_bounds_moves

def get_possible_moves_based_on_rules(valid_moves_of_a_piece, board, en_passant_target=None):

    possible_moves_based_on_rules=[]

    #go through valid moves of piece
    for piece_status, move in valid_moves_of_a_piece:

        #check if move is allowed based on the rules
        if is_move_allowed_based_on_rules(piece_status, move, board, en_passant_target):
            possible_moves_based_on_rules.append((piece_status, move))

    return possible_moves_based_on_rules

def is_move_allowed_based_on_rules(piece_status, move, board, en_passant_target=None):

    if move == (0, 0):
        return False

    #pawn
    if piece_status[0] in ["P", "p"]:

        #can move up 1 if no other piece is in front of it
        if move in [(1, 0), (-1, 0)]:
            target_square = board[piece_status[1][0] + move[0]][piece_status[1][1]]
            if not is_piece(target_square):
                return True

        #can move up 2 if in starting row and both squares in front are empty
        elif move in [(2, 0), (-2, 0)]:
            direction = 1 if piece_status[0] == "P" else -1
            in_starting_row = (piece_status[0] == "P" and piece_status[1][0] == 1) or (piece_status[0] == "p" and piece_status[1][0] == len(board) - 2)
            square_one_away = board[piece_status[1][0] + direction][piece_status[1][1]]
            square_two_away = board[piece_status[1][0] + 2 * direction][piece_status[1][1]]
            if in_starting_row and not square_one_away.isalpha() and not square_two_away.isalpha():
                return True

        #can capture diagonally if there is an opponent's piece in that location, or if it's the en passant target
        elif move in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            new_location = (piece_status[1][0] + move[0], piece_status[1][1] + move[1])
            target_piece = board[new_location[0]][new_location[1]]
            if is_piece(target_piece) and is_opponent(target_piece, piece_status[0]):
                return True
            if en_passant_target is not None and new_location == en_passant_target:
                return True

    #rook
    elif piece_status[0] in ["R", "r"]:

        #vertical movement
        vertical_move = 0 if move[0] == 0 else (1 if move[0] > 0 else -1)

        #horizontal movement
        horizontal_move = 0 if move[1] == 0 else (1 if move[1] > 0 else -1)

        current_location = piece_status[1]
        destination = (piece_status[1][0] + move[0], piece_status[1][1] + move[1])

        while True:

            #move one step towards destination
            current_location = (current_location[0] + vertical_move, current_location[1] + horizontal_move)

            #if we have reached the destination, check if move is valid
            if current_location == destination:

                destination_piece = board[destination[0]][destination[1]]

                #if destination is empty, move is valid
                if not is_piece(destination_piece):
                    return True

                #if destination has opponent's piece, move is valid
                return is_opponent(destination_piece, piece_status[0])

            #don't let rook jump over pieces
            target_square = board[current_location[0]][current_location[1]]
            if target_square.isalpha():
                return False

    #knight
    elif piece_status[0] in ["N", "n"]:

        destination = (piece_status[1][0] + move[0], piece_status[1][1] + move[1])
        destination_piece = board[destination[0]][destination[1]]

        #knight can jump over pieces, just need to check if destination square is empty or has opponent's piece
        if not is_piece(destination_piece) or is_opponent(destination_piece, piece_status[0]):
            return True

    #bishop
    elif piece_status[0] in ["B", "b"]:

        vertical_move = 1 if move[0] > 0 else -1
        horizontal_move = 1 if move[1] > 0 else -1

        current_location = piece_status[1]
        destination = (piece_status[1][0] + move[0], piece_status[1][1] + move[1])

        while True:

            #move one step towards destination
            current_location = (current_location[0] + vertical_move, current_location[1] + horizontal_move)

            #if we have reached the destination, check if move is valid
            if current_location == destination:

                destination_piece = board[destination[0]][destination[1]]

                #if destination is empty, move is valid
                if not is_piece(destination_piece):
                    return True

                #if destination has opponent's piece, move is valid
                return is_opponent(destination_piece, piece_status[0])

            #don't let bishop jump over pieces
            target_square = board[current_location[0]][current_location[1]]
            if target_square.isalpha():
                return False

    #queen
    elif piece_status[0] in ["Q", "q"]:

        vertical_move = 0 if move[0] == 0 else (1 if move[0] > 0 else -1)
        horizontal_move = 0 if move[1] == 0 else (1 if move[1] > 0 else -1)

        current_location = piece_status[1]
        destination = (piece_status[1][0] + move[0], piece_status[1][1] + move[1])

        while True:

            #move one step towards destination
            current_location = (current_location[0] + vertical_move, current_location[1] + horizontal_move)

            #if we have reached the destination, check if move is valid
            if current_location == destination:

                destination_piece = board[destination[0]][destination[1]]

                #if destination is empty, move is valid
                if not is_piece(destination_piece):
                    return True

                #if destination has opponent's piece, move is valid
                return is_opponent(destination_piece, piece_status[0])

            #don't let queen jump over pieces
            target_square = board[current_location[0]][current_location[1]]
            if target_square.isalpha():
                return False

    #king
    elif piece_status[0] in ["K", "k"]:

        #castling: full legality (rook present, empty squares, not through/out of check) is already checked in get_castling_moves
        if move in [(0, 2), (0, -2)]:
            return True

        destination = (piece_status[1][0] + move[0], piece_status[1][1] + move[1])
        destination_piece = board[destination[0]][destination[1]]

        #alr found which moves possible and within bounds, just need to check if destination square is empty or has opponent's piece
        if not is_piece(destination_piece) or is_opponent(destination_piece, piece_status[0]):
            return True

    return False

def filter_legal_moves(moves, board, white_to_move):

    #a move is only legal if it doesn't leave the mover's own king in check
    legal_moves = []
    for piece_status, move in moves:
        simulated_board = perform_move(piece_status, move, board)
        if not is_in_check(simulated_board, white_to_move):
            legal_moves.append((piece_status, move))
    return legal_moves

def get_legal_moves(board_state):

    board = get_board(board_state)
    white_to_move = board_state[0][0] == 'W'
    castling_rights = get_castling_rights(board_state)
    en_passant_target = get_en_passant_target(board_state)

    potential_pieces_list = get_pieces_of_current_player(board_state)
    current_pieces_statuses = get_pieces_on_board(potential_pieces_list, board)
    all_moves = get_all_moves(current_pieces_statuses, board, castling_rights)
    within_bounds_moves = get_moves_within_bounds(all_moves, board)
    pseudo_legal_moves = get_possible_moves_based_on_rules(within_bounds_moves, board, en_passant_target)
    return filter_legal_moves(pseudo_legal_moves, board, white_to_move)

def is_checkmate(board_state):
    board = get_board(board_state)
    white_to_move = board_state[0][0] == 'W'
    return not get_legal_moves(board_state) and is_in_check(board, white_to_move)

def is_stalemate(board_state):
    board = get_board(board_state)
    white_to_move = board_state[0][0] == 'W'
    return not get_legal_moves(board_state) and not is_in_check(board, white_to_move)

def perform_move(piece_status, move, board):

    #create a copy of the board to modify
    new_board = [row.copy() for row in board]

    #get piece type and location
    piece_type = piece_status[0]
    piece_location = piece_status[1]

    #calculate new location of piece after move
    new_location = (piece_location[0] + move[0], piece_location[1] + move[1])

    #en passant: a pawn capturing diagonally onto an empty square removes the pawn beside it,
    #not on the destination square. Only reachable here for moves already vetted as en passant
    #by is_move_allowed_based_on_rules, so any diagonal-pawn-move-to-empty-square qualifies.
    if piece_type in ("P", "p") and move[1] != 0 and not is_piece(board[new_location[0]][new_location[1]]):
        new_board[piece_location[0]][new_location[1]] = '.'

    #move piece on new board (normal move); promotion (pawn→Queen) is done in apply_promotion
    new_board[new_location[0]][new_location[1]] = piece_type
    new_board[piece_location[0]][piece_location[1]] = '.'

    #castling: king moves two squares, the rook jumps to the other side of it
    if piece_type in ("K", "k") and move[1] in (2, -2):
        row = piece_location[0]
        if move[1] == 2:
            rook_char = new_board[row][7]
            new_board[row][7] = '.'
            new_board[row][5] = rook_char
        else:
            rook_char = new_board[row][0]
            new_board[row][0] = '.'
            new_board[row][3] = rook_char

    new_board = apply_promotion(new_board)
    return new_board

def update_castling_rights(rights, board_length, piece_char, from_square, to_square):

    if rights == "-":
        return "-"

    rights_set = set(rights)
    white_home_row = 0
    black_home_row = board_length - 1

    #king moved: lose both rights for that color
    if piece_char == 'K':
        rights_set -= {'K', 'Q'}
    elif piece_char == 'k':
        rights_set -= {'k', 'q'}

    #rook moved from its home square: lose that side's right
    if piece_char == 'R' and from_square == (white_home_row, 0):
        rights_set.discard('Q')
    elif piece_char == 'R' and from_square == (white_home_row, 7):
        rights_set.discard('K')
    elif piece_char == 'r' and from_square == (black_home_row, 0):
        rights_set.discard('q')
    elif piece_char == 'r' and from_square == (black_home_row, 7):
        rights_set.discard('k')

    #a rook was captured on its home square: lose that right too
    if to_square == (white_home_row, 0):
        rights_set.discard('Q')
    elif to_square == (white_home_row, 7):
        rights_set.discard('K')
    elif to_square == (black_home_row, 0):
        rights_set.discard('q')
    elif to_square == (black_home_row, 7):
        rights_set.discard('k')

    return ''.join(sorted(rights_set)) if rights_set else "-"

def apply_move(board_state, piece_status, move):

    #apply a legal move to a full board_state, returning the resulting board_state
    #with the turn, move counter, en passant target, and castling rights all updated
    board = get_board(board_state)
    piece_char, (from_row, from_col) = piece_status
    delta_row, delta_col = move
    to_row, to_col = from_row + delta_row, from_col + delta_col

    new_board = perform_move(piece_status, move, board)

    next_turn = [['B']] if piece_char.isupper() else [['W']]

    #en passant is only available for the very next move, and only after a pawn double-step
    if piece_char in ('P', 'p') and abs(delta_row) == 2:
        en_passant_target = f"{(from_row + to_row) // 2},{to_col}"
    else:
        en_passant_target = "-"

    castling_rights = update_castling_rights(
        get_castling_rights(board_state), len(board), piece_char, (from_row, from_col), (to_row, to_col)
    )

    new_move_no = get_move_no(board_state) + 1

    return (
        next_turn
        + new_board
        + [list(str(get_used_time_ms(board_state)))]
        + [list(str(get_total_time_ms(board_state)))]
        + [list(str(new_move_no))]
        + [list(en_passant_target)]
        + [list(castling_rights)]
    )

def output_boards(board_state, legal_moves):

    #output as board.000, board.001, etc.
    for move_index, (piece_status, move) in enumerate(legal_moves):
        name = f"board.{move_index:03d}"
        new_board_status = apply_move(board_state, piece_status, move)
        output_board(name, new_board_status)

def output_board(name, board_status):

    filename = name

    with open(filename, 'w') as file_handle:
        for row in board_status:
            file_handle.write(''.join(row) + '\n')

if __name__ == "__main__":

    #read filename from standard input
    contents = sys.stdin.read()

    #get a 2D list representing the board's state
    board_state = get_board_state(contents)

    #get every fully legal move for the side to move (check-safe, includes castling and en passant)
    legal_moves = get_legal_moves(board_state)

    #output all possible boards resulting from legal moves
    output_boards(board_state, legal_moves)
