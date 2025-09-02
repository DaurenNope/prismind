from dataclasses import dataclass

@dataclass
class UserPreferences:
    enable_collection: bool = True
    enable_analysis: bool = True
