#!/usr/bin/env python3
import argparse
import tkinter as tk
from tkinter import messagebox

import regular_chess as engine
import chess_ai as ai_player

BOARD_ROWS = 8
BOARD_COLS = 8

AI_THINK_DELAY_MS = 150

PIECE_TEXT = {
    'K': '♔', 'k': '♚',
    'Q': '♕', 'q': '♛',
    'R': '♖', 'r': '♜',
    'B': '♗', 'b': '♝',
    'N': '♘', 'n': '♞',
    'P': '♙', 'p': '♟',
    '.': '',
}


class GuiGame:
    def __init__(self, root, board_state, vs_ai=False, human_side='W'):
        self.root = root
        self.vs_ai = vs_ai
        self.human_side = human_side
        self.ai_side = 'B' if human_side == 'W' else 'W'

        self.initial_board_state = [row[:] for row in board_state]
        self.board_state = board_state
        self.board = engine.get_board(self.board_state)
        self.buttons = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]

        self.selected_piece_status = None
        self.legal_moves_by_piece = {}
        self.highlighted_targets = set()
        self.game_over_targets = set()
        self.target_to_move = {}
        self.target_to_consequences = {}
        self.preview_friendly_losses = set()
        self.preview_enemy_losses = set()

        self.history = []
        self.move_log = []

        self.info_label = tk.Label(self.root, text="", font=("Consolas", 12))
        self.info_label.grid(row=0, column=0, columnspan=BOARD_COLS)

        self._create_board_widgets()

        self.play_again_button = tk.Button(self.root, text="Play again", command=self.reset_game)
        self.play_again_button.grid(row=BOARD_ROWS + 1, column=0, columnspan=BOARD_COLS, pady=3)

        self.undo_button = tk.Button(self.root, text="Undo", command=self.undo_move)
        self.undo_button.grid(row=BOARD_ROWS + 2, column=0, columnspan=BOARD_COLS, pady=(0, 5))

        self.log_frame = tk.Frame(self.root)
        self.log_frame.grid(row=BOARD_ROWS + 3, column=0, columnspan=BOARD_COLS, sticky="nsew", pady=(0, 4))

        self.copy_log_button = tk.Button(self.log_frame, text="Copy log", command=self.copy_log)
        self.copy_log_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.clear_log_button = tk.Button(self.log_frame, text="Clear log", command=self.clear_log)
        self.clear_log_button.grid(row=0, column=1, sticky="w")

        self.log_text = tk.Text(self.log_frame, height=6, width=40, font=("Consolas", 10), wrap="none")
        self.log_text.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(4, 0))
        self.log_scrollbar = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.log_scrollbar.grid(row=1, column=2, sticky="ns", pady=(4, 0))
        self.log_text.configure(yscrollcommand=self.log_scrollbar.set, state="disabled")

        self._refresh_legal_moves()
        self._refresh_board()

    def _create_board_widgets(self):
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                btn = tk.Button(
                    self.root, width=4, height=1, font=("Segoe UI Emoji", 16),
                    relief="solid", bd=1, padx=0, pady=0, highlightthickness=1,
                    command=lambda r=row, c=col: self.on_square_clicked(r, c),
                )
                btn.bind("<Enter>", lambda _e, r=row, c=col: self.on_square_hover(r, c))
                btn.bind("<Leave>", lambda _e, r=row, c=col: self.on_square_hover_leave(r, c))
                btn.grid(row=row + 1, column=col)
                self.buttons[row][col] = btn

    def append_log(self, line):
        self.move_log.append(line)
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def copy_log(self):
        text = "\n".join(self.move_log) if self.move_log else "(no moves yet)"
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception as error:
            messagebox.showerror("Error", f"Failed to copy log:\n{error}")

    def clear_log(self):
        self.move_log.clear()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _push_history(self):
        board_copy = [row[:] for row in self.board_state]
        log_copy = list(self.move_log)
        self.history.append((board_copy, log_copy))

    def undo_move(self):
        if not self.history:
            return
        # In vs-AI mode, undo a full turn (the AI's reply plus your move) if possible.
        if self.vs_ai and len(self.history) >= 2:
            self.history.pop()
        board_state, move_log = self.history.pop()

        self.board_state = [row[:] for row in board_state]
        self.board = engine.get_board(self.board_state)
        self._clear_selection()
        self.move_log = list(move_log)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for line in self.move_log:
            self.log_text.insert("end", line + "\n")
        self.log_text.configure(state="disabled")

        self._refresh_legal_moves()
        self._refresh_board(trigger_ai=False)

    def reset_game(self):
        self.board_state = [row[:] for row in self.initial_board_state]
        self.board = engine.get_board(self.board_state)
        self._clear_selection()
        self.history.clear()
        self.clear_log()
        self._refresh_legal_moves()
        self._refresh_board()

    def _clear_selection(self):
        self.selected_piece_status = None
        self.highlighted_targets.clear()
        self.game_over_targets.clear()
        self.target_to_move.clear()
        self.target_to_consequences.clear()
        self.preview_friendly_losses.clear()
        self.preview_enemy_losses.clear()

    def _refresh_legal_moves(self):
        legal_moves = engine.get_legal_moves(self.board_state)
        piece_to_moves = {}
        for piece_status, move_delta in legal_moves:
            piece_to_moves.setdefault(piece_status, []).append(move_delta)
        self.legal_moves_by_piece = piece_to_moves

    def _compute_move_consequences(self, piece_status, move_delta):
        turn_char = self.board_state[0][0]
        friendly_is_upper = (turn_char == "W")

        before_positions = {}
        for row_index, row in enumerate(self.board):
            for col_index, cell in enumerate(row):
                if cell.isalpha():
                    before_positions.setdefault(cell, []).append((row_index, col_index))

        simulated_board = engine.perform_move(piece_status, move_delta, self.board)
        after_positions = {}
        for row_index, row in enumerate(simulated_board):
            for col_index, cell in enumerate(row):
                if cell.isalpha():
                    after_positions.setdefault(cell, []).append((row_index, col_index))

        _, (from_row, from_col) = piece_status
        friendly_losses, enemy_losses = set(), set()
        for piece_char, before_list in before_positions.items():
            after_list = after_positions.get(piece_char, [])
            if len(after_list) >= len(before_list):
                continue
            after_set = set(after_list)
            disappeared = [pos for pos in before_list if pos not in after_set and pos != (from_row, from_col)]
            for pos in disappeared[:len(before_list) - len(after_list)]:
                is_friendly = piece_char.isupper() if friendly_is_upper else piece_char.islower()
                (friendly_losses if is_friendly else enemy_losses).add(pos)
        return friendly_losses, enemy_losses

    def _refresh_board(self, trigger_ai=True):
        turn_char = self.board_state[0][0]

        if not self.legal_moves_by_piece:
            if engine.is_in_check(self.board, turn_char == 'W'):
                winner = "Black" if turn_char == 'W' else "White"
                status_text = f"Checkmate! {winner} wins."
            else:
                status_text = "Stalemate. Draw."
        else:
            status_text = f"Turn: {'White' if turn_char == 'W' else 'Black'}"
        self.info_label.config(text=status_text)

        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                char = self.board[row][col]
                display = PIECE_TEXT.get(char, char)
                btn = self.buttons[row][col]
                btn.config(text=display)

                is_dark_square = (row + col) % 2 == 1
                base_bg = "#b58863" if is_dark_square else "#f0d9b5"
                base_fg = "black"
                if char.isalpha():
                    base_bg = "#ffffff" if char.isupper() else "#000000"
                    base_fg = "black" if char.isupper() else "white"

                if self.selected_piece_status is not None:
                    _, (sel_row, sel_col) = self.selected_piece_status
                    if row == sel_row and col == sel_col:
                        base_bg, base_fg = "#ffeb3b", "black"
                    elif (row, col) in self.preview_friendly_losses:
                        base_bg, base_fg = "#9c27b0", "white"
                    elif (row, col) in self.preview_enemy_losses:
                        base_bg, base_fg = "#1b5e20", "white"
                    elif (row, col) in self.highlighted_targets:
                        if (row, col) in self.game_over_targets:
                            base_bg, base_fg = "#e57373", "black"
                        else:
                            base_bg, base_fg = "#81c784", "black"

                btn.config(bg=base_bg, fg=base_fg, activebackground=base_bg, activeforeground=base_fg)

        if trigger_ai and self.vs_ai and self.legal_moves_by_piece and turn_char == self.ai_side:
            self.root.after(AI_THINK_DELAY_MS, self._make_ai_move)

    def _log_move(self, mover_side, piece_status, move_delta, to_square):
        piece_char, (from_row, from_col) = piece_status
        side_name = "White" if mover_side == "W" else "Black"
        piece_display = PIECE_TEXT.get(piece_char, piece_char)
        to_row, to_col = to_square
        self.append_log(f"{side_name} moved {piece_display} from ({from_row}, {from_col}) to ({to_row}, {to_col})")

    def on_square_clicked(self, row, col):
        if not self.legal_moves_by_piece:
            return  # game already over
        if self.vs_ai and self.board_state[0][0] != self.human_side:
            return  # not your turn

        if self.selected_piece_status is not None and (row, col) in self.highlighted_targets:
            move_delta = self.target_to_move.get((row, col))
            if move_delta is None:
                return
            self._push_history()
            mover_side = self.board_state[0][0]
            piece_status = self.selected_piece_status
            self.board_state = engine.apply_move(self.board_state, piece_status, move_delta)
            self.board = engine.get_board(self.board_state)
            self._log_move(mover_side, piece_status, move_delta, (row, col))
            self._clear_selection()
            self._refresh_legal_moves()
            self._refresh_board()
            return

        piece_char = self.board[row][col]
        if not piece_char.isalpha():
            self._clear_selection()
            self._refresh_board(trigger_ai=False)
            return

        turn_char = self.board_state[0][0]
        if (turn_char == 'W' and not piece_char.isupper()) or (turn_char == 'B' and not piece_char.islower()):
            return

        piece_status = (piece_char, (row, col))
        if piece_status not in self.legal_moves_by_piece:
            self._clear_selection()
            self._refresh_board(trigger_ai=False)
            return

        self._clear_selection()
        self.selected_piece_status = piece_status

        for move_delta in self.legal_moves_by_piece[piece_status]:
            delta_row, delta_col = move_delta
            target_row, target_col = row + delta_row, col + delta_col
            if 0 <= target_row < BOARD_ROWS and 0 <= target_col < BOARD_COLS:
                self.highlighted_targets.add((target_row, target_col))
                self.target_to_move[(target_row, target_col)] = move_delta

                friendly_losses, enemy_losses = self._compute_move_consequences(piece_status, move_delta)
                self.target_to_consequences[(target_row, target_col)] = (friendly_losses, enemy_losses)

                destination_state = engine.apply_move(self.board_state, piece_status, move_delta)
                if engine.is_checkmate(destination_state):
                    self.game_over_targets.add((target_row, target_col))

        self._refresh_board(trigger_ai=False)

    def on_square_hover(self, row, col):
        if self.selected_piece_status is None or (row, col) not in self.highlighted_targets:
            return
        friendly_losses, enemy_losses = self.target_to_consequences.get((row, col), (set(), set()))
        self.preview_friendly_losses = set(friendly_losses)
        self.preview_enemy_losses = set(enemy_losses)
        self._refresh_board(trigger_ai=False)

    def on_square_hover_leave(self, row, col):
        if not self.preview_friendly_losses and not self.preview_enemy_losses:
            return
        self.preview_friendly_losses.clear()
        self.preview_enemy_losses.clear()
        self._refresh_board(trigger_ai=False)

    def _make_ai_move(self):
        if self.board_state[0][0] != self.ai_side:
            return
        if not self.legal_moves_by_piece:
            return  # state changed (e.g. undo) since the AI move was scheduled

        move = ai_player.choose_move(self.board_state)
        piece_status, move_delta = move
        mover_side = self.board_state[0][0]
        self._push_history()
        self.board_state = engine.apply_move(self.board_state, piece_status, move_delta)
        self.board = engine.get_board(self.board_state)

        _, (from_row, from_col) = piece_status
        delta_row, delta_col = move_delta
        to_square = (from_row + delta_row, from_col + delta_col)
        self._log_move(mover_side, piece_status, move_delta, to_square)

        self._clear_selection()
        self._refresh_legal_moves()
        self._refresh_board()


def load_board_from_file(path):
    with open(path, "r") as board_file:
        contents = board_file.read()
    return engine.get_board_state(contents)


def parse_args():
    parser = argparse.ArgumentParser(description="Play regular chess with a GUI.")
    parser.add_argument("board", nargs="?", default="starting_board.txt",
                         help="board file to start from (default: starting_board.txt)")
    parser.add_argument("--mode", choices=["1v1", "ai"], default="ai",
                         help="'1v1' for local two-player, 'ai' to play chess_ai.py (default: ai)")
    parser.add_argument("--side", choices=["W", "B"], default="W",
                         help="which side you play in ai mode (default: W)")
    return parser.parse_args()


def main():
    args = parse_args()
    board_state = load_board_from_file(args.board)

    root = tk.Tk()
    root.title("Regular Chess - " + ("vs AI" if args.mode == "ai" else "1v1"))
    GuiGame(root, board_state, vs_ai=(args.mode == "ai"), human_side=args.side)
    root.mainloop()


if __name__ == "__main__":
    main()
