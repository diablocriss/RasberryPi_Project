import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
EXAMPLE_COMMANDS = [
    "move forward",
    "move foward",
    "go forward",
    "forward",
    "foward",
    "move backward",
    "go backward",
    "backward",
    "move left",
    "turn left",
    "left",
    "move right",
    "turn right",
    "right",
    "speed up",
    "slow down",
    "emergency stop",
    "stop",
]


def run(command: list[str], env: dict[str, str] | None = None, input_text: str | None = None) -> None:
    subprocess.run(command, cwd=ROOT, env=env, input=input_text, text=True, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Windows development checks.")
    parser.add_argument("--install", action="store_true", help="Install or refresh requirements.")
    parser.add_argument("--smoke", action="store_true", help="Run text workflow smoke test after pytest.")
    parser.add_argument("--all-commands", action="store_true", help="Run every example text command through the workflow.")
    args = parser.parse_args()

    if not VENV_PYTHON.exists():
        run(["py", "-3", "-m", "venv", ".venv"])
        args.install = True

    python = str(VENV_PYTHON)

    if args.install:
        run([python, "-m", "pip", "install", "-r", "requirements.txt"])

    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    print("Running compile check...")
    run([python, "-m", "compileall", "-q", "src", "tests"], env=env)

    print("Running tests...")
    run([python, "-m", "pytest", "-q"], env=env)

    if args.smoke or args.all_commands:
        smoke_env = env.copy()
        smoke_env["ROBOT_WORKFLOW"] = "text_hybrid"
        smoke_env["ROBOT_DRY_RUN"] = "1"
        smoke_env["ROBOT_UART_PORT"] = "COM3"

        commands = EXAMPLE_COMMANDS if args.all_commands else ["move forward"]
        input_text = "\n".join(commands + ["exit"]) + "\n"
        print("Running text workflow command test...")
        run([python, "src/main.py"], env=smoke_env, input_text=input_text)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
