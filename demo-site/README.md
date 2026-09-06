# demo-site — the client website under study

**This folder is not part of the platform.** It plays the role of the
*customer's* website — the shop whose visitors the four research modules act
on.

The system's premise is: a company registers its website URL, pastes one
`<script>` tag into it, and that website's customers become the marketing
audience. To study that you need a website you control — you cannot paste the
snippet into a real company's site for an experiment. So this folder is a
small, realistic online store for a fictional company, **Innov8Smart**.

## Why a shop, and not a SaaS product

The audience for this study is the 8,000 users of the *Digital Marketing
Campaign* dataset, imported by `scripts/import_research_audience.py`. Those
users have `PreviousPurchases` and `LoyaltyPoints` — they are retail customers.
A subscription product with monthly plans could not honestly own that
behaviour, so the website they are attached to is a store that sells
individual devices and runs a points scheme, exactly as the data describes.

| File | Role |
|---|---|
| `index.html` | Storefront — the headings, product copy and CTAs Module 4's crawler reads, plus the newsletter form with its consent checkbox |
| `cart.html` | Basket and checkout — completing an order fires the `purchase` conversion |
| `shop.js` | Basket state in `localStorage`, and the two commerce events (`add_to_cart`, `purchase`) |
| `tracking-status.js` | Footer badge showing whether the tracker is on, and the Do Not Track state |
| `style.css` | Styling |

`scripts/setup_demo_site.py` injects the freshly generated `site_key` into
every page, and `make site` serves them on <http://localhost:4000>.

## What to do with it during a viva

Browsing this store yourself creates a **live** visitor, written through the
same `/collect` endpoint as the imported research audience but recorded with
`source = 'live'`. That is the demonstration: the 8,000 dataset customers and
your own session sit side by side in the same database, every dashboard figure
says which of the two it rests on, and the badge changes from
`research dataset` to `dataset + live` the moment you click something.
