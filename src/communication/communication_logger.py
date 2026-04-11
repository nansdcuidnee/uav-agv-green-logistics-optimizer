#!/usr/bin/env python3
"""Communication logger for recording communication events."""

import csv
from pathlib import Path

class CommunicationLogger:
    """Communication logger for recording communication events."""
    
    def __init__(self, log_file):
        """Initialize communication logger."""
        self.log_file = Path(log_file)
        self._create_log_file()
    
    def _create_log_file(self):
        """Create log file with header."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "sender", "receiver", "message_type", "content"])
    
    def log_message(self, timestamp, sender, receiver, message_type, content):
        """Log a message."""
        with open(self.log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, sender, receiver, message_type, content])
    
    def log_event(self, timestamp, event_type, details):
        """Log an event."""
        with open(self.log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, "SYSTEM", "ALL", event_type, details])
    
    def get_logs(self):
        """Get all logs."""
        logs = []
        if self.log_file.exists():
            with open(self.log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                logs = list(reader)
        return logs
