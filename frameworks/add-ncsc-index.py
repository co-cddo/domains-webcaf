#!/usr/bin/env python3
import sys
from collections import defaultdict

import yaml


def main():
    if len(sys.argv) != 3:
        print("Usage: add-ncsc-index.py <yaml-file>")
        sys.exit(1)

    source = sys.argv[1]
    target = sys.argv[2]
    with open(source, "r") as f:
        data = yaml.safe_load(f)

    # For each indicator, add ncsc-index
    objectives = data.get("objectives", {})
    for obj_key, obj_val in objectives.items():
        principles = obj_val.get("principles", {})
        for princ_key, princ_val in principles.items():
            outcomes = princ_val.get("outcomes", {})
            for out_key, out_val in outcomes.items():
                indicators = out_val.get("indicators", {})
                # Track unique number per group
                group_counters = defaultdict(int)
                for group in ["achieved", "not-achieved", "partially-achieved"]:
                    group_short = {"achieved": "A", "not-achieved": "NA", "partially-achieved": "PA"}[group]
                    group_inds = indicators.get(group, {})
                    for ind_key, ind_val in group_inds.items():
                        group_counters[group] += 1
                        ncsc_index = f"{obj_key}{princ_key[-1]}.{out_key[-1]}.{group_short}.{group_counters[group]}"
                        ind_val["ncsc-index"] = ncsc_index
    # Output the modified YAML
    with open(target, "w") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


if __name__ == "__main__":
    main()
