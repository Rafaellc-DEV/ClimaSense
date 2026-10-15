"""Ponto de entrada: `python -m climasense --version`."""

import argparse

from climasense import __version__


def main() -> None:
    parser = argparse.ArgumentParser(prog="climasense", description=__doc__)
    parser.add_argument("--version", action="version", version=f"ClimaSense {__version__}")
    parser.parse_args()
    print(f"ClimaSense {__version__}. Use --help para ver os comandos.")


if __name__ == "__main__":
    main()
