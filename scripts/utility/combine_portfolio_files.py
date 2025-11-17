#!/usr/bin/env python3
"""Script to combine all portfolio_*.py files into a single portfolio.py file."""

import re
from pathlib import Path

# Order matters: files that depend on others should come later
FILES_TO_COMBINE = [
    "portfolio_calculations.py",
    "portfolio_ingestion.py",
    "portfolio_enrichment.py",
    "portfolio_exposure.py",
    "portfolio_optimizer.py",
    "portfolio_attribution.py",
    "portfolio_scenarios.py",
    "portfolio_reporting.py",
]

SRC_DIR = Path("src/finanlyzeos_chatbot")

def combine_files():
    """Combine all portfolio files into one."""
    
    # Collect all content
    sections = {
        "header": [],
        "imports": set(),
        "dataclasses": [],
        "functions": [],
    }
    
    # Process each file
    for filename in FILES_TO_COMBINE:
        filepath = SRC_DIR / filename
        if not filepath.exists():
            print(f"Warning: {filename} not found")
            continue
        
        content = filepath.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        # Extract docstring/header
        if lines[0].startswith('"""') or lines[0].startswith("'''"):
            sections["header"].append(f"# From {filename}")
            sections["header"].append(lines[0])
            if len(lines) > 1 and (lines[1].startswith('"""') or lines[1].startswith("'''")):
                sections["header"].append(lines[1])
        
        # Extract imports
        in_imports = False
        import_lines = []
        for line in lines:
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                import_lines.append(line.strip())
                sections["imports"].add(line.strip())
            elif line.strip() == "" and import_lines:
                continue
            else:
                if import_lines:
                    in_imports = False
        
        # Extract everything else (dataclasses and functions)
        skip_until_next = False
        current_section = []
        
        for i, line in enumerate(lines):
            # Skip imports and docstrings
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                continue
            if line.strip().startswith('"""') and i < 3:
                continue
            
            # Collect dataclasses
            if "@dataclass" in line or "class " in line:
                # Collect the full class/dataclass
                j = i
                class_lines = []
                indent = len(line) - len(line.lstrip())
                while j < len(lines):
                    class_lines.append(lines[j])
                    if j < len(lines) - 1:
                        next_line = lines[j + 1]
                        if next_line.strip() and not next_line.strip().startswith("#") and len(next_line) - len(next_line.lstrip()) <= indent:
                            if not next_line.strip().startswith("@"):
                                break
                    j += 1
                sections["dataclasses"].extend(class_lines)
                sections["dataclasses"].append("")
                continue
            
            # Collect functions (everything else)
            if line.strip() and not line.strip().startswith("#"):
                sections["functions"].append(line)
    
    # Write combined file
    output = []
    
    # Header
    output.append('"""Combined portfolio management module for IVPA."""')
    output.append("")
    output.append("from __future__ import annotations")
    output.append("")
    
    # Imports (sorted and deduplicated)
    sorted_imports = sorted(sections["imports"])
    output.extend(sorted_imports)
    output.append("")
    
    # Dataclasses (remove duplicates by name)
    seen_dataclasses = set()
    for line in sections["dataclasses"]:
        if line.strip().startswith("class "):
            class_name = line.split("(")[0].replace("class ", "").strip()
            if class_name in seen_dataclasses:
                continue
            seen_dataclasses.add(class_name)
        output.append(line)
    
    output.append("")
    output.append("# " + "=" * 70)
    output.append("# INGESTION")
    output.append("# " + "=" * 70)
    output.append("")
    
    # Functions from ingestion
    ingestion_funcs = extract_functions_from_file(SRC_DIR / "portfolio_ingestion.py")
    output.extend(ingestion_funcs)
    
    output.append("")
    output.append("# " + "=" * 70)
    output.append("# ENRICHMENT")
    output.append("# " + "=" * 70)
    output.append("")
    
    # Functions from enrichment
    enrichment_funcs = extract_functions_from_file(SRC_DIR / "portfolio_enrichment.py")
    output.extend(enrichment_funcs)
    
    output.append("")
    output.append("# " + "=" * 70)
    output.append("# CALCULATIONS")
    output.append("# " + "=" * 70)
    output.append("")
    
    # Functions from calculations
    calc_funcs = extract_functions_from_file(SRC_DIR / "portfolio_calculations.py")
    output.extend(calc_funcs)
    
    output.append("")
    output.append("# " + "=" * 70)
    output.append("# EXPOSURE")
    output.append("# " + "=" * 70)
    output.append("")
    
    # Functions from exposure
    exposure_funcs = extract_functions_from_file(SRC_DIR / "portfolio_exposure.py")
    output.extend(exposure_funcs)
    
    output.append("")
    output.append("# " + "=" * 70)
    output.append("# OPTIMIZER")
    output.append("# " + "=" * 70)
    output.append("")
    
    # Functions from optimizer
    optimizer_funcs = extract_functions_from_file(SRC_DIR / "portfolio_optimizer.py")
    output.extend(optimizer_funcs)
    
    output.append("")
    output.append("# " + "=" * 70)
    output.append("# ATTRIBUTION")
    output.append("# " + "=" * 70)
    output.append("")
    
    # Functions from attribution
    attribution_funcs = extract_functions_from_file(SRC_DIR / "portfolio_attribution.py")
    output.extend(attribution_funcs)
    
    output.append("")
    output.append("# " + "=" * 70)
    output.append("# SCENARIOS")
    output.append("# " + "=" * 70)
    output.append("")
    
    # Functions from scenarios
    scenario_funcs = extract_functions_from_file(SRC_DIR / "portfolio_scenarios.py")
    output.extend(scenario_funcs)
    
    output.append("")
    output.append("# " + "=" * 70)
    output.append("# REPORTING")
    output.append("# " + "=" * 70)
    output.append("")
    
    # Functions from reporting
    reporting_funcs = extract_functions_from_file(SRC_DIR / "portfolio_reporting.py")
    output.extend(reporting_funcs)
    
    # Fix internal imports
    combined_content = "\n".join(output)
    
    # Replace internal portfolio imports with empty (same file)
    combined_content = re.sub(r'from \.portfolio_\w+ import \w+\n', '', combined_content)
    combined_content = re.sub(r'from \.portfolio_\w+ import \([\s\S]*?\)\n', '', combined_content)
    
    # Write output
    output_path = SRC_DIR / "portfolio.py"
    output_path.write_text(combined_content, encoding="utf-8")
    print(f"Created {output_path}")
    print(f"Total lines: {len(combined_content.splitlines())}")

def extract_functions_from_file(filepath):
    """Extract all functions and classes from a file."""
    if not filepath.exists():
        return []
    
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines()
    
    # Skip imports and docstrings at the top
    skip_count = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("import ") or line.strip().startswith("from "):
            skip_count = i + 1
        elif line.strip().startswith('"""') and i < 5:
            continue
        elif line.strip() and not line.strip().startswith("#"):
            break
    
    return lines[skip_count:]

if __name__ == "__main__":
    combine_files()


