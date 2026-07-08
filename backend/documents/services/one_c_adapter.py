class OneCAdapter:
    def prepare_payload(self, data: dict) -> dict:
        return {
            "employee_name": data.get("employee_name"),
            "date": data.get("date"),
            "object": data.get("object"),
            "work_type": data.get("work_type"),
            "hours": data.get("hours"),
            "comment": data.get("comment"),
        }

    def send_worklog(self, data: dict) -> dict:
        return {
            "status": "prepared_for_1c",
            "mode": "mock",
            "payload": self.prepare_payload(data),
            "message": (
                "Real OData/API integration can be added after receiving "
                "1C credentials and endpoint structure."
            ),
        }
