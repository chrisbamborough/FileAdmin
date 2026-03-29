from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


OSASCRIPT_TIMEOUT_SECONDS = 30

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    TK_AVAILABLE = True
except ModuleNotFoundError:
    tk = None
    filedialog = None
    messagebox = None
    ttk = None
    TK_AVAILABLE = False


def iter_source_files(source: Path, include_subfolders: bool):
    if include_subfolders:
        for root, _, files in os.walk(source):
            for file_name in files:
                yield Path(root) / file_name
    else:
        for path in source.iterdir():
            if path.is_file():
                yield path


def build_unique_destination(desired_path: Path) -> Path:
    if not desired_path.exists():
        return desired_path

    stem = desired_path.stem
    suffix = desired_path.suffix
    parent = desired_path.parent
    counter = 1

    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def organize_files(
    source: Path,
    destination_root: Path,
    keyword: str,
    include_subfolders: bool,
    case_sensitive: bool,
    logger,
) -> tuple[int, int]:
    keyword_folder = destination_root / keyword
    keyword_folder.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    skipped_count = 0

    logger("--- Starting organization ---")
    logger(f"Source: {source}")
    logger(f"Destination keyword folder: {keyword_folder}")
    logger(f"Keyword: {keyword}")

    match_keyword = keyword if case_sensitive else keyword.lower()

    for file_path in iter_source_files(source, include_subfolders):
        name_to_check = file_path.name if case_sensitive else file_path.name.lower()
        if match_keyword not in name_to_check:
            continue

        # Avoid moving a file if it is already in the target keyword folder.
        if file_path.parent.resolve() == keyword_folder.resolve():
            skipped_count += 1
            logger(f"Skipped (already organized): {file_path}")
            continue

        destination_file = build_unique_destination(keyword_folder / file_path.name)

        try:
            shutil.move(str(file_path), str(destination_file))
            moved_count += 1
            logger(f"Moved: {file_path} -> {destination_file}")
        except Exception as exc:  # noqa: BLE001
            skipped_count += 1
            logger(f"Skipped (error): {file_path} ({exc})")

    return moved_count, skipped_count


class FileOrganizerApp:
    def __init__(self, root) -> None:
        self.root = root
        self.root.title("Keyword File Organizer")
        self.root.geometry("760x420")
        self.root.minsize(700, 380)

        self.source_var = tk.StringVar()
        self.keyword_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self.include_subfolders_var = tk.BooleanVar(value=True)
        self.case_sensitive_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(frame, text="Organize Files by Keyword", font=("Helvetica", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="Source folder:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.source_var, width=72).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse", command=self._pick_source).grid(row=1, column=2)

        ttk.Label(frame, text="Keyword:").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.keyword_var, width=72).grid(row=2, column=1, sticky="ew", padx=8)

        ttk.Label(frame, text="Destination folder:").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.destination_var, width=72).grid(row=3, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse", command=self._pick_destination).grid(row=3, column=2)

        options_frame = ttk.Frame(frame)
        options_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 4))

        ttk.Checkbutton(
            options_frame,
            text="Include subfolders",
            variable=self.include_subfolders_var,
        ).pack(side="left", padx=(0, 18))

        ttk.Checkbutton(
            options_frame,
            text="Case sensitive keyword match",
            variable=self.case_sensitive_var,
        ).pack(side="left")

        ttk.Button(frame, text="Organize Files", command=self._organize_files).grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(14, 10),
        )

        ttk.Label(frame, text="Activity log:").grid(row=6, column=0, columnspan=3, sticky="w")

        self.log_box = tk.Text(frame, height=12, wrap="word")
        self.log_box.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(4, 0))

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log_box.yview)
        scrollbar.grid(row=7, column=2, sticky="nse", padx=(0, 2))
        self.log_box.configure(yscrollcommand=scrollbar.set)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)

    def _pick_source(self) -> None:
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_var.set(folder)

    def _pick_destination(self) -> None:
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.destination_var.set(folder)

    def _log(self, message: str) -> None:
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")

    def _organize_files(self) -> None:
        source_str = self.source_var.get().strip()
        destination_str = self.destination_var.get().strip()
        keyword = self.keyword_var.get().strip()

        if not source_str or not destination_str or not keyword:
            messagebox.showerror(
                "Missing required fields",
                "Please choose source, keyword, and destination.",
            )
            return

        source = Path(source_str)
        destination_root = Path(destination_str)

        if not source.exists() or not source.is_dir():
            messagebox.showerror("Invalid source", "Source folder does not exist.")
            return

        if not destination_root.exists() or not destination_root.is_dir():
            messagebox.showerror("Invalid destination", "Destination folder does not exist.")
            return

        include_subfolders = self.include_subfolders_var.get()
        case_sensitive = self.case_sensitive_var.get()
        moved_count, skipped_count = organize_files(
            source=source,
            destination_root=destination_root,
            keyword=keyword,
            include_subfolders=include_subfolders,
            case_sensitive=case_sensitive,
            logger=self._log,
        )

        summary = f"Done. Moved: {moved_count}, Skipped: {skipped_count}"
        self._log(summary)
        messagebox.showinfo("Finished", summary)


def _prompt_bool(question: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    try:
        raw = input(f"{question} [{suffix}]: ").strip().lower()
    except EOFError:
        return default
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true"}


def _pick_folder_with_finder(prompt_text: str) -> Path | None:
    safe_prompt = prompt_text.replace('"', "'")
    script = (
        f'POSIX path of (choose folder with prompt "{safe_prompt}")'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=OSASCRIPT_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    folder = result.stdout.strip()
    if not folder:
        return None
    return Path(folder)


def _ask_text_with_dialog(prompt_text: str, title: str = "Keyword File Organizer") -> str | None:
    safe_prompt = prompt_text.replace('"', "'")
    safe_title = title.replace('"', "'")
    script = (
        f'text returned of (display dialog "{safe_prompt}" '
        f'with title "{safe_title}" default answer "" buttons {{"Cancel", "OK"}} default button "OK")'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=OSASCRIPT_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    return result.stdout.strip()


def _ask_bool_with_dialog(prompt_text: str, default: bool) -> bool | None:
    safe_prompt = prompt_text.replace('"', "'")
    yes_first = default
    buttons = '{"Yes", "No"}' if yes_first else '{"No", "Yes"}'
    default_button = '"Yes"' if default else '"No"'
    script = (
        f'button returned of (display dialog "{safe_prompt}" '
        f'buttons {buttons} default button {default_button})'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=OSASCRIPT_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    return result.stdout.strip() == "Yes"


def _show_dialog_message(message: str, title: str = "Keyword File Organizer") -> None:
    safe_message = message.replace('"', "'")
    safe_title = title.replace('"', "'")
    script = (
        f'display dialog "{safe_message}" with title "{safe_title}" '
        'buttons {"OK"} default button "OK"'
    )
    subprocess.run(
        ["osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=OSASCRIPT_TIMEOUT_SECONDS,
    )


def run_macos_dialog_mode() -> bool:
    print("Starting macOS dialog mode...")
    source = _pick_folder_with_finder("Select source folder")
    if source is None:
        print("macOS dialog mode unavailable or canceled at source selection.")
        return False

    keyword = _ask_text_with_dialog("Enter keyword to match in filenames")
    if keyword is None:
        return True

    destination_root = _pick_folder_with_finder("Select destination folder")
    if destination_root is None:
        return True

    include_subfolders = _ask_bool_with_dialog("Include subfolders?", default=True)
    if include_subfolders is None:
        return True

    case_sensitive = _ask_bool_with_dialog("Use case-sensitive keyword match?", default=False)
    if case_sensitive is None:
        return True

    if not source.exists() or not source.is_dir():
        _show_dialog_message("Source folder does not exist.")
        return True

    if not destination_root.exists() or not destination_root.is_dir():
        _show_dialog_message("Destination folder does not exist.")
        return True

    if not keyword:
        _show_dialog_message("Keyword cannot be empty.")
        return True

    moved_count, skipped_count = organize_files(
        source=source,
        destination_root=destination_root,
        keyword=keyword,
        include_subfolders=include_subfolders,
        case_sensitive=case_sensitive,
        logger=print,
    )
    _show_dialog_message(f"Done. Moved: {moved_count}, Skipped: {skipped_count}")
    return True


def _pick_folder_cli(label: str) -> Path:
    use_finder = _prompt_bool(f"Select {label} in Finder", default=True)
    if use_finder:
        selected = _pick_folder_with_finder(f"Select {label}")
        if selected is not None:
            print(f"Selected {label}: {selected}")
            return selected
        print("Finder selection unavailable or canceled. Please type the path instead.")

    try:
        typed = input(f"{label.capitalize()} folder path: ").strip()
    except EOFError:
        return Path()
    return Path(typed).expanduser()


def run_cli() -> None:
    print("Keyword File Organizer (CLI mode)")
    print("Tkinter is unavailable, so running in terminal mode.")

    if not sys.stdin.isatty():
        print("Interactive input is required. Run this in a terminal and follow the prompts.")
        return

    try:
        source = _pick_folder_cli("source")
        keyword = input("Keyword: ").strip()
        destination_root = _pick_folder_cli("destination")
    except KeyboardInterrupt:
        print("\nCanceled by user.")
        return

    include_subfolders = _prompt_bool("Include subfolders", default=True)
    case_sensitive = _prompt_bool("Case sensitive keyword match", default=False)

    if not source.exists() or not source.is_dir():
        print("Error: Source folder does not exist.")
        return

    if not destination_root.exists() or not destination_root.is_dir():
        print("Error: Destination folder does not exist.")
        return

    if not keyword:
        print("Error: Keyword cannot be empty.")
        return

    moved_count, skipped_count = organize_files(
        source=source,
        destination_root=destination_root,
        keyword=keyword,
        include_subfolders=include_subfolders,
        case_sensitive=case_sensitive,
        logger=print,
    )

    print(f"Done. Moved: {moved_count}, Skipped: {skipped_count}")


def main() -> None:
    print("Launching Keyword File Organizer...")

    args = set(sys.argv[1:])

    if "--help" in args or "-h" in args:
        print("Usage:")
        print("  python3 app.py               # terminal mode (default)")
        print("  python3 app.py --mac-dialog  # macOS popup dialogs")
        print("  python3 app.py --gui         # Tk GUI mode (if available)")
        return

    if "--mac-dialog" in args:
        if sys.platform == "darwin" and run_macos_dialog_mode():
            return
        print("macOS dialog mode failed. Falling back to terminal prompts.")
        run_cli()
        return

    if "--gui" in args:
        if not TK_AVAILABLE:
            print("Tkinter not available. Falling back to terminal prompts.")
            run_cli()
            return

        try:
            root = tk.Tk()
        except tk.TclError as exc:
            print(f"GUI unavailable ({exc}). Falling back to terminal prompts.")
            run_cli()
            return

        # Use a modern ttk theme when available.
        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        FileOrganizerApp(root)
        root.mainloop()
        return

    print("Using terminal mode.")
    run_cli()


if __name__ == "__main__":
    main()
