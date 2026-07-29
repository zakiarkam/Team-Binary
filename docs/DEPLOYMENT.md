# Deployment — taking Marketing OS to production

How the system runs for real companies, what changes from local dev, and two
concrete ways to host it.

---

## How it works in the real world

Locally, everything points at `localhost`. In production the same four pieces
get real addresses:

```
 aymex.com  (the customer's website — THEY host this)
     │  <script defer src="https://api.marketingos.lk/mos.js" data-site="mos_x1y2">
     ▼
 api.marketingos.lk      FastAPI — /collect, /track, campaigns, the 4 modules
     │                            │
     ▼                            ▼
 PostgreSQL (managed)
     ▲
     │
 app.marketingos.lk      Next.js dashboard — where companies sign in
                         and work their Action Plan

 No SMTP provider, no publishing integrations: the platform hands the company
 finished content and the company sends it from its own tools.
```

The real-world journey, end to end:

1. **Aymex signs up** at `app.marketingos.lk` → registers `https://aymex.com`.
2. The dashboard gives them **one script tag**. Their developer pastes it into
   the site's `<head>` (in WordPress/Shopify/Wix this is the "custom code"
   box — no engineering project needed).
3. **Real visitors** browse aymex.com → the snippet batches page views,
   scrolls, clicks and purchases to `POST /collect`. Do Not Track honoured.
4. Visitors who sign up on aymex.com **with the consent box ticked** become
   contactable.
5. Aymex runs segmentation, generates content (the crawler reads aymex.com),
   then opens the **Action Plan**: *"send this email to these 15 High Intent
   contacts"*, *"post this on LinkedIn"* — content already written.
6. Aymex executes those actions in **its own** tools and marks them done.
7. Because the tracked links live in the content, **clicks and conversions
   flow back anyway** → funnel, attribution, predictions → the next plan gets
   better copy. The loop is closed without us ever sending anything.

Nothing in the code changes between demo and production — only `.env`.

---

## What must change from local dev (the checklist)

| # | Item | Where |
|---|---|---|
| 1 | **A domain + HTTPS** for API and dashboard. The snippet, tracking pixel and click-redirects embed `PUBLIC_API_URL` — email clients and customer sites will refuse mixed http/https content. | `.env`: `PUBLIC_API_URL=https://api.yourdomain` |
| 2 | **CORS** locked to the dashboard's real origin | `.env`: `CORS_ORIGINS=https://app.yourdomain` |
| 3 | **Dashboard → API URL** | web env: `NEXT_PUBLIC_API_URL=https://api.yourdomain` |
| 4 | **Nothing** — the platform advises rather than sends, so there is no SMTP to configure, no sending domain to warm up and no spam reputation to manage. This is the single biggest operational saving of the advisory design. | — |
| 5 | *(Optional)* If you deliberately want the opt-in sending feature: real SMTP credentials **and** SPF + DKIM DNS records for your From-domain, or mail lands in spam. | `.env` + your DNS panel |
| 6 | **Strong `POSTGRES_PASSWORD`** + database not exposed to the internet (only the API talks to it) | `.env` / firewall |
| 7 | **A plan scheduler.** `POST /campaigns/scheduler/run` refreshes the Action Plan from observed behaviour — locally you click, in production cron calls it. Protect it with `SCHEDULER_TOKEN`. | crontab / platform cron |
| 8 | Session cookie is already `Secure` in production builds (done), passwords scrypt, tenant isolation enforced in the API — no change needed | — |
| 9 | **Backups** — `pg_dump` nightly to object storage | crontab |

Resource note: the API imports PyTorch + XGBoost, so give it **≥ 2 GB RAM**.
The `fast` content engine needs no GPU; the optional `phi3` engine needs
Ollama on the same box.

---

## Option A — one small VPS (recommended, ~$6–12/month)

Everything on a single Ubuntu server (Hetzner CX22, DigitalOcean basic
droplet, AWS Lightsail). Closest to how you already run it with `make`.

```bash
# 1. Server basics
apt update && apt install -y docker.io docker-compose python3.11-venv nodejs npm caddy git
git clone <your-repo> /opt/marketing-os && cd /opt/marketing-os

# 2. Configure
cp .env.example .env    # then edit: PUBLIC_API_URL, CORS_ORIGINS, SMTP_*, strong DB password
make setup && make db

# 3. Run API + dashboard as services (systemd keeps them alive across reboots)
#    /etc/systemd/system/mos-api.service      → venv/bin/uvicorn api.main:app --port 8000
#    /etc/systemd/system/mos-web.service      → npm start --prefix web   (after: cd web && npm run build)
systemctl enable --now mos-api mos-web

# 4. HTTPS in 4 lines — Caddy gets certificates automatically
cat > /etc/caddy/Caddyfile <<'EOF'
api.yourdomain.lk { reverse_proxy localhost:8000 }
app.yourdomain.lk { reverse_proxy localhost:3000 }
EOF
systemctl reload caddy

# 5. The scheduler + backups
crontab -e
#   */10 * * * *  curl -s -X POST https://api.yourdomain.lk/campaigns/advance-all   # or per-campaign send/advance
#   0 3 * * *     docker exec mos_postgres pg_dump -U mos marketing_os | gzip > /backups/$(date +\%F).sql.gz
```

Point two DNS A-records (`api.`, `app.`) at the server and you're live.
No demo-site, no `make demo` — real customers bring their own websites.

## Option B — managed platforms, step by step

Free-to-cheap, no server to maintain. Three services, ~30 minutes.

**Before you start:** have the repo on GitHub, and pick your two subdomains
(e.g. `api.yourdomain.lk` and `app.yourdomain.lk`). Vercel and Railway both
issue their own URLs, so a custom domain is optional at first.

### 1 · Database — Neon (free tier)

1. Create a project at <https://neon.tech>; copy the connection details.
2. Neon requires TLS, which is why the API exposes `POSTGRES_SSLMODE`.

You will set these on the API service in step 2:

```
POSTGRES_HOST=ep-xxx-xxx.eu-central-1.aws.neon.tech
POSTGRES_PORT=5432
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=<from Neon>
POSTGRES_DB=neondb
POSTGRES_SSLMODE=require        # ← without this the connection is refused
```

The schema creates itself on first boot (`db.init_schema()` runs in the app
lifespan), so there is no migration step.

### 2 · API — Railway (needs ~2 GB RAM for PyTorch)

1. **New Project → Deploy from GitHub repo**, pick this repository.
2. Railway detects the `Dockerfile` at the repo root and builds it. The image
   installs **CPU-only torch** on purpose — the default wheel pulls ~2 GB of
   CUDA that a web dyno cannot use, and several platforms fail the build on
   image size because of it.
3. Set the environment variables:

```
# database — from step 1
POSTGRES_HOST=…  POSTGRES_PORT=5432  POSTGRES_USER=…
POSTGRES_PASSWORD=…  POSTGRES_DB=…  POSTGRES_SSLMODE=require

# public identity — the snippet, tracked links and /l/ links are built from this
PUBLIC_API_URL=https://your-api.up.railway.app
CORS_ORIGINS=https://your-dashboard.vercel.app

# protects the cron endpoint; any long random string
SCHEDULER_TOKEN=<openssl rand -hex 32>

# email stays OFF: the platform advises, it does not send.
# Only set SMTP_* if you deliberately want the opt-in sending feature.
```

4. Deploy, then check `https://your-api.up.railway.app/health` returns
   `"database": "up"`.

> `PORT` is injected by Railway and the Dockerfile's `CMD` already honours it.

### 3 · Dashboard — Vercel (free)

1. **Add New → Project**, import the same repo.
2. Set **Root Directory** to `web`. Vercel detects Next.js automatically.
3. Environment variable: `NEXT_PUBLIC_API_URL=https://your-api.up.railway.app`
4. Deploy. Then go back to Railway and set `CORS_ORIGINS` to the real Vercel
   URL, so the dashboard is the only origin allowed to call the API.

The session cookie is already `Secure` in production builds, so it will only
travel over the HTTPS both platforms give you.

### 4 · The scheduler — Railway cron

The Action Plan needs refreshing as visitors behave: a trigger plan queues its
next recommendation only after someone clicks or goes quiet. Add a Railway
**Cron Job** service on the same project:

```bash
curl -fsS -X POST https://your-api.up.railway.app/campaigns/scheduler/run \
     -H "X-Scheduler-Token: $SCHEDULER_TOKEN"
```

Schedule: `*/15 * * * *` (every 15 minutes) is ample.

This tick **adds recommendations and sends nothing** — an unattended job that
mails people on a timer is precisely what an advisory platform must not become.

### 5 · First real customer

1. Open the dashboard → **Create your company account**.
2. **Add your website** → copy the snippet → paste it into that site's
   `<head>` (in WordPress/Shopify this is the "custom code" box).
3. **Check installation** — it waits for the first event to arrive.
4. Once visitors accumulate: **Segment**, **Generate content**, then
   **Action Plan → Generate action plan**.
5. Work the plan: copy each email into your own mail tool, paste each caption
   into the matching social account, keep the tracked links intact, and mark
   each action done.

Clicks and conversions flow back automatically — the links are yours no matter
who published them.

### Costs, honestly

| | Free tier | If you outgrow it |
|---|---|---|
| Neon (Postgres) | 0.5 GB — plenty for early tenants | ~$19/mo |
| Railway (API) | trial credit only; 2 GB RAM needed | ~$10–20/mo |
| Vercel (dashboard) | genuinely free for this | $20/mo Pro |

Railway is the one that will actually cost money, because of the PyTorch
memory requirement. If that matters, Option A (one $6 VPS running everything)
is cheaper.

---

## What "production-ready" honestly means here

Already built in: multi-tenant isolation (404 across tenants, tested),
scrypt passwords, DB-backed sessions, consent enforced in SQL and re-checked
at send time, RFC 8058 one-click unsubscribe, Do Not Track, dry-run-by-default
email, `is_synthetic`/`is_real` data honesty.

Known gaps you should state rather than hide: no rate limiting on `/collect`
or `/auth`, no email-address verification at signup, single API worker (fine
for early tenants; scale with `uvicorn --workers` later), models trained on
simulated data until real traffic accumulates, and email deliverability
depends on warming up the sending domain. None of these block a small real
deployment; all are the natural "future work" chapter.
