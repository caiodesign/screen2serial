import time
import serial


def open_serial(port: str, baud: int, retries: int = 5) -> serial.Serial:
    """Open serial connection with retries."""
    for _ in range(retries):
        try:
            ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # wait for device to be ready
            return ser
        except Exception:
            time.sleep(2)
    raise RuntimeError(f"Failed to open serial port: {port}")


def send_move(ser: serial.Serial, dx: int, dy: int) -> None:
    """Send move command to serial device."""
    ser.write(f"M{dx},{dy}\n".encode())


def send_click(ser: serial.Serial) -> None:
    """Send left click command to serial device."""
    ser.write(b"L\n")


def send_shift_click(ser: serial.Serial, x: int, y: int) -> None:
    """Send shift+left click command at absolute position."""
    ser.write(f"SL{x},{y}\n".encode())


def compute_hesitation(
    confidence: float,
    threshold: float,
    hesitation_min: float,
    hesitation_max: float,
) -> float:
    """
    Compute hesitation time based on confidence.
    Higher confidence = less hesitation.
    """
    t = (confidence - threshold) / (1.0 - threshold)
    t = max(0.0, min(1.0, t))
    return hesitation_max - t * (hesitation_max - hesitation_min)
