import sys

MODE_ARGS = {"1": "2d", "2d": "2d", "2": "3d", "3d": "3d"}


def print_menu():
    print("=" * 50)
    print(" DRAW IN AIR")
    print("=" * 50)
    print(" 1) 2D Air Canvas   - pen, shapes, eraser, colors")
    print(" 2) 3D Air Canvas   - draw in 3D space")
    print(" q) Quit")
    print("=" * 50)


def run_mode(mode):
    """Runs one mode and returns the mode to open next (None goes back to the menu)."""
    if mode == "2d":
        from canvas2d import AirCanvas2D
        return AirCanvas2D().run()
    if mode == "3d":
        from canvas3d import AirCanvas3D
        return "2d" if AirCanvas3D().run() else None
    return None


def main():
    mode = None
    if len(sys.argv) > 1:
        mode = MODE_ARGS.get(sys.argv[1].lower().lstrip("-"))

    while True:
        if mode is None:
            print_menu()
            try:
                choice = input("Select mode: ").strip().lower()
            except EOFError:
                choice = "q"
            if choice in ("q", "quit", "exit"):
                print("Goodbye!")
                break
            mode = MODE_ARGS.get(choice)
            if mode is None:
                print("Invalid choice.\n")
                continue

        mode = run_mode(mode)


if __name__ == "__main__":
    main()
