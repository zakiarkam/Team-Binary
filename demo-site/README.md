# demo-site — the stand-in client website

**This folder is not part of the platform.** It plays the role of the
*customer's* website — the "Aymex" of the demo.

The product's premise is: a company registers its website URL, pastes one
`<script>` tag into it, and that website's visitors become the marketing
audience. To demonstrate that live (at the viva, or locally) you need a
website you control — you cannot paste the snippet into a real company's
site during an exam. So this folder is a small, realistic website for a
fictional company, **Innov8Smart**, with exactly the pages the demo needs:

| File | Role |
|---|---|
| `index.html` | Landing page — headings/copy the crawler reads, a signup form with the consent checkbox |
| `pricing.html` | Pricing page — choosing a plan fires the `purchase` conversion |
| `tracking-status.js` | Footer badge showing whether the tracker is on (and Do Not Track state) |
| `style.css` | Styling |

`scripts/setup_demo_site.py` injects the freshly generated `site_key` into
these pages, and `make site` serves them on <http://localhost:4000>.

In real use this folder is irrelevant: a company signs up in the dashboard,
registers **their own** URL, and installs the snippet on **their own** site.
Everything else — tracking, segmentation, campaigns, analytics, content —
behaves identically either way, because the demo site talks to the same
public `/collect` endpoint any real website would.
