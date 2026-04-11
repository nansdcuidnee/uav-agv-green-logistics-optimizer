#!/usr/bin/env python3
"""Message dispatch for communication."""

class MessageDispatcher:
    """Message dispatcher for routing messages between devices."""
    
    def __init__(self, network_manager):
        """Initialize message dispatcher."""
        self.network_manager = network_manager
        self.handlers = {}
    
    def register_handler(self, message_type, handler):
        """Register a message handler for a specific message type."""
        self.handlers[message_type] = handler
    
    def dispatch_message(self, message):
        """Dispatch a message to the appropriate handler."""
        message_type = message["message_type"]
        if message_type in self.handlers:
            self.handlers[message_type](message)
        else:
            print(f"No handler for message type: {message_type}")
    
    def process_messages(self, device_id):
        """Process messages for a device."""
        messages = self.network_manager.receive_messages(device_id)
        for message in messages:
            self.dispatch_message(message)
    
    def broadcast_message(self, sender, message_type, content):
        """Broadcast a message to all connected devices."""
        for device_id in self.network_manager.connections:
            if device_id != sender:
                self.network_manager.send_message(sender, device_id, message_type, content)
