# Viva demonstration — a 10-minute walkthrough

**Team Binary · University of Moratuwa · 2026**

A script for demonstrating the system live, and the questions it is built to
survive.

---

## Before the room

Four terminals, then one command.

```bash
make db                                    # terminal 1 — PostgreSQL
venv/bin/uvicorn api.main:app --port 8000  # terminal 2 — API
cd web && npm run dev                      # terminal 3 — dashboard
make site                                  # terminal 4 — the demo client website

make demo                                  # populates everything (~60s)
make status                                # confirm all four are up
```

Open **<http://localhost:3000>** (dashboard) and **<http://localhost:4000>**
(the client's website) in two tabs.

`make demo` prints the demo login:
**demo@innov8smart.example / demo1234**

> **The platform never sends or publishes.** It writes the content and tells
> the company what to do with it. Sending exists only as an opt-in extra
> (`SMTP_HOST`), and stays off for the viva.

---

## The walkthrough

### 0 · Sign in — it's a product, not a script (1 minute)

The dashboard opens at a **sign-in page**. Sign in as the demo company.

> "This is a multi-tenant platform. A company — any company — creates an
> account, registers its website, and the system markets to that website's
> visitors. What you'll see is one company's view; another account sees none
> of this data. Isolation is enforced in the API, not the UI, and there's a
> test that proves one company's probes into another's site return 404."

If time allows, the strongest 60 seconds of the demo: click **Sign out →
Create your company account**, register as a made-up company (e.g. "Aymex"),
and show the onboarding — **Add your website → here's your snippet → check
installation**. Then sign back in as the demo account.

> "That snippet is the entire integration. Paste one line into their site and
> its visitors become the audience for everything you're about to see."

### 1 · The problem (30 seconds)

> "Marketing tools are fragmented: one for segmentation, one for email, one for
> analytics, one for content. Nothing connects them, and a newly launched
> product has almost no data to work with. This system is the four joined into
> one loop, built for exactly that low-data case."

### 2 · A real visitor becomes an audience member (2 minutes)

Open the demo site at :4000. Point at the footer badge: `tracking: on · a1b2c3d4`.

Do this while narrating:

| Action | What is recorded |
|---|---|
| Scroll to the bottom | `scroll` at 25 / 50 / 75 / 100% |
| Click **Book a demo** | `click` with the element's label |
| Enter an email, **tick the consent box**, submit | `form_submit` + `identify` — now a *contactable* visitor |
| Go to Pricing, choose **Growth** | `purchase` — the conversion |

Now refresh the dashboard's **Audience** page. The visitor count has gone up,
and the badge on the funnel has flipped from `simulated data` to
`real + simulated`.

> "That is one line of JavaScript on their website. Nothing was uploaded."

**Then turn on Do Not Track in the browser and reload the demo site.** The badge
reads `tracking: off (Do Not Track)` and nothing is collected.

> "It honours Do Not Track by default. Consent for email is separate again — a
> visitor can be tracked and still not be contactable."

### 3 · The audience is segmented (1 minute)

**Audience** page. Point at the consent breakdown:

> "150 visitors, but only about 15 can lawfully be emailed. That gap is the
> honest size of the addressable audience, and most dashboards hide it."

Point at **New Cold User** — usually the second-largest segment:

> "That is the cold-start group: visitors we do not know enough about yet.
> Clustering cannot express *'insufficient evidence'* — it has to put everyone
> somewhere — so the rules decide for them and they are flagged."

### 3b · The Action Plan — the product itself (2 minutes)

**Action Plan** page. This is the screen that answers "so what do I actually
do?"

> "This is what the system produces. Not a report — a list of jobs. 'Send this
> email to these 13 contacts.' The subject and body are written. 'Post this on
> Instagram' — caption, hashtags and a visual brief, ready to paste."

Point at the reason line under each action:

> "Every action says *why*. Instagram is first because it carries 20% of the
> attributed credit among the channels you can actually publish to. That
> sentence comes from the attribution model on the Analytics page."

Then the crucial point — pick up the **Link to use**:

> "We never send this email and never publish this post. So how is it still
> measured? The tracked link is in the *content*, not the delivery. Whoever
> puts it in the envelope — Mailchimp, Gmail, your own Instagram account — the
> link is ours. Clicking it records the click and forwards the visitor tagged
> `utm_source=instagram`, which the attribution model already understands."

> "What we give up is guaranteed open tracking. Opens were the weakest number
> we had anyway — Apple pre-fetches every pixel. We kept the metric that works
> and dropped the liability of being an email sender."

### 4 · Three automation policies, measured (2 minutes)

**Campaigns** page.

> "Same audience, same content, three policies. Fixed sends the whole sequence
> to everyone. Trigger sends one message and waits to see what they do. Hybrid
> uses the segment to pick the opener."

Point at **conversions per 1,000 sends**, not raw conversions:

> "Fixed often wins on raw conversions — because it sends five times as many
> messages. Per-send efficiency is the fair comparison, and the rules column is
> the operational cost: hybrid needs eight decision rules, fixed needs one."

### 5 · Attribution disagreeing is the finding (2 minutes)

**Analytics** page, attribution chart.

> "Four models over the same journeys. First-touch credits the channel that
> brought them in — LinkedIn, a newsletter. Last-touch credits the email that
> closed. They point at opposite ends of the same journey. A company using only
> last-touch would conclude email is everything and cut the spend that created
> the audience."

Then point at the diagnostic underneath:

> "It also tells you that around 40% of these journeys had a single touchpoint.
> On those, all four models agree by arithmetic, not because they found
> anything. Reporting the agreement without that caveat would be misleading."

### 6 · Content written from their own website (1 minute)

**Content** page.

> "The hashtags are lifted from their site's own headings; the copy comes from
> its meta description. We crawled the URL — nothing here was typed by hand."

Point at the platform priority panel:

> "The order comes from the attribution we just looked at. And it says plainly
> that 55% of the attributed credit sits with channels we cannot publish to —
> Google, direct traffic. Only the rest can influence what gets written."

### 7 · The Research page (2 minutes) — spend real time here

> "This page is generated from the repository and the database as it loads. Row
> counts are read from disk, so it cannot drift away from what is actually
> there."

Walk the dataset table:

> "Four datasets are real. Four are simulated or synthetic. Three real ones are
> shipped and **nothing reads them** — they turned out to be comment-level
> scrapes, so they cannot train a post-engagement model. That is listed rather
> than quietly dropped."

Then the **headline vs. what it actually means** column:

> "Every model shows both. The conversion model reads AUC 0.98 — on *simulated*
> data. Using it on a live audience is a transfer across distributions, so the
> ranking holds but the thresholds do not, and the system raises a calibration
> warning when they collapse."

---

## Questions this is built to answer

**"Is any of this real, or is it all simulated?"**
Both, and the system says which. `visitors.is_synthetic` and
`interactions.is_real` are set when the row is written — derived, never
asserted — and every figure carries a basis badge. A test fails the build if a
synthetic visitor ever produces a row marked real. Browse the demo site during
the viva and watch the badge change.

**"Your segmentation confidence is 0.71. What does that mean?"**
Agreement between the three methods, not a probability. All three agreeing gives
0.95; only the rules deciding gives 0.60. About 41% of users sit at 0.60 — the
methods disagree more often than they agree, and the engine says so.

**"Why is the silhouette score only 0.087?"**
Because the clusters genuinely overlap. The segments are commercially
meaningful — conversion differs by 38 points across them — without being
geometrically tidy. Both facts are in the report.

**"Your engagement model has a negative R². Why ship it?"**
It previously reported R² 0.99, which came entirely from label leakage: the
target's own components were left in the feature set. With the leak removed the
honest figure is −0.30, and no text feature correlates with engagement in that
dataset at all (every p > 0.16). So its weight in the content score was cut from
0.45 to 0.20, and the pathway stays wired for a dataset that has real signal.
Finding it is the contribution; hiding it would have been the failure.

**"How do you keep one company's data away from another?"**
Ownership is checked in one middleware that covers every site-scoped route —
a new endpoint cannot forget the check. Denials are 404, not 403, so a rejected
probe doesn't even confirm the site exists. Sessions are database rows (logout
deletes the row, killing the token instantly), passwords are salted scrypt, and
the browser never sees the token — it lives in an HttpOnly cookie.

**"Could you email real customers with this?"**
Technically yes — set `SMTP_HOST` and it sends. Consent is enforced in SQL
rather than in the UI, re-checked at the moment of sending, every message
carries one-click unsubscribe, and unsubscribing cancels anything still queued.
For the viva it stays in dry-run.

**"What would you do next?"**
Three things, in order: run it on a real launch to replace the simulated funnel;
find or collect an engagement dataset that actually has text signal; and grow
the goal/tone corpus, where `humorous` still has a single example and cannot be
learned.

---

## If something breaks

| Symptom | Fix |
|---|---|
| Dashboard shows "Cannot reach the API" | `make api` in terminal 2 |
| API exits with no traceback | An OpenMP segfault — check `import openmp_guard` is first in the entry point |
| Content generation fails | Is the demo site served? `make site` |
| Everything looks empty | `make demo` |
| Total reset | `make reset && make db && make demo` |
