import json
import os
from datetime import datetime

LOG_FILE = "server_logs.json"


def write_log(event, data=None):

    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "data": data
    }

    # If file doesn't exist create it
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f)

    # Read existing logs
    with open(LOG_FILE, "r") as f:
        logs = json.load(f)

    # Append new log
    logs.append(log_entry)

    # Write back
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)