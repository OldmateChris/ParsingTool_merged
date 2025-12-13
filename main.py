from __future__ import annotations

import sys


def main() -> None:
    """Entry point.

    - No args  -> launch GUI (recommended for most users)
    - Any args -> run CLI
    """

    # If the user provides arguments, run the CLI interface.
    if len(sys.argv) > 1:
        from ParsingTool.parsing.cli import main as cli_main

        cli_main()
        return

    # Otherwise, launch the GUI that is wired to the correct pipelines.
    from ParsingTool.main import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
