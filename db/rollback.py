from db.migration import runCommand


# Reverses the most recently applied migration using the same migration file.
def main() -> int:
    return runCommand("down")


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["main"]
