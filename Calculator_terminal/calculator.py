def calculate(num1, operator, num2):
    if operator == "+":
        return num1 + num2
    elif operator == "-":
        return num1 - num2
    elif operator == "*":
        return num1 * num2
    elif operator == "/":
        if num2 == 0:
            return "Error: Division by zero"
        return num1 / num2
    else:
        return "Error: Invalid operator"


def main():
    print("=== Simple Terminal Calculator ===")
    print("Operators: + - * /")
    print("Type 'q' to quit\n")

    while True:
        first = input("Enter first number (or 'q' to quit): ")
        if first.lower() == "q":
            break

        operator = input("Enter operator (+, -, *, /): ")
        if operator.lower() == "q":
            break

        second = input("Enter second number: ")
        if second.lower() == "q":
            break

        try:
            num1 = float(first)
            num2 = float(second)
        except ValueError:
            print("Please enter valid numbers.\n")
            continue

        result = calculate(num1, operator, num2)
        print(f"Result: {result}\n")

    print("Goodbye!")


if __name__ == "__main__":
    main()
