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
    db = get_db()
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    per_page = 15
    offset = (page - 1) * per_page

    total = db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    total_pages = math.ceil(total / per_page) if total else 1

    rows = db.execute(
        "SELECT id, title FROM recipes ORDER BY id DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()

    recipes = []
    for r in rows:
        ing_rows = db.execute(
            "SELECT i.name FROM recipe_ingredients AS ri JOIN ingredients AS i ON i.id = ri.ingredient_id WHERE ri.recipe_id = ? ORDER BY i.name",
            (r[0],),
        ).fetchall()
        ingredients = [ir[0] for ir in ing_rows]
        recipes.append({"id": r[0], "title": r[1], "ingredients": ingredients})

    return render_template("index.html", recipes=recipes, page=page, total_pages=total_pages)


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
        ORDER BY t.name
        """,
        (recipe_id,),
    ).fetchall()
    return render_template(
        "recipe_detail.html", recipe=recipe, ingredients=ingredients, tags=tags
    )


@app.route("/search")
def search() -> str:
    query = request.args.get("q", "").strip()
    if not query:
        return render_template("search.html", query=query, matches=[], page=1, total_pages=1)

    db = get_db()
    # Pagination params
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    per_page = 15
    offset = (page - 1) * per_page

    # Prefer FTS5 search for performance; fall back to regex scanning if unavailable or errors
    try:
        total = db.execute("SELECT COUNT(*) FROM recipes_fts WHERE recipes_fts MATCH ?", (query,)).fetchone()[0]
        total_pages = math.ceil(total / per_page) if total else 1

        rows = db.execute(
            "SELECT rowid, title FROM recipes_fts WHERE recipes_fts MATCH ? ORDER BY rowid DESC LIMIT ? OFFSET ?",
            (query, per_page, offset),
        ).fetchall()

        matches = []
        for r in rows:
            recipe_id = r[0]
            title = r[1]
            ing_rows = db.execute(
                "SELECT i.name FROM recipe_ingredients AS ri JOIN ingredients AS i ON i.id = ri.ingredient_id WHERE ri.recipe_id = ? ORDER BY i.name",
                (recipe_id,),
            ).fetchall()
            ingredients = [ir[0] for ir in ing_rows]
            matches.append({"id": recipe_id, "title": title, "ingredients": ingredients})

        return render_template(
            "search.html",
            query=query,
            matches=matches,
            page=page,
            total_pages=total_pages,
        )
    except sqlite3.OperationalError:
        # Fallback: previous regex-based scanning (slower, but supports complex patterns)
        rows = db.execute("SELECT id, title, directions FROM recipes ORDER BY id DESC").fetchall()

        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        matched = [r for r in rows if pattern.search(r[1]) or pattern.search(r[2])]

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

        return render_template(
            "search.html",
            query=query,
            matches=matches,
            page=page,
            total_pages=total_pages,
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
