# Wagtail in Production: companion project

*Studio* is the example site from the book *Wagtail in Production: Building, Extending and Running Wagtail 8 Sites* (Foxy Press). Every code listing in the book comes from this project, and every chapter's code has tests.

This repository holds the finished project, with the code and tests from all chapters.

## Requirements

- Python 3.11 or later
- Wagtail 8.0 and Django 5.2 (pinned in `requirements.txt`)
- Node 24, only for the headless front-end build (chapter 7)

## Run it

```bash
git clone https://github.com/foxy-press/wagtail-in-production.git
cd wagtail-in-production
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_site
python manage.py createsuperuser
python manage.py runserver
```

The site is at `http://localhost:8000/` and the admin at `http://localhost:8000/studio-admin/`.

Development uses SQLite. Set `POSTGRES_DB` (and `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`) to use PostgreSQL instead.

## Run the tests

```bash
python manage.py test
```

Set `STRICT_DEPRECATIONS=1` to turn Wagtail deprecation warnings into errors, as CI does. CI runs the suite on PostgreSQL with Python 3.12 and 3.13 (`.github/workflows/tests.yml`).

## Run it with Docker

```bash
SECRET_KEY=change-me docker compose up --build
```

This runs the site on PostgreSQL with `DEBUG` off, as in production (chapter 15).

## Where things are

| Path | Contents |
| --- | --- |
| `core/` | Shared models, StreamField blocks, admin extensions, search, SEO, AI review and management commands |
| `pages/` | Home, service and legal pages, enquiries and newsletter sign-ups |
| `blog/` | Blog pages and the legacy HTML importer |
| `config/` | Settings, URLs and the read-only API that the front end uses |
| `templates/` | Page and block templates |
| `frontend/` | A dependency-free static front end built from the Wagtail API (chapter 7) |
| `deploy/` | Apache, systemd and cron files for a server deploy (chapter 15) |

The AI review command (chapter 12) calls the Claude API and needs `ANTHROPIC_API_KEY` in the environment. Its tests do not.
