import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "x_sensitivity": 1.5,
    "y_sensitivity": 1.8,
    "head_eye_ratio": 0.5,  # 0.0 = 100% Eye, 1.0 = 100% Head
    "smoothing": 0.35,      # Exponential moving average weight (0.05 - 1.0)
    "deadzone": 0.002,      # Minimum displacement required to move cursor
    "blink_threshold": 0.005,
    "blink_cooldown": 0.8,
    "blink_enabled": True,
    "mouse_control_enabled": False,
    "draw_landmarks": True,
    "calibration": {
        "is_calibrated": False,
        "raw_x_min": 0.3,
        "raw_x_max": 0.7,
        "raw_y_min": 0.3,
        "raw_y_max": 0.7,
        "points": []
    }
}

class ConfigManager:
    def __init__(self, filepath=CONFIG_FILE):
        self.filepath = filepath
        self.data = self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    saved_data = json.load(f)
                    # Merge with default config to ensure missing keys are populated
                    config = DEFAULT_CONFIG.copy()
                    config.update(saved_data)
                    return config
            except Exception as e:
                print(f"Error loading config, using defaults: {e}")
        return DEFAULT_CONFIG.copy()

    def save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.data, f, indent=4)
            print(f"Configuration saved to {self.filepath}")
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def reset_defaults(self):
        self.data = DEFAULT_CONFIG.copy()
        self.save()
