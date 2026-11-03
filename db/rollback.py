from db.migration import run_command


# Reverse the most recently applied migration using the same migration file.
def main() -> int:
    return run_command("down")


if __name__ == "__main__":
    raise SystemExit(main())
