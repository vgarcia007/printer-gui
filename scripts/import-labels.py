#!/usr/bin/env python3
"""Import saved rich-text labels from ai-label-printer without importing AI labels."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


COLUMNS = (
    "user_prompt",
    "template_id",
    "orientation",
    "width_mm",
    "height_mm",
    "png_content",
    "source_type",
    "editor_content",
    "is_saved",
    "created_at",
    "updated_at",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("/home/pi/ai-label-printer/instance/labels.db"))
    parser.add_argument("--target", type=Path, default=Path("data/labels/labels.db"))
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error("Source database does not exist: " + str(args.source))
    if not args.target.is_file():
        parser.error("Target database does not exist. Start the web container once first.")

    backup = args.target.with_name(args.target.name + ".before-import-" + datetime.now().strftime("%Y%m%d%H%M%S"))
    shutil.copy2(args.target, backup)

    source = sqlite3.connect("file:" + str(args.source.resolve()) + "?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    target = sqlite3.connect(args.target)
    try:
        rows = source.execute(
            "SELECT " + ", ".join(COLUMNS) + " FROM labels "
            "WHERE source_type = 'editor' AND is_saved = 1 AND editor_content IS NOT NULL"
        ).fetchall()
        imported = 0
        with target:
            for row in rows:
                duplicate = target.execute(
                    "SELECT 1 FROM labels WHERE source_type = 'editor' "
                    "AND editor_content = ? AND png_content = ? LIMIT 1",
                    (row["editor_content"], row["png_content"]),
                ).fetchone()
                if duplicate:
                    continue
                placeholders = ", ".join("?" for _ in COLUMNS)
                target.execute(
                    "INSERT INTO labels (" + ", ".join(COLUMNS) + ") VALUES (" + placeholders + ")",
                    tuple(row[column] for column in COLUMNS),
                )
                imported += 1
    finally:
        source.close()
        target.close()

    print("Imported " + str(imported) + " saved editor label(s).")
    print("Backup: " + str(backup))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
