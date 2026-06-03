DROP TABLE IF EXISTS import_meta;
DROP TABLE IF EXISTS recipes_fts;
DROP TABLE IF EXISTS recipe_tags;
DROP TABLE IF EXISTS recipe_ingredients;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS ingredients;
DROP TABLE IF EXISTS recipes;

CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL UNIQUE,
    title TEXT NOT NULL,
    directions TEXT NOT NULL,
    link TEXT
);

CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE recipe_ingredients (
    recipe_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantity TEXT,
    PRIMARY KEY (recipe_id, ingredient_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
);

CREATE TABLE recipe_tags (
    recipe_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (recipe_id, tag_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE import_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Full-text search virtual table for fast recipe title/directions lookup
-- Full-text search virtual table for fast recipe title/directions/ingredients lookup
CREATE VIRTUAL TABLE IF NOT EXISTS recipes_fts USING fts5(
    title,
    directions,
    ingredients
);
