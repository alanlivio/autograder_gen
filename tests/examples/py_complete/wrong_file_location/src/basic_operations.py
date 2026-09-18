#!/usr/bin/env python3
"""
Basic Operations Module
Handles simple input/output operations for testing
"""


def main():
    """Main function that processes input and produces output"""
    try:
        # Read input
        text = input().strip()
        number = int(input().strip())
        float_val = float(input().strip())

        # Process and output
        print(f"{text}")
        print(f"Number: {number}")
        print(f"Float: {float_val}")

    except (ValueError, EOFError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
