import sys


def main():
    for line in sys.stdin:
        print(f"PROCESSING: {line.strip()}")
    print("DONE!")


if __name__ == "__main__":
    main()
