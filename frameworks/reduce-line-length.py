#!/usr/bin/env python3
"""
Reflow YAML plain scalars without using block indicators ('>' or '|').
Usage: reflow_yaml_plain.py <infile> [width]
Writes output to <infile>.reflowed by default.
"""
import sys
from collections.abc import Mapping, Sequence

from ruamel.yaml import YAML

if len(sys.argv) < 2:
    print("Usage: reflow_yaml_plain.py <infile> [width]")
    sys.exit(2)

INFILE = sys.argv[1]
WIDTH = int(sys.argv[2]) if len(sys.argv) > 2 else 80
TARGET_KEYS = {"description", "title", "summary", "content"}

yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False
yaml.width = WIDTH


def collapse_whitespace(s: str) -> str:
    return " ".join(s.split())


def walk(node):
    if isinstance(node, Mapping):
        for k, v in list(node.items()):
            if isinstance(k, str) and isinstance(v, str) and k in TARGET_KEYS:
                node[k] = collapse_whitespace(v)  # type: ignore
            else:
                walk(v)
    elif isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
        for item in node:
            walk(item)


with open(INFILE, "r", encoding="utf-8") as f:
    data = yaml.load(f)

walk(data)

OUT = INFILE + ".reflowed"
with open(OUT, "w", encoding="utf-8") as f:
    yaml.dump(data, f)

print(f"Wrote: {OUT}")
