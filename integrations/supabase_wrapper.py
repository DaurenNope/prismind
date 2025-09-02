from typing import Any, Optional

class SupabaseWrapper:
    def __init__(self, client: Any):
        self.client = client

    def insert(self, table: str, data: dict) -> Any:
        return self.client.table(table).insert(data).execute()
