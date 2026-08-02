import sys


def print_menu():
    print("=" * 50)
    print(" DRAW IN AIR")
    print("=" * 50)
    print(" 1) 2D Air Canvas   - pen, shapes, eraser, colors")
    print(" 2) 3D Air Canvas   - draw in 3D space")
    print(" q) Quit")
    print("=" * 50)


def main():
    choice = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower().lstrip("-")
        if arg == "2d":
            choice = "1"
        elif arg == "3d":
            choice = "2"

    while True:
        if choice is None:
            print_menu()
            choice = input("Select mode: ").strip().lower()

        if choice in ("1", "2d"):
            from canvas2d import AirCanvas2D
            go_3d = AirCanvas2D().run()
            choice = "2" if go_3d else None
        elif choice in ("2", "3d"):
            from canvas3d import AirCanvas3D
            go_2d = AirCanvas3D().run()
            choice = "1" if go_2d else None
        elif choice in ("q", "quit", "exit"):
            print("Goodbye!")
            break
        else:
            print("Invalid choice.\n")
            choice = None


if __name__ == "__main__":
    main()
