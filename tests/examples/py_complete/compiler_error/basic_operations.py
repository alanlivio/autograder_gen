# basic_operations.py - Contains syntax errors

import sys


def main():
    # Syntax error: missing closing parenthesis
    for line in sys.stdin:
        if "Hello" in line:
            print(f"{line.strip()}")
        elif line.strip().replace(".", "").replace("-", "").isdigit():  # Missing )
            num = float(line.strip())
            if num.is_integer():
                print(f"Number: {int(num)}")
            else:
                print(f"Float: {num}")


if __name__ == "__main__":
    main()
