import logging
import os

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Color codes
COLORS = {
    "INFO": "\033[92m",    # Green
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",   # Red
    "DEBUG": "\033[94m",   # Blue
    "RESET": "\033[0m"     # Reset color
}

# Custom colored formatter


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, COLORS["RESET"])
        message = super().format(record)
        return f"{color}{message}{COLORS['RESET']}"


# Logger setup
logger = logging.getLogger("travel_logger")
logger.setLevel(logging.INFO)

formatter = ColoredFormatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler (without color)
file_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)
file_handler = logging.FileHandler("logs/app.log", mode="a")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
