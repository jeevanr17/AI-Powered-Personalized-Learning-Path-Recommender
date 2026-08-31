class ProgressTracker:
    """Track progress across the learning roadmap."""

    def compute_progress(self, path: dict, completed_resource_ids: set[str]) -> dict:
        items = path.get("phases", [])
        total = 0
        completed = 0
        for phase in items:
            for resource in phase.get("resources", []):
                total += 1
                if resource.get("resource_id") in completed_resource_ids:
                    completed += 1
        percent = (completed / total) * 100 if total else 0.0
        return {
            "total_resources": total,
            "completed_resources": completed,
            "percent_complete": round(percent, 2),
            "current_phase": items[0].get("name") if items else "N/A",
        }
