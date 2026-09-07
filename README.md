# ZionBoutique — Business Manager

Flask backend for the ZionBoutique retail system, using Google Sheets as
the database (no paid DB required) and real server-side authentication
with role-based access control.

## Project structure

```
zionboutique/
├── app.py              # main Flask app — routes for products/customers/orders/staff/reports
├── auth.py             # login/logout/session, login_required & role_required decorators
├── config.py           # env-var driven settings (credentials, sheet id, secret key, tax rate)
├── schema.py            # column headers for each Sheets tab
├── sheets_db.py        # generic get/find/insert/update/delete over Google Sheets
├── init_sheets.py       # one-time script: creates tabs with headers
├── seed_admin.py         # one-time script: creates the first admin login
├── example_routes.py     # reference only — not imported by app.py
├── api/
│   └── index.py         # Vercel serverless entrypoint (re-exports app.py's Flask app)
├── vercel.json           # Vercel build/route config
├── templates/
│   └── index.html       # the frontend (login + dashboard), calls the API with fetch
├── requirements.txt
├── Procfile              # `web: gunicorn app:app` — used by Render/Railway, not Vercel
├── .env.example           # copy to .env locally; never commit the real .env
└── .gitignore
```

## Google Sign-In (staff + customer)

Two separate flows, both new in `google_auth.py`:

- **Staff/Admin** — the "Sign in with Google" button on the Staff/Admin
  tab only works for an email that's already a row in the Users tab.
  It's an alternate way to log in to an existing account, never a way
  to create one — nobody can grant themselves staff or admin access
  just by having a Google account.
- **Customer** — the Customer tab's "Continue with Google" button is
  genuinely self-service: if the email isn't already a Customer, one
  is created automatically, then the person is dropped into a minimal
  read-only portal (`/customer`) showing their own order history —
  never the business dashboard.

This needs a second, separate set of Google Cloud credentials from the
Sheets service account — an **OAuth Client ID**, not a service account:

1. In the same (or a new) Google Cloud project → APIs & Services →
   OAuth consent screen → set it up (External is fine for a small
   boutique; add your own email as a test user while it's not verified).
2. APIs & Services → Credentials → Create Credentials → **OAuth client ID**
   → Application type: Web application.
3. Under **Authorized redirect URIs**, add:
   - `http://localhost:5000/auth/google/callback` (local dev)
   - `https://<your-production-domain>/auth/google/callback` (Vercel,
     e.g. `https://bethel-boutique.vercel.app/auth/google/callback`)
4. Copy the generated **Client ID** and **Client Secret**.
5. Set as environment variables (locally in `.env`, on Vercel in the
   dashboard): `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`.

One schema change: the Users and Customers tabs now have a `google_id`
column. If you already ran `init_sheets.py` before this update, add a
`google_id` column by hand to both tabs (any position works, but
matching the order in `schema.py` keeps things tidy) — `init_sheets.py`
only creates tabs that don't exist yet, it won't add columns to ones
that already do.

## 1. Google Cloud + Sheets setup

1. console.cloud.google.com → New Project.
2. APIs & Services → Library → enable **Google Sheets API** and
   **Google Drive API**.
3. APIs & Services → Credentials → Create Credentials → Service Account.
4. Open the service account → Keys → Add Key → JSON. Download it.
5. Create a Google Sheet (e.g. "ZionBoutique Database"). Copy the Sheet
   ID from its URL (the long string between `/d/` and `/edit`).
6. Open the downloaded JSON, copy `client_email`, and share the Sheet
   with that address as **Editor**.

## 2. Local setup

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
copy .env.example .env            # Windows: copy | macOS/Linux: cp
```

Edit `.env`:
- `FLASK_SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `GOOGLE_SHEET_ID` — from step 5 above
- `GOOGLE_SHEETS_CREDS_PATH` — put the downloaded JSON key at this path
  (default expects it at `instance/gsheets-creds.json`)

Then:
```bash
python init_sheets.py    # creates the 6 tabs with headers
python seed_admin.py     # creates your first admin login (asks for name/email/password)
python app.py            # runs at http://localhost:5000
```

Open `http://localhost:5000`, log in with the admin account you just
created.

## 3. Pushing to GitHub

```bash
git init
git add .
git commit -m "ZionBoutique: Flask + Google Sheets backend"
git branch -M main
git remote add origin <your-empty-github-repo-url>
git push -u origin main
```

`.gitignore` already excludes `.env`, `instance/` (your credentials
file), and `__pycache__/` — double-check `git status` before your first
commit that neither shows up as staged.

## 4. Deploying to Vercel

Two extra files make this work on Vercel's serverless platform:
- `api/index.py` — re-exports the real Flask `app` from `app.py` so
  Vercel's Python runtime can run it as a WSGI function
- `vercel.json` — routes every request to that function and tells the
  build to include the `templates/` folder (Vercel's Python builder
  doesn't auto-bundle non-Python files otherwise)

Steps:
1. Push this repo to GitHub (see step 3 above).
2. On vercel.com → Add New → Project → import the GitHub repo.
3. Framework Preset: choose "Other" (there's no Flask preset — the
   `vercel.json` in the repo does the actual work).
4. Under **Environment Variables**, add:
   - `FLASK_SECRET_KEY`
   - `GOOGLE_SHEET_ID` → `1Aelcs_IagOGyrWXCFKKyfTZZczwXHmUCgBN0XoamfsU`
   - `GOOGLE_SHEETS_CREDS_JSON` — paste the entire service account JSON
     key as one value. Vercel functions have no persistent disk at all
     (even less than Render's free tier), so the file-path option isn't
     usable here — this env var is the only way in.
   - `TAX_RATE` (optional)
   - `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` (for Google Sign-In)
5. Deploy. Vercel gives you a URL like `bethel-boutique.vercel.app` —
   make sure that exact URL + `/auth/google/callback` is in your OAuth
   client's Authorized redirect URIs (see "Google Sign-In" section above).

Things that behave differently on Vercel specifically:
- **Cold starts.** Each new serverless invocation re-authenticates with
  Google (no long-lived process), adding a bit of latency on the first
  request after idle time. Fine for a boutique's traffic; not something
  to worry about at this scale.
- **The in-process stock lock (`adjust_stock`'s `threading.Lock`) only
  protects a single function instance.** Vercel can spin up multiple
  concurrent instances under load, so two near-simultaneous sales on
  the very last unit of a product could both pass the stock check. Low
  risk for a single small shop, but if that ever becomes a real problem,
  it's the same fix noted below (a shared lock or a real database).
- **Sessions still work fine** — Flask's default session is a signed
  cookie stored in the browser, not server-side memory, so it doesn't
  care that serverless functions don't persist state between requests.
- `init_sheets.py` and `seed_admin.py` are one-time scripts — keep
  running those from your own machine (pointed at the same Sheet), not
  on Vercel.

## 5. Deploying to Render (alternative)

Render is a straightforward alternative if you'd rather run this as a
persistent Flask process instead of serverless.

1. Push this repo to GitHub (step 3).
2. On render.com → New → Web Service → connect your GitHub repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: leave it to read the `Procfile` (`gunicorn app:app`),
   or set it explicitly to the same thing.
5. Under **Environment**, add:
   - `FLASK_SECRET_KEY` — the same one you generated (or a new one)
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_SHEETS_CREDS_JSON` — paste the **entire contents** of your
     downloaded service account JSON key as one value. (Render's free
     tier has no persistent disk, so a file path won't survive restarts
     — the JSON-as-env-var path in `config.py`/`sheets_db.py` exists for
     exactly this.)
   - `TAX_RATE` (optional, defaults to 0.16)
6. Deploy. Render gives you a URL like `zionboutique.onrender.com`.
7. Once it's live, run `seed_admin.py` **locally** (pointed at the same
   Sheet, using your local `GOOGLE_SHEETS_CREDS_PATH`) to create the
   admin login the deployed app will use — the Sheet is the shared
   source of truth regardless of which machine talks to it.

Railway and PythonAnywhere work the same way in spirit: set the same
environment variables, point the start command at `gunicorn app:app`
(Railway) or configure a WSGI app pointing at `app:app`
(PythonAnywhere).

## Auth & access control

- Passwords are hashed (PBKDF2 via Werkzeug) — never stored or compared
  as plaintext.
- `login_required` — any signed-in user.
- `role_required("admin")` — Reports, Staff Management, product
  create/edit. Enforced **server-side** on every request; the sidebar
  hiding admin links in the browser is just a UX nicety, not what's
  protecting the data.
- Order totals (subtotal/tax/total) are computed server-side from the
  current product price — the client never gets to submit its own price.
- Stock is decremented through `adjust_stock()`, which rejects an order
  if it would oversell, and logs every change to the StockLedger tab.

## Known limitations (see README history in this project for more)

- Google Sheets API quota is ~300 requests/min/project — fine for one
  boutique, but cache reads if traffic grows.
- No real DB transactions; `adjust_stock`'s in-process lock only
  protects a single running gunicorn worker. If you scale to multiple
  workers/dynos, move that lock to Redis or migrate to a real database
  (Supabase/Neon/Railway all have free Postgres tiers) — the route code
  barely changes since it already goes through `sheets_db.py` instead of
  raw SQL.
