#!/usr/bin/env python3
"""Network manager for communication."""

class NetworkManager:
    """Network manager for communication between UAVs, AGVs, and control center."""
    
    def __init__(self):
        """Initialize network manager."""
        self.connections = {}
        self.message_queue = []
    
    def connect(self, device_id, device_type):
        """Connect a device to the network."""
        self.connections[device_id] = device_type
        print(f"Device {device_id} ({device_type}) connected to network")
    
    def disconnect(self, device_id):
        """Disconnect a device from the network."""
        if device_id in self.connections:
            del self.connections[device_id]
            print(f"Device {device_id} disconnected from network")
    
    def send_message(self, sender, receiver, message_type, content):
        """Send a message from sender to receiver."""
        message = {
            "sender": sender,
            "receiver": receiver,
            "message_type": message_type,
            "content": content,
            "timestamp": self.get_timestamp()
        }
        self.message_queue.append(message)
        print(f"Message sent from {sender} to {receiver}: {message_type}")
    
    def receive_messages(self, device_id):
        """Receive messages for a device."""
        messages = [msg for msg in self.message_queue if msg["receiver"] == device_id]
        # Remove received messages from queue
        self.message_queue = [msg for msg in self.message_queue if msg["receiver"] != device_id]
        return messages
    
    def get_timestamp(self):
        """Get current timestamp."""
        import time
        return time.time()
    
    def broadcast_status(self, sender, status_type, content):
        """Broadcast status to all connected devices."""
        for device_id in self.connections:
            if device_id != sender:
                self.send_message(sender, device_id, status_type, content)
    
    def get_connected_devices(self):
        """Get list of connected devices."""
        return list(self.connections.items())
