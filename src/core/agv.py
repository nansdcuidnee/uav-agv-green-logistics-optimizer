class AGV:
    """Ground vehicle used for mobile charging."""

    def __init__(self, agv_id, position, charging_power=200.0):
        self.id = agv_id
        self.position = position
        self.status = "idle"  # idle, transporting, charging
        self.charging_power = float(charging_power)

    def move_to(self, target_position):
        self.position = target_position

    def charge(self, uav):
        # Simple fixed-step charging model for baseline simulation.
        uav.update_battery(20)
        print(
            f"AGV {self.id} charged UAV {uav.id}: "
            f"{max(0, uav.battery - 20)}% -> {uav.battery}%"
        )