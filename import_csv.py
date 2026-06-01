from __future__ import annotations

import ast
import csv
import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(value)
        except (ValueError, SyntaxError, json.JSONDecodeError):
            continue
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [value.strip()] if value.strip() else []


def _file_signature(csv_path: Path) -> str:
    stats = csv_path.stat()
    return f"{stats.st_mtime_ns}:{stats.st_size}"


def _get_meta(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute(
        "SELECT value FROM import_meta WHERE key = ?",
        (key,),
    ).fetchone()
    return None if row is None else str(row[0])


def _set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO import_meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def _load_cache(connection: sqlite3.Connection, table: str) -> dict[str, int]:
    rows = connection.execute(f"SELECT id, name FROM {table}").fetchall()
    return {str(row[1]): int(row[0]) for row in rows}


def _clear_data(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM recipe_tags")
    connection.execute("DELETE FROM recipe_ingredients")
    connection.execute("DELETE FROM recipes")
    connection.execute("DELETE FROM ingredients")
    connection.execute("DELETE FROM tags")
    # clear import metadata and FTS table if present
    connection.execute("DELETE FROM import_meta")
    try:
        connection.execute("DELETE FROM recipes_fts")
    except sqlite3.OperationalError:
        # FTS table might not exist on older DBs - ignore
        pass


def _import_csv_data(connection: sqlite3.Connection, csv_path: Path) -> int:
    ingredient_cache = _load_cache(connection, "ingredients")
    tag_cache = _load_cache(connection, "tags")
    imported_rows = 0

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            source_id = int(row.get("") or row.get("source_id") or imported_rows)
            title = (row.get("title") or "").strip()
            link = (row.get("link") or "").strip() or None
            source = (row.get("source") or "").strip() or "unknown"
            raw_ingredients = _parse_list(row.get("ingredients"))
            directions = _parse_list(row.get("directions"))
            normalized_ingredients = _parse_list(row.get("NER"))

            recipe_cursor = connection.execute(
                "INSERT INTO recipes (source_id, title, directions, link) VALUES (?, ?, ?, ?)",
                (source_id, title, "\n\n".join(directions), link),
            )
            recipe_id = int(recipe_cursor.lastrowid)

            # populate FTS table for fast search (if present)
            try:
                connection.execute(
                    "INSERT INTO recipes_fts(rowid, title, directions) VALUES (?, ?, ?)",
                    (recipe_id, title, "\n\n".join(directions)),
                )
            except sqlite3.OperationalError:
                # FTS table not available on this SQLite build or schema; continue
                pass

            source_tag = f"source:{source}"
            tag_id = tag_cache.get(source_tag)
            if tag_id is None:
                tag_cursor = connection.execute(
                    "INSERT INTO tags (name) VALUES (?)",
                    (source_tag,),
                )
                tag_id = int(tag_cursor.lastrowid)
                tag_cache[source_tag] = tag_id

            connection.execute(
                "INSERT INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)",
                (recipe_id, tag_id),
            )

            max_length = max(len(raw_ingredients), len(normalized_ingredients))
            recipe_ingredients: dict[int, str | None] = {}
            for index in range(max_length):
                ingredient_name = None
                quantity = None

                if index < len(normalized_ingredients):
                    ingredient_name = normalized_ingredients[index]
                if index < len(raw_ingredients):
                    quantity = raw_ingredients[index]

                if not ingredient_name:
                    ingredient_name = quantity or f"ingredient-{index + 1}"

                ingredient_id = ingredient_cache.get(ingredient_name)
                if ingredient_id is None:
                    ingredient_cursor = connection.execute(
                        "INSERT INTO ingredients (name) VALUES (?)",
                        (ingredient_name,),
                    )
                    ingredient_id = int(ingredient_cursor.lastrowid)
                    ingredient_cache[ingredient_name] = ingredient_id

                if ingredient_id in recipe_ingredients:
                    previous_quantity = recipe_ingredients[ingredient_id]
                    if quantity and quantity not in (previous_quantity or ""):
                        if previous_quantity:
                            recipe_ingredients[ingredient_id] = f"{previous_quantity}; {quantity}"
                        else:
                            recipe_ingredients[ingredient_id] = quantity
                    continue

                recipe_ingredients[ingredient_id] = quantity

            for ingredient_id, quantity in recipe_ingredients.items():
                connection.execute(
                    "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                    (recipe_id, ingredient_id, quantity),
                )

            imported_rows += 1

    return imported_rows


def ensure_csv_imported(
    DATABASE_PATH: Path,
    schema_path: Path,
    csv_path: Path,
) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    csv_signature = _file_signature(csv_path)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 600000")

        try:
            connection.execute("SELECT 1 FROM import_meta LIMIT 1")
        except sqlite3.OperationalError:
            connection.executescript(schema_path.read_text(encoding="utf-8"))

        connection.execute("BEGIN IMMEDIATE")
        current_signature = _get_meta(connection, "csv_signature")
        if current_signature == csv_signature:
            connection.execute("COMMIT")
            return

        _clear_data(connection)
        imported_rows = _import_csv_data(connection, csv_path)
        _set_meta(connection, "csv_signature", csv_signature)
        _set_meta(connection, "csv_rows", str(imported_rows))
        connection.execute("COMMIT")
