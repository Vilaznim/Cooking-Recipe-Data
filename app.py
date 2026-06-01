from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, abort, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "recipes.sqlite3"
SCHEMA_PATH = BASE_DIR / "schema.sql"

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
    with sqlite3.connect(DATABASE_PATH) as db:
        db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


@app.cli.command("init-db")
def init_db_command() -> None:
    init_db()
    print("Initialized the database.")


@app.route("/")
def index() -> str:
    db = get_db()
    recipes = db.execute(
        "SELECT id, title, directions, link FROM recipes ORDER BY id DESC"
    ).fetchall()
    return render_template("index.html", recipes=recipes)


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
        return render_template("search.html", query=query, matches=[])

    db = get_db()
    recipes = db.execute(
        "SELECT id, title, directions, link FROM recipes ORDER BY id DESC"
    ).fetchall()

    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    matches = [
        recipe
        for recipe in recipes
        if pattern.search(recipe["title"]) or pattern.search(recipe["directions"])
    ]
    return render_template("search.html", query=query, matches=matches)


@app.route("/seed")
def seed_demo_data() -> Any:
    db = get_db()
    db.execute(
        "INSERT INTO recipes (title, directions, link) VALUES (?, ?, ?)",
        (
            "Simple Tomato Pasta",
            "Boil pasta, warm sauce, and combine.",
            "https://example.com/pasta",
        ),
    )
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
