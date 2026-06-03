from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List

KEYWORDS_PATH = Path(__file__).resolve().parent / "data" / "tag_keywords.json"
DB_PATH = Path(__file__).resolve().parent / "instance" / "recipes.sqlite3"


def load_keywords(path: Path) -> Dict[str, Dict[str, List[str]]]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def normalize_text(s: str) -> str:
    return s.lower()


def ensure_tag(conn: sqlite3.Connection, tag_name: str) -> int:
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
    if row:
        return int(row[0])
    cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
    return int(cur.lastrowid)


def complexity_label(score: int) -> str:
    if score < 1100:
        return "easy"
    if score < 2600:
        return "medium"
    return "hard"


def upsert_recipe_tag(conn: sqlite3.Connection, recipe_id: int, tag_id: int) -> None:
    exists = conn.execute(
        "SELECT 1 FROM recipe_tags WHERE recipe_id = ? AND tag_id = ?",
        (recipe_id, tag_id),
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)",
            (recipe_id, tag_id),
        )


def assign_tags(db_path: Path, keywords_path: Path) -> None:
    kw = load_keywords(keywords_path)
    with sqlite3.connect(db_path, timeout=60) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 60000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("BEGIN")
        # remove old source:* tags and links; they are internal metadata, not user-facing tags
        conn.execute("DELETE FROM recipe_tags WHERE tag_id IN (SELECT id FROM tags WHERE name LIKE 'source:%')")
        conn.execute("DELETE FROM tags WHERE name LIKE 'source:%'")

        # prebuild tag ids
        tag_ids: Dict[str, int] = {}
        for tag in kw.keys():
            tag_ids[tag] = ensure_tag(conn, tag)

        complexity_tags = {name: ensure_tag(conn, name) for name in ("easy", "medium", "hard")}

        # iterate recipes
        rows = conn.execute("SELECT id, title, directions FROM recipes").fetchall()
        for r in rows:
            recipe_id = int(r[0])
            title = normalize_text(str(r[1] or ""))
            directions = normalize_text(str(r[2] or ""))
            # gather ingredient names for this recipe
            ing_rows = conn.execute(
                "SELECT i.name FROM recipe_ingredients ri JOIN ingredients i ON ri.ingredient_id = i.id WHERE ri.recipe_id = ?",
                (recipe_id,),
            ).fetchall()
            ingredients = ", ".join([normalize_text(ir[0]) for ir in ing_rows])

            text_blob = " ".join([title, directions, ingredients])
            complexity_score = len(directions) + (len(ingredients) * 2)
            label = complexity_label(complexity_score)
            upsert_recipe_tag(conn, recipe_id, complexity_tags[label])

            for tag, rules in kw.items():
                included = False
                # if any include keyword present and no exclude keyword present -> assign
                inc = rules.get("include", [])
                exc = rules.get("exclude", [])
                if any(k in text_blob for k in inc) and not any(k in text_blob for k in exc):
                    included = True
                else:
                    # if no explicit include keywords, apply negative rule: assign if no excludes
                    if not inc and not any(k in text_blob for k in exc):
                        included = True
                if included:
                    upsert_recipe_tag(conn, recipe_id, tag_ids[tag])
        conn.execute("COMMIT")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Assign tags to recipes using keyword heuristics")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to SQLite database")
    parser.add_argument("--keywords", default=str(KEYWORDS_PATH), help="Path to tag keywords JSON")
    args = parser.parse_args()

    assign_tags(Path(args.db), Path(args.keywords))
