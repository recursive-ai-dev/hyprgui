import sys

from .ui import HyprGuiApplication


def main() -> int:
    app = HyprGuiApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
