# basic_operations.py - Wrong output format

import sys


def main():
    for line in sys.stdin:
        if "Hello" in line or "Test" in line:
            print(f"PROCESSING: {line.strip()}")  # Wrong: should be "Processing:"
        elif line.strip().replace(".", "").replace("-", "").isdigit():
            num = float(line.strip())
            if num.is_integer():
                print(f"NUMBER: {int(num)}")  # Wrong: should be "Number:"
            else:
                print(f"FLOAT: {num}")  # Wrong: should be "Float:"
    print("DONE!")  # Wrong: should be "Done!"


if __name__ == "__main__":
    main()
