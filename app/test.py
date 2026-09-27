"""Scratch/debug helpers for exploring the Minitab COM object.

Nothing here runs on import. Call the functions manually when debugging.
"""

import win32com.client  # pyright: ignore[reportMissingImports]


def dump_minitab_commands():
    """Print the commands and outputs of the active Minitab project."""
    mtb = win32com.client.Dispatch("Mtb.Application")
    project = mtb.ActiveProject
    print("Commands Count:", project.Commands.Count)

    for i in range(1, project.Commands.Count + 1):
        cmd = project.Commands.Item(i)
        print(f"\nCommand {i} -- Name: {cmd.Name}")
        for attr in ("CommandLanguage", "OutputDocument"):
            try:
                print(f"  {attr}:", getattr(cmd, attr))
            except Exception as exc:  # noqa: BLE001
                print(f"  {attr}: <n/a> ({exc})")


if __name__ == "__main__":
    dump_minitab_commands()
