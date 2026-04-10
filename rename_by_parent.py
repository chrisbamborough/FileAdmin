#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def build_target(file_path: Path) -> Path:
    parent_name = file_path.parent.name
    return file_path.with_name(f"{parent_name}_{file_path.name}")


def pick_folder() -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "tkinter is not available in this Python environment"
        ) from exc

    root = tk.Tk()
    root.withdraw()
    root.update()
    selected = filedialog.askdirectory(title="Select folder to rename files in")
    root.destroy()
    if not selected:
        return None
    return Path(selected).resolve()


def pick_folder_macos() -> Path | None:
    script = 'POSIX path of (choose folder with prompt "Select folder to rename files in")'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        if "(-128)" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or "macOS file picker failed")

    selected = result.stdout.strip()
    if not selected:
        return None
    return Path(selected).resolve()


def iter_files(root: Path, recursive: bool) -> list[Path]:
    if root.is_file():
        return [root]
    pattern = "**/*" if recursive else "*"
    return sorted(path for path in root.glob(pattern) if path.is_file())


def rename_files(files: list[Path], dry_run: bool) -> int:
    renamed = 0

    for file_path in files:
        target = build_target(file_path)

        if file_path.name == target.name:
            print(f"skip: {file_path} (already prefixed)")
            continue

        if target.exists():
            print(f"skip: {file_path} -> {target} (target exists)")
            continue

        print(f"{'would rename' if dry_run else 'rename'}: {file_path} -> {target}")
        if not dry_run:
            file_path.rename(target)
        renamed += 1

    return renamed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename files to <parent-folder>_<original-filename>."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="File or directory to process.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Process files in subdirectories.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the rename. Without this flag, the script runs in dry-run mode.",
    )
    parser.add_argument(
        "--select-folder",
        action="store_true",
        help="Open a folder picker and process all files recursively.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    open_picker = args.select_folder or args.path is None

    if open_picker:
        try:
            selected_folder = pick_folder()
        except RuntimeError as exc:
            if sys.platform == "darwin":
                try:
                    selected_folder = pick_folder_macos()
                except RuntimeError as mac_exc:
                    print(f"error: {exc}; macOS fallback failed: {mac_exc}")
                    return 1
            else:
                print(f"error: {exc}")
                return 1

        if not selected_folder:
            print("no folder selected")
            return 0

        files = iter_files(selected_folder, recursive=True)
    else:
        root = Path(args.path or ".").expanduser().resolve()
        if not root.exists():
            print(f"error: path does not exist: {root}")
            return 1
        files = iter_files(root, args.recursive)

    renamed = rename_files(files, dry_run=not args.apply)
    print(f"processed: {renamed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
