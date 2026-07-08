class EnergyLayer:
    def __init__(self, energy_profile: dict = None):
        if energy_profile is None:
            energy_profile = {
                "loaded_consumption_l_per_km": 2.8,
                "empty_consumption_l_per_km": 1.7,
                "idle_consumption_l_per_hour": 12.0,
                "fuel_to_energy_kwh_coeff": 9.7
            }
        self.loaded_consumption = energy_profile.get("loaded_consumption_l_per_km", 2.8)
        self.empty_consumption = energy_profile.get("empty_consumption_l_per_km", 1.7)
        self.idle_consumption = energy_profile.get("idle_consumption_l_per_hour", 12.0)
        self.fuel_to_kwh = energy_profile.get("fuel_to_energy_kwh_coeff", 9.7)

    def calculate_fuel(self, status: str, distance_km: float, idle_hours: float) -> float:
        """
        Calculates fuel consumed during a specific movement or idling period.
        """
        if status == "moving_loaded" or status == "haul":
            return distance_km * self.loaded_consumption
        elif status == "moving_empty" or status == "back" or status == "init":
            return distance_km * self.empty_consumption
        elif status in ["idle", "loading", "unloading", "stopped"]:
            return idle_hours * self.idle_consumption
        return 0.0

    def fuel_to_energy_kwh(self, fuel_liters: float) -> float:
        """
        Converts fuel in liters to equivalent kWh of energy.
        """
        return fuel_liters * self.fuel_to_kwh
