#!/usr/bin/env python3

import copy
import os
from typing import Any

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(SCRIPT_DIR, "cyber-assessment-framework-v3.2.yaml")
TARGET = os.path.join(SCRIPT_DIR, "cyber-assessment-framework-v3.2-renumbered.yaml")


def process_indicators(indicators: dict[str, dict[int | str, str]], section_code: str) -> dict[str, dict[str, str]]:
    new_indicators: dict[str, dict[str, str]] = {}
    all_indicators = []
    for level, indicators_dict in indicators.items():
        if not indicators_dict:
            new_indicators[level] = {}
            continue
        for key, text in indicators_dict.items():
            all_indicators.append((level, key, text))

    def get_sort_key(item):
        key = item[1]
        if isinstance(key, int):
            return key
        try:
            return int(key)
        except (ValueError, TypeError):
            return key

    all_indicators.sort(key=get_sort_key)
    for i, (level, _, text) in enumerate(all_indicators, 1):
        if level not in new_indicators:
            new_indicators[level] = {}
        new_key = f"{section_code}.{i}"
        new_indicators[level][new_key] = text
    return new_indicators


def process_yaml(yaml_data: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(yaml_data)
    for obj_key, objective in yaml_data["objectives"].items():
        if "principles" not in objective:
            continue
        for prin_key, principle in objective["principles"].items():
            if not isinstance(principle, dict):
                continue
            if "sections" not in principle:
                continue
            for sec_key, section in principle["sections"].items():
                if not isinstance(section, dict):
                    continue
                if "code" not in section or "indicators" not in section:
                    continue
                section_code = section["code"]
                result["objectives"][obj_key]["principles"][prin_key]["sections"][sec_key][
                    "indicators"
                ] = process_indicators(section["indicators"], section_code)
    return result


def main(input_file: str, output_file: str):
    with open(input_file, "r") as f:
        yaml_data = yaml.safe_load(f)
    processed_data = process_yaml(yaml_data)
    with open(output_file, "w") as f:
        yaml.dump(processed_data, f, default_flow_style=False, sort_keys=False, width=80)
    print(f"Processed YAML saved to {output_file}")


if __name__ == "__main__":
    main(SOURCE, TARGET)
