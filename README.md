# Project-cooking-recipe

Project-cooking-recipe is a cooking recipe web app for the DIS project.

## Project structure

```text
Project-cooking-recipe/
	app.py
	schema.sql
	instance/recipes.sqlite3
	import_csv.py
	requirements.txt
	README.md
	.gitignore
	docs/
	Recipes/
	static/
	templates/
```

## How to run

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Start the app with `flask --app app run`.
4. Open the site in your browser.

The app uses a local SQLite database at `instance/recipes.sqlite3`.

If the database already exists on your computer, startup is fast because the app reuses it.

If the database does not exist yet, the first setup on your machine must build it from the CSV. That takes longer, but only happens once. Use these commands for a first-time rebuild:

1. `flask --app app init-db`
2. `flask --app app import-csv`
3. `flask --app app run`


## Windows quick start

Use the integrated VS Code terminal or Windows PowerShell.

1. Open the project folder in VS Code which could look like: `c:\Users\sonil\OneDrive\Skrivebord\2. år\blok 4\DIS\Project-cooking-recipe`.
2. Open the terminal in VS Code with `Terminal > New Terminal`, or open PowerShell from the Start menu.
3. Make sure Python is installed:
	- Run `python --version`.
	- If that says Python is not found, install Python from https://www.python.org/downloads/ and make sure you tick the checkbox for `Add Python to PATH`.
4. Go into the project folder in the terminal if you are not already there:
	- `cd "c:\Users\sonil\OneDrive\Skrivebord\2. år\blok 4\DIS\Project-cooking-recipe"`
5. Create a virtual environment:
	- `python -m venv .venv`
6. Activate it:
	- PowerShell: `.\.venv\Scripts\Activate.ps1`
	- If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.
7. Install the packages:
	- `python -m pip install --upgrade pip`
	- `pip install -r requirements.txt`
8. Start the program:
	- `flask --app app run`
9. Open the address shown in the terminal, usually `http://127.0.0.1:5000`.

If `pip` is missing, use `python -m pip ...` instead.

If Flask is missing, the `pip install -r requirements.txt` step installs it.

If the database file is missing, use the rebuild steps above or run `flask --app app init-db` followed by `flask --app app import-csv`.

The first rebuild can take a while because it imports the full CSV into SQLite. After that, normal runs are much faster because the app reads from the local database instead of the raw CSV.

If you want to reset everything, run `flask --app app init-db` before starting the app again.

## What the app does

- Lists recipes from SQLite.
- Shows a recipe detail page with ingredients and tags.
- Uses SQL queries for reading and inserting data.
- Uses Python regular expressions in the search route.



## AI declaration

