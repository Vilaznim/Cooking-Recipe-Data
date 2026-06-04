
# Project-cooking-recipe

A cooking recipe web app built for the DIS project. Uses a local SQLite database built from the [RecipeNLG dataset on Kaggle](https://www.kaggle.com/datasets/paultimothymooney/recipenlg).

---
## Authors

| Name | KU username |
|---|---|
| Sonil Jamshidi | zgh982 |
| William Bruun | tnc885 |
| Zaigham S. U. Rahman | kxg471 |

---

## Project structure

```text
Project-cooking-recipe/
    app.py
    assign_tags.py
    import_csv.py
    schema.sql
    requirements.txt
    README.md
    .gitignore
    data/
        tag_keywords.json
    instance/
        recipes.sqlite3
    docs/
    Recipes/
    static/
    templates/
```

---

## What the app does

- Lists recipes from a local SQLite database.
- Shows a recipe detail page with ingredients and tags.
- Uses SQL queries for reading and inserting data.
- Uses Python regular expressions in the search route.
- Supports automatic keyword-based tag assignment (vegan, vegetarian, gluten-free, etc.).

---

## First-time setup

Follow these steps if you are running the project for the first time.

### 1. Check that Python is installed

```bash
python --version
```

If Python is not found, download and install it from https://www.python.org/downloads/.  
**Windows:** make sure to tick **Add Python to PATH** during installation.

### 2. Download the dataset

The dataset is too large to include in the repository and must be downloaded separately.

**Option A — manual download (always works):**

1. Go to https://www.kaggle.com/datasets/paultimothymooney/recipenlg
2. Click **Download** (requires a free Kaggle account).
3. Unzip the file and place `RecipeNLG_dataset.csv` inside the `Recipes/` folder so the path is:
   ```
   Project-cooking-recipe/Recipes/RecipeNLG_dataset.csv
   ```

**Option B — automatic download with `kagglehub`:**

This downloads the file for you, but requires a Kaggle API token set up on your machine first:

1. Log in at https://www.kaggle.com → go to **Settings → API → Create New Token**.
2. Place the downloaded `kaggle.json` file at:
   - **macOS/Linux:** `~/.kaggle/kaggle.json`
   - **Windows:** `C:\Users\<YourName>\.kaggle\kaggle.json`
3. Then run:
   ```bash
   python -c "import kagglehub; path = kagglehub.dataset_download('paultimothymooney/recipenlg'); print('Downloaded to:', path)"
   ```
4. Copy the resulting `RecipeNLG_dataset.csv` into the `Recipes/` folder.

### 3. Create and activate a virtual environment

```bash
python -m venv .venv
```

**Activate it:**

| Platform | Command |
|----------|---------|
| macOS / Linux | `source .venv/bin/activate` |
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Windows CMD | `.venv\Scripts\activate.bat` |

> **Windows note:** if PowerShell blocks the activation script, run this once and then try again:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### 4. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Build the database

This only needs to be done once. It imports the full CSV into SQLite, which may take a few minutes.

```bash
flask --app app init-db
flask --app app import-csv
```

### 6. (Optional) Assign tags

Run this after importing the CSV to auto-label recipes with tags like vegan, vegetarian, and gluten-free. Edit `data/tag_keywords.json` to adjust keyword lists before running.

```bash
python assign_tags.py --db instance/recipes.sqlite3 --keywords data/tag_keywords.json
```

### 7. Start the app

```bash
flask --app app run
```

Open the address shown in the terminal, usually **http://127.0.0.1:5000**.

---

## Opening the project in VS Code (Windows)

1. Open VS Code and use **File → Open Folder** to open the project folder, e.g.:
   ```
   C:\Users\sonil\OneDrive\Skrivebord\2. år\blok 4\DIS\Project-cooking-recipe
   ```
2. Open the terminal with **Terminal → New Terminal** and follow the steps above.

---

## Quick start — if you have already set up the project once

If the database already exists at `instance/recipes.sqlite3`, just activate your virtual environment and start the app:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
flask --app app run
```

Then open **http://127.0.0.1:5000**.

### Reset everything from scratch

If you want to wipe and rebuild the database:

```bash
flask --app app init-db
flask --app app import-csv
flask --app app run
```
---
## Testing guide

### Search and regex
| What to type in search | Expected result |
|---|---|
| `chicken` | Recipes containing chicken |
| `chick.n` | Same results — regex dot matches any character |
| `^Chocolate` | Recipes whose title starts with "Chocolate" |
| `(pasta\|rice)` | Recipes containing either pasta or rice |

### Tags
| Action | Expected result |
|---|---|
| Search `pasta`, filter by **easy** | Only easy pasta recipes |
| Search `pasta`, filter by **vegetarian** | Only vegetarian friendly pasta recipes, no meat-based results |
| Search `pasta`, filter by **vegan** | Only vegan pasta recipes |
---

## AI-deklaration

> *Københavns Universitet — Version 1*
> Deklaration for anvendelse af generative AI-værktøjer (studerende)

- [x] Jeg/vi har **benyttet** generativ AI som hjælpemiddel/værktøj
- [ ] Jeg/vi har **IKKE** benyttet generativ AI som hjælpemiddel/værktøj

*Hvis brug af generativ AI er tilladt til eksamen, men du ikke har benyttet det i din opgave, skal du blot krydse af at du ikke har brugt GAI og behøver ikke at udfylde resten.*

---

### Anvendte GAI-værktøjer

| Værktøj | Link |
|---------|------|
| Claude | https://claude.ai/new |
| Claude | VS Code copilot |

---

### Beskrivelse af anvendelse

**Formål** — hvad har du/I brugt værktøjet til?

> Det er blevet brugt som støtte til at give ideer og troubleshoot vores kode når der er problemer. Den er eg. blevet brugt til at opsætte en pænere readme fil, og gøre vores andre filer pænere og mere læsbar for brugere.

**Arbejdsfase** — hvornår i arbejdsprocessen har du/I brugt GAI?

> I starten, for at hjælpe med opsætning, under for troubleshooting og og problemløsning, og til sidst for at tjekke om vi opfylder alle krav sat til os og om vi har manglet noget, samt gøre det hele pænt og let at læse

**Output** — hvad gjorde du/I med outputtet (inkl. om det er redigeret og arbejdet videre med)?

> Kode, ideer osv er alt blevet redigeret og arbejdet videre med selv, der er intet der er blevet givet der er sat direkte ind i koden uden grundig gennemgang og redigering, så vi kan få fuld forståelse.

---

*NB: GAI-genereret indhold brugt som kilde i opgaven kræver korrekt brug af citationstegn og kildehenvisning.*