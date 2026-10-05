balance = 1000
pin = "1234"


def check_pin():
    entered_pin = input("Enter your 4-digit PIN: ")
    return entered_pin == pin


def check_balance():
    print(f"Your current balance is: ${balance}")


def deposit():
    global balance
    amount = float(input("Enter amount to deposit: $"))
    if amount <= 0:
        print("Invalid amount. Please enter a positive number.")
        return
    balance += amount
    print(f"${amount} deposited successfully.")
    print(f"New balance: ${balance}")


def withdraw():
    global balance
    amount = float(input("Enter amount to withdraw: $"))
    if amount <= 0:
        print("Invalid amount. Please enter a positive number.")
        return
    if amount > balance:
        print("Insufficient balance.")
        return
    balance -= amount
    print(f"${amount} withdrawn successfully.")
    print(f"New balance: ${balance}")


def main():
    print("=== Welcome to Python ATM ===")

    attempts = 3
    authenticated = False
    while attempts > 0:
        if check_pin():
            authenticated = True
            break
        attempts -= 1
        print(f"Incorrect PIN. Attempts remaining: {attempts}")

    if not authenticated:
        print("Too many incorrect attempts. Card blocked.")
        return

    while True:
        print("\n--- ATM Menu ---")
        print("1. Check Balance")
        print("2. Deposit")
        print("3. Withdraw")
        print("4. Exit")

        choice = input("Choose an option (1-4): ")

        if choice == "1":
            check_balance()
        elif choice == "2":
            deposit()
        elif choice == "3":
            withdraw()
        elif choice == "4":
            print("Thank you for using Python ATM. Goodbye!")
            break
        else:
            print("Invalid option. Please choose between 1-4.")


if __name__ == "__main__":
    main()
