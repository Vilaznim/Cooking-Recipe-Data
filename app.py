from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any
 
from flask import Flask, abort, g, redirect, render_template, request, url_for

from import_csv import ensure_csv_imported
import math

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "recipes.sqlite3"
SCHEMA_PATH = BASE_DIR / "schema.sql"
CSV_PATH = BASE_DIR / "Recipes" / "RecipeNLG_dataset.csv"

app = Flask(__name__)
app.config.from_mapping(SECRET_KEY="dev")

DIFFICULTY_TAGS = ("easy", "medium", "hard")


def normalize_recipe_link(link: str | None) -> str | None:
    if not link:
        return None

    cleaned_link = link.strip()
    if cleaned_link.startswith(("http://", "https://")):
        return cleaned_link

    return f"https://{cleaned_link}"


def sort_tags(tags: list[str]) -> list[str]:
    return sorted(dict.fromkeys(tags), key=str.casefold)


def split_search_tags(tags: list[str]) -> tuple[list[str], list[str]]:
    normalized_tags = sort_tags(tags)
    difficulty_tags = [tag for tag in DIFFICULTY_TAGS if tag in normalized_tags]
    normal_tags = [tag for tag in normalized_tags if tag not in DIFFICULTY_TAGS]
    return normal_tags, difficulty_tags


def get_search_tag_groups(db: sqlite3.Connection) -> tuple[list[str], list[str]]:
    all_tags = sort_tags([
        t[0]
        for t in db.execute(
            "SELECT name FROM tags WHERE name NOT LIKE 'source:%' ORDER BY name"
        ).fetchall()
    ])
    return split_search_tags(all_tags)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: Exception | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(DATABASE_PATH) as db:
        try:
            db.executescript(schema_text)
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            if "fts5" in msg or "no such module" in msg:
                # Some SQLite builds may not have FTS5 enabled. Remove the FTS block and retry.
                import re as _re

                cleaned = _re.sub(r"-- Full-text search virtual table[\s\S]*$", "", schema_text)
                db.executescript(cleaned)
            else:
                raise


@app.cli.command("init-db")
def init_db_command() -> None:
    init_db()
    print("Initialized the database.")


@app.cli.command("import-csv")
def import_csv_command() -> None:
    ensure_csv_imported(DATABASE_PATH=DATABASE_PATH, schema_path=SCHEMA_PATH, csv_path=CSV_PATH)
    print("Imported CSV data into the database.")


@app.route("/")
def index() -> str:
    return redirect(url_for("search"))


@app.route("/recipes/<int:recipe_id>")
def recipe_detail(recipe_id: int) -> str:
    db = get_db()
    recipe = db.execute(
        "SELECT id, title, directions, link FROM recipes WHERE id = ?",
        (recipe_id,),
    ).fetchone()
    if recipe is None:
        abort(404)

    ingredients = db.execute(
        """
        SELECT i.name, ri.quantity
        FROM recipe_ingredients AS ri
        JOIN ingredients AS i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = ?
        ORDER BY i.name
        """,
        (recipe_id,),
    ).fetchall()
    tags = db.execute(
        """
        SELECT t.name
        FROM recipe_tags AS rt
        JOIN tags AS t ON t.id = rt.tag_id
        WHERE rt.recipe_id = ?
        ORDER BY t.name COLLATE NOCASE
        """,
        (recipe_id,),
    ).fetchall()
    return render_template(
        "recipe_detail.html",
        recipe=recipe,
        ingredients=ingredients,
        tags=tags,
        external_link=normalize_recipe_link(recipe["link"]),
    )


@app.route("/search")
def search() -> str:
    query = request.args.get("q", "").strip()
    if not query:
        # still provide tag list for the empty search page
        db = get_db()
        normal_tags, difficulty_tags = get_search_tag_groups(db)
        return render_template(
            "search.html",
            query=query,
            matches=[],
            page=1,
            total_pages=1,
            normal_tags=normal_tags,
            difficulty_tags=difficulty_tags,
            selected_tags=[],
            selected_normal_tags=[],
            selected_difficulty_tags=[],
        )

    db = get_db()
    # Pagination params
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    per_page = 15
    offset = (page - 1) * per_page

    # collect selected tags (support repeated ?tag=x or comma-separated ?tags=a,b)
    selected_tags = request.args.getlist("tag") or []
    if not selected_tags:
        tags_param = request.args.get("tags") or ""
        if tags_param:
            selected_tags = [t.strip() for t in tags_param.split(",") if t.strip()]
    selected_tags = sort_tags(selected_tags)
    selected_normal_tags, selected_difficulty_tags = split_search_tags(selected_tags)

    # Prefer FTS5 search for performance; fall back to regex scanning if unavailable or errors
    try:
        # fetch all FTS matches first so we can apply tag-filters, then paginate in Python
        rows_all = db.execute(
            "SELECT rowid, title FROM recipes_fts WHERE recipes_fts MATCH ? ORDER BY rowid DESC",
            (query,),
        ).fetchall()

        # if tags selected, compute allowed recipe_ids that have all selected tags
        allowed_ids = None
        if selected_tags:
            placeholders = ",".join("?" for _ in selected_tags)
            sql = (
                "SELECT recipe_id FROM recipe_tags rt JOIN tags t ON rt.tag_id = t.id "
                f"WHERE t.name IN ({placeholders}) GROUP BY recipe_id HAVING COUNT(DISTINCT t.name) = ?"
            )
            params = tuple(selected_tags) + (len(selected_tags),)
            id_rows = db.execute(sql, params).fetchall()
            allowed_ids = {r[0] for r in id_rows}

        filtered = [r for r in rows_all if (allowed_ids is None or r[0] in allowed_ids)]

        total = len(filtered)
        total_pages = math.ceil(total / per_page) if total else 1

        page_rows = filtered[offset: offset + per_page]

        matches = []
        for r in page_rows:
            recipe_id = r[0]
            title = r[1]
            ing_rows = db.execute(
                "SELECT i.name FROM recipe_ingredients AS ri JOIN ingredients AS i ON i.id = ri.ingredient_id WHERE ri.recipe_id = ? ORDER BY i.name",
                (recipe_id,),
            ).fetchall()
            ingredients = [ir[0] for ir in ing_rows]
            matches.append({"id": recipe_id, "title": title, "ingredients": ingredients})

        normal_tags, difficulty_tags = get_search_tag_groups(db)

        return render_template(
            "search.html",
            query=query,
            matches=matches,
            page=page,
            total_pages=total_pages,
            normal_tags=normal_tags,
            difficulty_tags=difficulty_tags,
            selected_tags=selected_tags,
            selected_normal_tags=selected_normal_tags,
            selected_difficulty_tags=selected_difficulty_tags,
        )
    except sqlite3.OperationalError:
        # Fallback: previous regex-based scanning (slower, but supports complex patterns)
        rows = db.execute("SELECT id, title, directions FROM recipes ORDER BY id DESC").fetchall()

        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        matched = [r for r in rows if pattern.search(r[1]) or pattern.search(r[2])]

        # apply tag filter if requested
        if selected_tags:
            placeholders = ",".join("?" for _ in selected_tags)
            sql = (
                "SELECT recipe_id FROM recipe_tags rt JOIN tags t ON rt.tag_id = t.id "
                f"WHERE t.name IN ({placeholders}) GROUP BY recipe_id HAVING COUNT(DISTINCT t.name) = ?"
            )
            params = tuple(selected_tags) + (len(selected_tags),)
            id_rows = db.execute(sql, params).fetchall()
            allowed_ids = {r[0] for r in id_rows}
            matched = [r for r in matched if r[0] in allowed_ids]

        total = len(matched)
        total_pages = math.ceil(total / per_page) if total else 1
        start = (page - 1) * per_page
        end = start + per_page
        page_rows = matched[start:end]

        matches = []
        for r in page_rows:
            ing_rows = db.execute(
                "SELECT i.name FROM recipe_ingredients AS ri JOIN ingredients AS i ON i.id = ri.ingredient_id WHERE ri.recipe_id = ? ORDER BY i.name",
                (r[0],),
            ).fetchall()
            ingredients = [ir[0] for ir in ing_rows]
            matches.append({"id": r[0], "title": r[1], "ingredients": ingredients})

        normal_tags, difficulty_tags = get_search_tag_groups(db)

        return render_template(
            "search.html",
            query=query,
            matches=matches,
            page=page,
            total_pages=total_pages,
            normal_tags=normal_tags,
            difficulty_tags=difficulty_tags,
            selected_tags=selected_tags,
            selected_normal_tags=selected_normal_tags,
            selected_difficulty_tags=selected_difficulty_tags,
        )


@app.route("/seed")
def seed_demo_data() -> Any:
    db = get_db()
    next_source_id = db.execute(
        "SELECT COALESCE(MAX(source_id), 0) + 1 FROM recipes"
    ).fetchone()[0]
    db.execute(
        "INSERT INTO recipes (source_id, title, directions, link) VALUES (?, ?, ?, ?)",
        (
            int(next_source_id),
            "Simple Tomato Pasta",
            "Boil pasta, warm sauce, and combine.",
            "https://example.com/pasta",
        ),
    )
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
