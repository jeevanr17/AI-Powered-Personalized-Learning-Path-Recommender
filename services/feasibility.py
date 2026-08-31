class FeasibilityEngine:
    """Check whether the roadmap fits within available study time."""

    def calculate_feasibility(self, available_hours: float, required_hours: float) -> dict:
        utilization = required_hours / available_hours if available_hours > 0 else 0.0
        feasible = utilization <= 1.0
        return {
            "available_hours": available_hours,
            "required_hours": required_hours,
            "utilization": utilization,
            "feasible": feasible,
            "warning": "Roadmap exceeds available study time." if not feasible else "Roadmap fits within available time.",
        }
