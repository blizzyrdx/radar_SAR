
import subprocess
import threading
import queue
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
from project_paths import POWERSHELL_DIR

BRIDGE = POWERSHELL_DIR / "rstd_persistent.ps1"

class RadarSession:

    def __init__(self):

        self.messages = queue.Queue()

        self.process = subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-File",
                str(BRIDGE)
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        self.reader = threading.Thread(
            target=self.read_output,
            daemon=True
        )

        self.reader.start()

        try:
            self.wait_for("RSTD_READY", timeout=15)
        except Exception:
            self.process.kill()
            self.process.wait()
            raise

        print("Persistent radar connection established.")

    def read_output(self):

        for line in self.process.stdout:
            self.messages.put(line.strip())

    def wait_for(self, expected, timeout=15):

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:

            remaining = deadline - time.monotonic()

            try:
                message = self.messages.get(
                    timeout=max(0, remaining)
                )

            except queue.Empty:
                break

            if message.startswith("ERROR:"):
                raise RuntimeError(message)

            if message.startswith(expected):
                return message

            print(message)

        raise TimeoutError(
            f"Timed out waiting for {expected}"
        )

    def send(self, command, timeout=15):

        if self.process.poll() is not None:
            raise RuntimeError("Radar session is closed.")

        if "\n" in command or "\r" in command:
            raise ValueError("Send one Lua line at a time.")

        print("Sending:", command)

        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

        response = self.wait_for(
            "STATUS:", timeout
        )

        status = int(response.split(":")[1])

        if status != 0:
            raise RuntimeError(
                f"Command returned status {status}"
            )

        print("Command status:", status)

        return status

    def run_script(self, filename):

        path = PROJECT_DIR / filename

        if not path.is_file():
            raise FileNotFoundError(path)

        return self.send(
            f'dofile([[{path.as_posix()}]])',
            timeout=60
        )

    def close(self):

        if self.process.poll() is None:

            try:
                self.process.stdin.write("EXIT\n")
                self.process.stdin.flush()
                self.process.wait(timeout=5)

            except (subprocess.TimeoutExpired, OSError):
                self.process.kill()
                self.process.wait()

        print("Radar session closed.")


# ==========================================
# Test persistent connection
# ==========================================

if __name__ == "__main__":

    radar = RadarSession()

    try:

        for i in range(1, 6):

            radar.send(
                f'WriteToLog("Python test {i}", "green")'
            )

            time.sleep(1)

        print("\nAll five commands returned successfully!")

    finally:

        radar.close()
