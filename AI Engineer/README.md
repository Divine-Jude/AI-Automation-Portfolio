# AW Client Report Portal

Internal demo portal: **client profiles**, **quarterly balance entry** with live SACS/TCC math, and **WeasyPrint PDFs** (SACS + TCC).

## Stack

- Python 3.11+ · Flask · SQLite (`instance/app.db`)
- Tailwind (CDN) · HTMX · vanilla JS
- WeasyPrint (HTML/CSS → PDF)
- Railway via Dockerfile

## Run locally

```bash
cd "AI Engineer"
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**WeasyPrint system libraries (macOS):**

```bash
brew install pango cairo gdk-pixbuf libffi
```

**Start the app:**

```bash
export FLASK_APP=app.py
flask run --debug
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). A **sample married couple** is seeded with **$15,000** inflow and **$11,000** outflow (plus retirement / trust / liability demo figures).

## One-click Railway deploy

1. Push this folder to a **new GitHub repository** (repository root = this project root containing `Dockerfile` and `railway.toml`).
2. In [Railway](https://railway.app): **New Project** → **Deploy from GitHub** → select the repo.
3. Railway detects `railway.toml` and builds with the **Dockerfile** (includes WeasyPrint OS dependencies).
4. After deploy, open the generated **public URL**.

**Optional:** Add a **volume** mounted at `/app/instance` if you need the SQLite file to persist across deploys (ephemeral disk otherwise).

**Environment variables (optional):**


| Variable       | Purpose                                         |
| -------------- | ----------------------------------------------- |
| `SECRET_KEY`   | Flask session/signing (set in production)       |
| `DATABASE_URL` | Override DB URI (defaults to `instance/app.db`) |


## Project layout


| Path                                               | Role                                               |
| -------------------------------------------------- | -------------------------------------------------- |
| `app.py`                                           | Flask app, routes, seed data                       |
| `models.py` / `database.py`                        | SQLAlchemy models                                  |
| `calculations.py`                                  | SACS/TCC rules (mirrored in `static/js/report.js`) |
| `templates/`                                       | Jinja UI + WeasyPrint HTML                         |
| `static/js/report.js`                              | Dynamic rows, live totals, HTMX preview            |
| `requirements.txt` / `Dockerfile` / `railway.toml` | Deploy                                             |


## Business rules (demo)

- **Excess** = Inflow − Outflow  
- **Private reserve target** = 6 × agreed monthly expense budget + **$5,000** insurance deductibles (demo constant)  
- **Grand total net worth** = Client 1 retirement + Client 2 retirement + non-retirement + trust (Zillow) — **liabilities are listed separately and not subtracted**

## Out of scope (by design)

No authentication, report history/versioning, Canva, or Zillow API — PDFs and forms use **manual** trust value entry.