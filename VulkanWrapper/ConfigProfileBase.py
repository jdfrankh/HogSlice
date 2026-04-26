import copy
import json
import os


class ConfigProfileBase:
    """Shared profile base with setting-group metadata and profile IO helpers."""

    def __init__(self):
        self._setting_groups = {}
        self._default_settings_snapshot = None

    def add_group(self, group_name, setting_items):
        self._setting_groups[group_name] = list(setting_items)

    def get_group_names(self):
        return list(self._setting_groups.keys())

    def get_group_items(self, group_name):
        return list(self._setting_groups.get(group_name, []))

    @staticmethod
    def make_setting(label, attr_name, bounds):
        return {
            "type": "SETTING",
            "label": label,
            "attr": attr_name,
            "bounds": list(bounds),
        }

    @staticmethod
    def make_combobox(label, attr_name, options):
        return {
            "type": "COMBOBOX",
            "label": label,
            "attr": attr_name,
            "options": list(options),
        }

    def build_setting_rows(self, group_name):
        rows = []
        for item in self.get_group_items(group_name):
            if item.get("type") == "COMBOBOX":
                rows.append(["COMBOBOX", item["label"], item["attr"], list(item["options"])])
            else:
                rows.append(["SETTING", item["label"], item["attr"], list(item["bounds"])])
        return rows

    def _serialize_value(self, value):
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]

        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}

        if hasattr(value, "__dict__"):
            serialized = {}
            for key, item in value.__dict__.items():
                if key.startswith("_"):
                    continue
                serialized[key] = self._serialize_value(item)
            return serialized

        return value

    def to_settings_dict(self):
        data = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            data[key] = self._serialize_value(value)
        return data

    def _apply_value(self, current, incoming):
        if isinstance(current, dict) and isinstance(incoming, dict):
            merged = dict(current)
            for key, value in incoming.items():
                if key in merged:
                    merged[key] = self._apply_value(merged[key], value)
                else:
                    merged[key] = value
            return merged

        if isinstance(current, list) and isinstance(incoming, list):
            return list(incoming)

        if hasattr(current, "__dict__") and isinstance(incoming, dict):
            for key, value in incoming.items():
                if hasattr(current, key):
                    setattr(current, key, self._apply_value(getattr(current, key), value))
            return current

        return incoming

    def apply_settings_dict(self, data):
        for key, value in data.items():
            if key.startswith("_") or not hasattr(self, key):
                continue
            current = getattr(self, key)
            setattr(self, key, self._apply_value(current, value))

    def capture_defaults(self):
        self._default_settings_snapshot = copy.deepcopy(self.to_settings_dict())

    def reset_to_defaults(self):
        if self._default_settings_snapshot is None:
            self.capture_defaults()
        self.apply_settings_dict(copy.deepcopy(self._default_settings_snapshot))

    def save_settings(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as handle:
            json.dump(self.to_settings_dict(), handle, indent=4)

    def export_settings(self, filepath):
        self.save_settings(filepath)

    def import_settings(self, filepath):
        with open(filepath, "r") as handle:
            data = json.load(handle)
        self.apply_settings_dict(data)

    def load_settings(self, filepath):
        self.import_settings(filepath)
