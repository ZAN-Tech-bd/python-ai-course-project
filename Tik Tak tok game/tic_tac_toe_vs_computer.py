import os
import random


def print_board(board):
    os.system("cls" if os.name == "nt" else "clear")
    print()
    for row in range(3):
        cells = [board[row * 3 + col] for col in range(3)]
        print(f"  {cells[0]} | {cells[1]} | {cells[2]} ")
        if row < 2:
            print(" ---+---+---")
    print()


def check_winner(board, player):
    win_combos = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # columns
        (0, 4, 8), (2, 4, 6),             # diagonals
    ]
    return any(board[a] == board[b] == board[c] == player for a, b, c in win_combos)


def is_full(board):
    return all(cell != " " for cell in board)


def get_move(board):
    while True:
        raw = input("Your move, enter a position (1-9): ").strip()
        if not raw.isdigit():
            print("Please enter a number between 1 and 9.")
            continue
        pos = int(raw)
        if pos < 1 or pos > 9:
            print("Please enter a number between 1 and 9.")
            continue
        if board[pos - 1] != " ":
            print("That spot is already taken. Try again.")
            continue
        return pos - 1


def get_computer_move(board):
    empty = [i for i, cell in enumerate(board) if cell == " "]
    return random.choice(empty)


def play_round():
    board = [" "] * 9
    human, computer = "X", "O"

    print_board(board)
    while True:
        move = get_move(board)
        board[move] = human
        print_board(board)

        if check_winner(board, human):
            print("You win!")
            return
        if is_full(board):
            print("It's a draw!")
            return

        move = get_computer_move(board)
        board[move] = computer
        print(f"Computer chose position {move + 1}.")
        print_board(board)

        if check_winner(board, computer):
            print("Computer wins!")
            return
        if is_full(board):
            print("It's a draw!")
            return


def main():
    print("Welcome to Tic Tac Toe - You vs Computer!")
    print("You are X, Computer is O.")
    print("Positions are numbered 1-9 like this:")
    print(" 1 | 2 | 3 ")
    print(" 4 | 5 | 6 ")
    print(" 7 | 8 | 9 ")

    while True:
        play_round()
        again = input("Play again? (y/n): ").strip().lower()
        if again != "y":
            print("Thanks for playing!")
            break


if __name__ == "__main__":
    main()
