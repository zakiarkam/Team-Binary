-- ===========================================================================
--  AI-Powered Digital Marketing Orchestration — PostgreSQL schema
--  Team Binary · University of Moratuwa · 2026
--
--  Table names follow the architecture figures in the Interim Report:
--    Figure 5.2  → user_segments      ("PostgreSQL Segments Table")
--    Figure 5.3  → interactions       ("PostgreSQL Interactions Table")
--    Figure 5.4  → analytics_output   ("Analytics Output / PostgreSQL Tables")
--    Figure 5.5  → content_assets     ("PostgreSQL Content Assets Table")
--
--  Everything is IF NOT EXISTS so this file is safe to re-run on every boot.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- users — the companies using this platform. A business (say, "Aymex")
-- creates an account, registers its website, and the system markets to that
-- website's visitors. Passwords are scrypt-hashed, never stored.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT        NOT NULL UNIQUE,
    password_hash TEXT        NOT NULL,
    company_name  TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Opaque login tokens. A row here IS the session; logout deletes it, so a
-- token cannot outlive the sign-out the way a self-contained JWT can.
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT        PRIMARY KEY,
    user_id    BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);

-- ---------------------------------------------------------------------------
-- sites — one row per client website being marketed.
-- `site_key` is the PUBLIC key embedded in the mos.js tracking snippet.
-- `ingest_secret` is private and used for server-to-server calls.
-- `owner_id` is the account that registered the site through the app; sites
-- created by local scripts/tests have no owner and stay visible in local mode.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sites (
    id              SERIAL PRIMARY KEY,
    owner_id        BIGINT      REFERENCES users(id) ON DELETE CASCADE,
    site_key        TEXT        NOT NULL UNIQUE,
    ingest_secret   TEXT        NOT NULL,
    name            TEXT        NOT NULL,
    url             TEXT        NOT NULL,
    product_name    TEXT,
    description     TEXT,
    target_audience TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Existing databases predate accounts; add ownership in place.
ALTER TABLE sites ADD COLUMN IF NOT EXISTS owner_id BIGINT REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_sites_owner ON sites (owner_id);

-- ---------------------------------------------------------------------------
-- visitors — one row per person seen on the client's website.
-- Starts anonymous (visitor_uid from localStorage); becomes "known" when
-- mos.identify(email) is called, e.g. on newsletter signup.
--
-- email_consent gates ALL outbound email. It is only set true when the visitor
-- explicitly opts in, and is set back to false on unsubscribe.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS visitors (
    id              BIGSERIAL PRIMARY KEY,
    site_id         INTEGER     NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    visitor_uid     TEXT        NOT NULL,
    email           TEXT,
    name            TEXT,
    email_consent   BOOLEAN     NOT NULL DEFAULT FALSE,
    consent_at      TIMESTAMPTZ,
    unsubscribed_at TIMESTAMPTZ,
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
    utm_source      TEXT,
    utm_medium      TEXT,
    utm_campaign    TEXT,
    referrer        TEXT,
    device          TEXT,
    country         TEXT,
    -- TRUE for visitors created by scripts/generate_demo_traffic.py. Simulated
    -- traffic is useful for demonstrating the system before a real audience
    -- exists, but it must never be counted as a real result — so it is labelled
    -- in the data itself, not just in a README.
    is_synthetic    BOOLEAN     NOT NULL DEFAULT FALSE,
    UNIQUE (site_id, visitor_uid)
);

-- Existing databases predate is_synthetic; add it in place.
ALTER TABLE visitors ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_visitors_site       ON visitors (site_id);
CREATE INDEX IF NOT EXISTS idx_visitors_email      ON visitors (site_id, email);
CREATE INDEX IF NOT EXISTS idx_visitors_consent    ON visitors (site_id, email_consent);

-- ---------------------------------------------------------------------------
-- events — the raw behavioural stream collected by the mos.js snippet.
-- This is the ONLY source of real audience data (Phase 1 decision: the
-- audience is built from live website tracking, not uploaded CSVs).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id           BIGSERIAL PRIMARY KEY,
    site_id      INTEGER     NOT NULL REFERENCES sites(id)    ON DELETE CASCADE,
    visitor_id   BIGINT      NOT NULL REFERENCES visitors(id) ON DELETE CASCADE,
    session_id   TEXT,
    event_type   TEXT        NOT NULL,   -- page_view | click | scroll | form_submit
                                         -- | identify | add_to_cart | purchase
    path         TEXT,
    referrer     TEXT,
    props        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_visitor ON events (visitor_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_site    ON events (site_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_type    ON events (site_id, event_type);

-- ---------------------------------------------------------------------------
-- site_crawls — cached output of crawler.py for a client website (Module 4).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS site_crawls (
    id         BIGSERIAL PRIMARY KEY,
    site_id    INTEGER     NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    url        TEXT        NOT NULL,
    ok         BOOLEAN     NOT NULL DEFAULT TRUE,
    data       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    crawled_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_site_crawls_site ON site_crawls (site_id, crawled_at DESC);

-- ---------------------------------------------------------------------------
-- MODULE 1 — user_segments  (Report Figure 5.2, "PostgreSQL Segments Table")
-- Latest hybrid segment per visitor. One row per visitor; re-segmenting
-- upserts. `is_cold_start` marks visitors whose behavioural history was too
-- thin for the ML clustering, so the rule-based path decided the label —
-- this is the cold-start contribution of the research.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_segments (
    id                 BIGSERIAL PRIMARY KEY,
    site_id            INTEGER     NOT NULL REFERENCES sites(id)    ON DELETE CASCADE,
    visitor_id         BIGINT      NOT NULL REFERENCES visitors(id) ON DELETE CASCADE,
    segment_id         INTEGER,
    segment_name       TEXT        NOT NULL,
    segment_method     TEXT        NOT NULL,   -- rule | ml | hybrid | cold_start
    segment_confidence NUMERIC(5,4),
    is_cold_start      BOOLEAN     NOT NULL DEFAULT FALSE,
    features           JSONB       NOT NULL DEFAULT '{}'::jsonb,
    model_version      TEXT,
    computed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (visitor_id)
);

CREATE INDEX IF NOT EXISTS idx_user_segments_site ON user_segments (site_id, segment_name);

-- ---------------------------------------------------------------------------
-- MODULE 4 — content_assets  (Report Figure 5.5, "PostgreSQL Content Assets Table")
-- Platform-native marketing assets with the four quality scores.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_assets (
    id                        BIGSERIAL PRIMARY KEY,
    site_id                   INTEGER     NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    campaign_id               BIGINT,
    platform                  TEXT        NOT NULL,   -- email | instagram | linkedin | tiktok | facebook
    subject                   TEXT,                   -- email subject line
    caption                   TEXT        NOT NULL,
    hashtags                  JSONB       NOT NULL DEFAULT '[]'::jsonb,
    cta                       TEXT,
    image_prompt              TEXT,
    campaign_goal             TEXT,
    tone                      TEXT,
    target_segment            TEXT,
    engagement_score          NUMERIC(6,4),
    semantic_score            NUMERIC(6,4),
    platform_suitability_score NUMERIC(6,4),
    final_score               NUMERIC(6,4),
    engine                    TEXT,                   -- fast | phi3
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_assets_site ON content_assets (site_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- MODULE 2 — campaigns and campaign_sends
-- `strategy` is the automation policy under test: fixed | trigger | hybrid.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaigns (
    id           BIGSERIAL PRIMARY KEY,
    site_id      INTEGER     NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    name         TEXT        NOT NULL,
    strategy     TEXT        NOT NULL DEFAULT 'hybrid',   -- fixed | trigger | hybrid
    status       TEXT        NOT NULL DEFAULT 'draft',    -- draft | running | paused | done
    campaign_goal TEXT,
    tone         TEXT,
    audience_filter JSONB    NOT NULL DEFAULT '{}'::jsonb, -- e.g. {"segments":["High Intent"]}
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_campaigns_site ON campaigns (site_id, status);

-- One row per message queued/sent to one visitor.
-- `track_token` is the opaque id embedded in the open-pixel and click URLs.
CREATE TABLE IF NOT EXISTS campaign_sends (
    id                  BIGSERIAL PRIMARY KEY,
    campaign_id         BIGINT      NOT NULL REFERENCES campaigns(id)      ON DELETE CASCADE,
    visitor_id          BIGINT      NOT NULL REFERENCES visitors(id)       ON DELETE CASCADE,
    content_asset_id    BIGINT               REFERENCES content_assets(id) ON DELETE SET NULL,
    step                INTEGER     NOT NULL DEFAULT 0,
    channel             TEXT        NOT NULL DEFAULT 'email',
    subject             TEXT,
    body_html           TEXT,
    body_text           TEXT,
    scheduled_for       TIMESTAMPTZ,
    sent_at             TIMESTAMPTZ,
    status              TEXT        NOT NULL DEFAULT 'scheduled',
                                    -- scheduled | sent | failed | skipped | dry_run
    error               TEXT,
    provider_message_id TEXT,
    track_token         TEXT        NOT NULL UNIQUE,
    -- Destination URLs for this message, resolved server-side by index.
    -- Tracked links are /track/click/{token}/{index} rather than carrying the
    -- target in a query string, which makes an open-redirect impossible.
    links               JSONB       NOT NULL DEFAULT '[]'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE campaign_sends ADD COLUMN IF NOT EXISTS links JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_sends_campaign  ON campaign_sends (campaign_id, status);
CREATE INDEX IF NOT EXISTS idx_sends_visitor   ON campaign_sends (visitor_id);
CREATE INDEX IF NOT EXISTS idx_sends_due       ON campaign_sends (status, scheduled_for);

-- ---------------------------------------------------------------------------
-- MODULE 3 input — interactions  (Report Figure 5.3, "PostgreSQL Interactions Table")
-- The marketing funnel event log. Unlike the simulated logs used in the
-- research study, every row here is a REAL observed event:
--   sent    — the SMTP handoff succeeded
--   open    — the tracking pixel was fetched
--   click   — a tracked link was followed
--   convert — a goal event fired on the website after a click
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interactions (
    id          BIGSERIAL PRIMARY KEY,
    site_id     INTEGER     NOT NULL REFERENCES sites(id)     ON DELETE CASCADE,
    visitor_id  BIGINT      NOT NULL REFERENCES visitors(id)  ON DELETE CASCADE,
    campaign_id BIGINT               REFERENCES campaigns(id) ON DELETE CASCADE,
    send_id     BIGINT               REFERENCES campaign_sends(id) ON DELETE CASCADE,
    strategy    TEXT,                            -- fixed | trigger | hybrid
    channel     TEXT        NOT NULL DEFAULT 'email',
    platform    TEXT        NOT NULL DEFAULT 'email',
    event_type  TEXT        NOT NULL,            -- sent | open | click | convert
                                                 -- | bounce | unsubscribe
    is_real     BOOLEAN     NOT NULL DEFAULT TRUE,  -- FALSE for simulated rows
    meta        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_interactions_site     ON interactions (site_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_interactions_visitor  ON interactions (visitor_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_interactions_campaign ON interactions (campaign_id, event_type);

-- ---------------------------------------------------------------------------
-- MODULE 3 output — analytics_output  (Report Figure 5.4)
-- Per-visitor predictions and the next-best action recommendation that closes
-- the loop back into Module 2 (campaigns) and Module 4 (content).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_output (
    id                   BIGSERIAL PRIMARY KEY,
    site_id              INTEGER     NOT NULL REFERENCES sites(id)    ON DELETE CASCADE,
    visitor_id           BIGINT      NOT NULL REFERENCES visitors(id) ON DELETE CASCADE,
    predicted_conversion NUMERIC(6,4),
    drop_off_risk        NUMERIC(6,4),
    recommendation       TEXT,
    recommended_platform TEXT,
    attribution_model    TEXT,        -- first_touch | last_touch | linear | markov
    confidence           NUMERIC(6,4),
    model_version        TEXT,
    computed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (visitor_id)
);

CREATE INDEX IF NOT EXISTS idx_analytics_site ON analytics_output (site_id, predicted_conversion DESC);

-- ---------------------------------------------------------------------------
-- pipeline_runs — audit trail of every orchestration run (for the Research tab)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id           BIGSERIAL PRIMARY KEY,
    site_id      INTEGER     REFERENCES sites(id) ON DELETE CASCADE,
    stage        TEXT        NOT NULL,   -- segmentation | automation | analytics | content | full
    status       TEXT        NOT NULL DEFAULT 'running',  -- running | ok | failed
    detail       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    error        TEXT,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_site ON pipeline_runs (site_id, started_at DESC);

-- ---------------------------------------------------------------------------
-- content_actions — "post THIS on Instagram", the broadcast half of a plan.
--
-- The platform is ADVISORY: it never publishes anything and never sends mail.
-- It writes the content, says who it is for and why, and hands it to the
-- company to publish from their own accounts. That is the report's Module 3
-- "Decision Support" / "Recommendation Generator" rather than an ESP.
--
-- Per-recipient email drafts live in campaign_sends (one row per person);
-- a platform post is one-to-many, so it needs its own row shape.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_actions (
    id               BIGSERIAL PRIMARY KEY,
    site_id          INTEGER     NOT NULL REFERENCES sites(id)          ON DELETE CASCADE,
    campaign_id      BIGINT               REFERENCES campaigns(id)      ON DELETE CASCADE,
    content_asset_id BIGINT               REFERENCES content_assets(id) ON DELETE SET NULL,
    platform         TEXT        NOT NULL,          -- instagram | linkedin | shorts | facebook
    target_segment   TEXT,
    audience_size    INTEGER     NOT NULL DEFAULT 0,
    rationale        TEXT,                          -- why this action, in plain language
    priority         INTEGER     NOT NULL DEFAULT 100,
    -- The link the company puts in the post. Clicking it lands on their site
    -- via /l/{token}, which is how a published post stays measurable even
    -- though we never published it.
    track_token      TEXT        NOT NULL UNIQUE,
    target_url       TEXT,
    status           TEXT        NOT NULL DEFAULT 'suggested',  -- suggested | executed | skipped
    executed_at      TIMESTAMPTZ,
    outcome          JSONB       NOT NULL DEFAULT '{}'::jsonb,  -- what the company reported back
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_actions_site ON content_actions (site_id, status, priority);
CREATE INDEX IF NOT EXISTS idx_content_actions_camp ON content_actions (campaign_id);

-- Email drafts are recommended actions too, so they carry the same lifecycle
-- fields. `status` moves planned → executed | skipped; nothing is ever "sent"
-- by this platform.
ALTER TABLE campaign_sends ADD COLUMN IF NOT EXISTS executed_at TIMESTAMPTZ;
ALTER TABLE campaign_sends ADD COLUMN IF NOT EXISTS rationale   TEXT;
