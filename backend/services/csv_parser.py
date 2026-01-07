from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple


def _open_csv_file(csv_path: Path):
    """Try multiple encodings to open CSV file."""
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]
    for enc in encodings:
        try:
            f = csv_path.open("r", encoding=enc)
            content = f.read(4096)
            f.seek(0)
            return f, enc, content
        except (UnicodeDecodeError, UnicodeError):
            try:
                f.close()
            except:
                pass
            continue
    raise ValueError(f"Cannot decode CSV file with encodings: {encodings}")


def _detect_delimiter(sample: str) -> str:
    """Detect CSV delimiter from sample content."""
    first_line = sample.split("\n")[0]
    tab_count = first_line.count("\t")
    comma_count = first_line.count(",")
    if tab_count > comma_count:
        return "\t"
    return ","


def extract_users(csv_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Extract users from CSV file.

    Returns:
        Tuple of (handles, user_rows) where:
        - handles: list of Handle values for counting
        - user_rows: list of full row dicts for passing to Grok
    """
    f, enc, sample = _open_csv_file(csv_path)
    delimiter = _detect_delimiter(sample)

    try:
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("CSV missing header row")

        # Normalize field names (strip BOM, whitespace)
        clean_fields = {}
        for name in reader.fieldnames:
            clean_name = name.strip().lstrip('\ufeff')
            clean_fields[clean_name.lower()] = clean_name

        handle_key = None
        for possible_key in ["handle", "username", "screen_name"]:
            if possible_key in clean_fields:
                handle_key = clean_fields[possible_key]
                break

        if not handle_key:
            available = list(clean_fields.keys())
            raise ValueError(f"CSV missing required column: Handle or username. Found columns: {available}")

        user_rows = []
        handles = []
        for row in reader:
            # Also clean row keys
            clean_row = {k.strip().lstrip('\ufeff'): v for k, v in row.items() if k}
            handle = (clean_row.get(handle_key) or "").strip()
            if handle:
                handles.append(handle)
                user_rows.append(clean_row)

        if not handles:
            raise ValueError("No users found in CSV")

        return handles, user_rows
    finally:
        f.close()


def format_user_info(row: Dict[str, str]) -> str:
    """Format a user row as readable text for Grok prompt."""
    parts = []
    key_fields = ["Handle", "Name", "Bio", "Location", "FollowersCount", "FollowingCount"]

    for field in key_fields:
        value = row.get(field, "").strip()
        if value:
            parts.append(f"{field}: {value}")

    return " | ".join(parts) if parts else str(row)
