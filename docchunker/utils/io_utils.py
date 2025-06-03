
import json


def write_json(file_path: str, data: dict | list[dict]) -> None:
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
