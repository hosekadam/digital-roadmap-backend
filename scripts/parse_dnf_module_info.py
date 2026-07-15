#!/usr/bin/env python3
"""
Parse `dnf module info "*"` output and generate MODULE_PACKAGES-compatible data.

Usage:
    dnf module info "*" 2>/dev/null > /tmp/dnf_modules.txt
    python scripts/parse_dnf_module_info.py /tmp/dnf_modules.txt

    # Or pipe directly:
    dnf module info "*" 2>/dev/null | python scripts/parse_dnf_module_info.py

Output:
    src/roadmap/data/module_packages_live.py  (same format as module_packages.py)

Then diff:
    diff src/roadmap/data/module_packages.py src/roadmap/data/module_packages_live.py
"""

import re
import sys

from datetime import datetime
from pathlib import Path


def parse_nevra(nevra_string):
    """Extract package name from NEVRA string (same logic as generate_module_packages.py)."""
    if ":" in nevra_string:
        match = re.match(r"^(.+?)-\d+:", nevra_string)
        if match:
            return match.group(1)
    return nevra_string.split("-")[0]


def detect_os_major(nevra):
    """Detect OS major version from NEVRA release string."""
    for ver in (10, 9, 8):
        if f".el{ver}" in nevra or f"module+el{ver}" in nevra or f"module_el{ver}" in nevra:
            return ver
    return None


def parse_dnf_module_info(lines):  # noqa: C901
    """
    Parse dnf module info output into {(name, os_major, stream): set[str]}.

    dnf module info output format:
        Name             : nodejs
        Stream           : 10
        ...
        Artifacts        : nodejs-1:10.24.1-1.module+el8.5.0+....x86_64
                         : nodejs-devel-1:10.24.1-1.module+el8.5.0+....x86_64
    """
    module_packages = {}

    current_name = None
    current_stream = None
    current_artifacts = []
    in_artifacts = False

    def flush():
        nonlocal current_name, current_stream, current_artifacts, in_artifacts
        if current_name and current_stream and current_artifacts:
            os_major = None
            for nevra in current_artifacts[:5]:
                os_major = detect_os_major(nevra)
                if os_major:
                    break

            if os_major:
                packages = set()
                for nevra in current_artifacts:
                    if "debuginfo" in nevra or "debugsource" in nevra:
                        continue
                    if not (".x86_64" in nevra or ".src" in nevra or ".noarch" in nevra):
                        continue
                    packages.add(parse_nevra(nevra))

                if packages:
                    key = (current_name, os_major, str(current_stream))
                    # Merge if same key appears multiple times (different arches/contexts)
                    if key in module_packages:
                        module_packages[key].update(packages)
                    else:
                        module_packages[key] = packages

        current_name = None
        current_stream = None
        current_artifacts = []
        in_artifacts = False

    for line in lines:
        line = line.rstrip("\n")

        # Blank line separates module entries
        if not line.strip():
            in_artifacts = False
            continue

        # Hint/error lines from dnf
        if line.startswith("Hint:") or line.startswith("Error:") or line.startswith("Warning:"):
            continue

        # Continuation line for Artifacts (starts with spaces + ":")
        if in_artifacts and re.match(r"^\s+:", line):
            nevra = line.split(":", 1)[1].strip()
            if nevra:
                current_artifacts.append(nevra)
            continue

        # New field line: "Key             : value"
        match = re.match(r"^(\w[\w ]*?)\s*:\s*(.*)", line)
        if not match:
            in_artifacts = False
            continue

        key, value = match.group(1).strip(), match.group(2).strip()

        if key == "Name":
            # Starting a new module block — flush previous
            flush()
            current_name = value
        elif key == "Stream":
            current_stream = value
        elif key == "Artifacts":
            in_artifacts = True
            if value:
                current_artifacts.append(value)
        else:
            in_artifacts = False

    flush()
    return module_packages


def generate_output_file(module_packages, output_path):
    """Write MODULE_PACKAGES in the same format as generate_module_packages.py."""
    sorted_items = sorted(
        module_packages.items(),
        key=lambda x: (x[0][1], x[0][0], x[0][2]),
    )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    for (module_name, os_major, stream), packages in sorted_items:
        key_repr = f'("{module_name}", {os_major}, "{stream}")'
        pkgs = set(sorted(packages))
        if len(pkgs) <= 3:
            packages_str = "{" + ", ".join(f'"{p}"' for p in pkgs) + "}"
            lines.append(f"    {key_repr}: {packages_str},")
        else:
            lines.append(f"    {key_repr}: {{")
            for pkg in pkgs:
                lines.append(f'        "{pkg}",')
            lines.append("    },")

    dict_content = "\n".join(lines)

    with open(output_path, "w") as f:
        f.write(f'''"""
AppStream Module to Package Mappings (from live system dnf module info)

This file maps (module_name, os_major, stream) -> set of package names.
Generated from: dnf module info "*"

Auto-generated by scripts/parse_dnf_module_info.py on {timestamp}
"""

MODULE_PACKAGES = {{
{dict_content}
}}
''')

    print(f"  Written {len(module_packages)} module entries to {output_path}")


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        print(f"Reading from file: {path}")
        with open(path) as f:
            lines = f.readlines()
    else:
        print('Reading from stdin (pipe `dnf module info "*" 2>/dev/null` into this script)...')
        lines = sys.stdin.readlines()

    module_packages = parse_dnf_module_info(lines)

    if not module_packages:
        print("ERROR: No module data parsed. Check input format.", file=sys.stderr)
        return 1

    print(f"Parsed {len(module_packages)} module entries")

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("module_packages_live.py")
    generate_output_file(module_packages, output_path)

    print("\nCopy to local machine, then diff:")
    print(f"  diff src/roadmap/data/module_packages.py {output_path.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
