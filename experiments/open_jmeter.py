#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import subprocess
import sys

# ==========================================================
# CONFIGURATION: Set your JMeter path here
# ----------------------------------------------------------
# Set this to your JMeter root directory or leave as None / ""
# Examples:
#   macOS/Linux: Path("/opt/apache-jmeter-5.6.3")
#   Windows:     Path(r"C:\Tools\apache-jmeter-5.6.3")
JMETER_HOME = Path("$HOME/Documents/AIS/901-Thesis/Apps/apache-jmeter-5.6.3")
# ==========================================================


def get_jmeter_binary() -> str:
    """Resolve the path to the jmeter executable."""
    # Binary name differs on Windows
    binary_name = "jmeter.bat" if sys.platform == "win32" else "jmeter"

    # 1. Check user-configured JMETER_HOME at top of this script
    if JMETER_HOME and str(JMETER_HOME).strip():
        # Expand environment variables ($HOME) and tilde (~)
        expanded_path = os.path.expandvars(str(JMETER_HOME))
        jmeter_home_path = Path(expanded_path).expanduser()

        custom_bin = jmeter_home_path / "bin" / binary_name
        if custom_bin.is_file():
            return str(custom_bin)
        else:
            print(
                f"Error: Could not find '{binary_name}' in '{custom_bin.parent}'.",
                file=sys.stderr,
            )
            sys.exit(1)

    # 2. Check if JMETER_HOME environment variable is set in the OS
    env_home = os.environ.get("JMETER_HOME")
    if env_home:
        env_bin = Path(env_home) / "bin" / binary_name
        if env_bin.is_file():
            return str(env_bin)

    # 3. Fallback: Check if 'jmeter' is available directly in system PATH
    system_bin = shutil.which("jmeter")
    if system_bin:
        return system_bin

    print(
        "Error: JMeter could not be found.\n"
        "Please set 'JMETER_HOME' at the top of the script or add JMeter to your PATH.",
        file=sys.stderr,
    )
    sys.exit(1)


def open_jmeter(jmx_path: Path):
    """Launch JMeter with the specified .jmx file."""
    jmeter_cmd = get_jmeter_binary()

    print(f"\nOpening JMeter using: {jmeter_cmd}")
    print(f"Loading test plan:   {jmx_path}")

    subprocess.run([jmeter_cmd, "-t", str(jmx_path)])


def main():
    target_arg = sys.argv[1] if len(sys.argv) > 1 else "."
    target_dir = Path(target_arg).resolve()

    if not target_dir.is_dir():
        print(f"Error: Directory '{target_arg}' does not exist.", file=sys.stderr)
        sys.exit(1)

    jmx_files = sorted(list(target_dir.glob("*.jmx")))
    file_count = len(jmx_files)

    if file_count == 0:
        print("Error: No .jmx files found in this directory.", file=sys.stderr)
        sys.exit(1)

    elif file_count == 1:
        target_jmx = jmx_files[0]
        print(f"Found exactly one file: {target_jmx.name}")
        open_jmeter(target_jmx)

    else:
        print("Multiple .jmx files found. Please choose one to open:")
        print("------------------------------------------------")

        for idx, file in enumerate(jmx_files, start=1):
            print(f"{idx}) {file.name}")

        prompt = "Enter the number of your choice (or press 'q' to quit): "

        while True:
            try:
                choice = input(prompt).strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting script.")
                sys.exit(0)

            if choice.lower() == "q":
                print("Exiting script.")
                break
            elif choice.isdigit() and 1 <= int(choice) <= file_count:
                selected_file = jmx_files[int(choice) - 1]
                open_jmeter(selected_file)
                break
            else:
                print(f"Invalid choice. Please pick a number from 1 to {file_count}.")


if __name__ == "__main__":
    main()
