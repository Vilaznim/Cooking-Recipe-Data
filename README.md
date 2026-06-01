# Project-cooking-recipe

Project-cooking-recipe is a cooking recipe web app for the DIS project.

## Project structure

```text
Project-cooking-recipe/
	app.py
	schema.sql
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
3. Initialize the database with `flask --app app init-db`.
4. Start the app with `flask --app app run`.

## Windows quick start

Use the integrated VS Code terminal or Windows PowerShell.

1. Open the project folder in VS Code: `c:\Users\sonil\OneDrive\Skrivebord\2. år\blok 4\DIS\Project-cooking-recipe`.
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
8. Initialize the database:
	- `flask --app app init-db`
9. Start the program:
	- `flask --app app run`
10. Open the address shown in the terminal, usually `http://127.0.0.1:5000`.

If `pip` is missing, use `python -m pip ...` instead.

If Flask is missing, the `pip install -r requirements.txt` step installs it.

If the database file is missing, rerun `flask --app app init-db`.

## What the app does

- Lists recipes from SQLite.
- Shows a recipe detail page with ingredients and tags.
- Uses SQL queries for reading and inserting data.
- Uses Python regular expressions in the search route.



## AI declaration

