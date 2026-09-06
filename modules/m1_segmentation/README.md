# Module 1 — Audience Targeting & Personalization

**Novel Contribution 1: Hybrid Dynamic Segmentation Engine**

Combines rule-based segmentation with machine-learning clustering so that
segmentation still works when a newly launched product has almost no data.

```
   rule-based   ─┐
   K-Means       ├──▶  agreement vote  ──▶  segment + confidence
   hierarchical ─┘
```

Five segments, shared with Modules 2 and 3:
`High Intent · Loyal Customer · Price Sensitive · Low Engagement · New Cold User`

---

## Files

| File | What it is |
|---|---|
| **`segment.py`** | The engine. This is the code that runs in production. |
| `segmentation.ipynb` | The original exploratory notebook (kept for the report's figures) |
| `validation_segmentation.ipynb` | Validation experiments |
| `digital_marketing_campaign_dataset.csv` | 8,000-user research dataset (Kaggle) |
| `user_segments.csv` | Research output — regenerate with `segment.py` |
| `dashboard.py` | Legacy Streamlit view. **Currently broken** — it imports `DB_CONFIG` from a `config.py` that a `.gitignore` rule swallowed. Superseded by the Next.js dashboard. |

---

## Running it

```bash
# Reproduce the research segmentation on the 8,000-user dataset
venv/bin/python modules/m1_segmentation/segment.py

# Segment a live website audience (needs the API + tracked visitors)
curl -X POST http://localhost:8000/sites/1/segment
```

---

## Two feature domains, one engine

The engine is feature-set agnostic. The same algorithm runs over two domains:

| | `research_segmenter()` | `web_segmenter()` |
|---|---|---|
| Data | Kaggle campaign dataset | Live visitors from `mos.js` |
| Features | email opens/clicks, site visits, pages/visit, time on site, social shares, previous purchases, loyalty points | page views, clicks, sessions, unique pages, scroll depth, time on site, form submits, purchases |
| Purpose | reproduce the study | run the product |

They are separate because a first-time visitor to a newly launched product has
no email history at all — which is precisely the cold-start problem this project
studies. Forcing web visitors into the research schema would mean inventing
values for columns that do not exist yet.

---

## Cold start, handled at two levels

**Population** — below 30 visitors there is nothing meaningful to cluster, so
the engine runs rules only and reports `mode: cold_start_rules` with the reason.
A newly launched product lives in this state; it is the normal early case, not
an error.

**Individual** — a visitor with almost no history is decided by rules and
flagged `is_cold_start`, regardless of where the clustering would place them.

---

## Three corrections made when the notebook became code

The notebook produced the research figures, but three defects would have
mattered the moment it ran on any new audience. Each is fixed in `segment.py`
and locked in by a test in `tests/test_segmentation.py`.

### 1. Cluster names were hardcoded to cluster indices

```python
cluster_names = {0: 'Low Engagement', 1: 'High Intent', ...}   # notebook
```

Those indices are an artifact of one dataset and one random seed. On any other
audience the mapping is arbitrary. `segment.py` derives each cluster's name from
its own centroid — scoring it on engagement and loyalty — so the labels mean
what they say on data the engine has never seen.

### 2. The Random Forest was leaking

The notebook built the classifier with `rule_encoded` as **both an input feature
and the target** (cells 27–28), so it was trained to predict its own input.
Result: 6,248 of 8,000 users came out with confidence exactly `1.00`, and mean
confidence was 0.9965.

`segment.py` learns the hybrid consensus from **behavioural features only**.

| | notebook | `segment.py` |
|---|---|---|
| Classifier accuracy | ~1.00 (leaked) | **0.92** (honest, held-out) |
| Mean confidence | 0.997 | **0.712** |

The classifier also gains a real purpose: labelling a newly arrived visitor
instantly, without re-clustering the whole audience.

### 3. The cold-start segment was being silently deleted

This is the most consequential one, because it erased Novel Contribution 1 from
the output.

In the agreement vote, `ml == hier` was checked **before**
`rule == 'New Cold User'`. Clustering cannot represent *"there is not enough
evidence about this user"* — it must place everyone in some cluster — so
whenever the two clusterings happened to agree, they overruled the rules and the
cold-start finding disappeared.

| | rules detect | survived the vote |
|---|---|---|
| Live website audience | 43 | **0** → now 43 |
| Research dataset | 163 | 127 → now **163** |

A method that cannot express a finding does not get to veto it, so cold start is
now resolved immediately after unanimous agreement.

---

## Results on the research dataset (8,000 users)

| Segment | Users | Share | Conversion rate |
|---|---:|---:|---:|
| Low Engagement | 3,384 | 42.3% | 86.0% |
| Loyal Customer | 2,247 | 28.1% | 91.0% |
| Price Sensitive | 1,393 | 17.4% | 87.9% |
| High Intent | 813 | 10.2% | 91.8% |
| New Cold User | 163 | 2.0% | **53.4%** |

**Conversion separation: 38.4 percentage points.** Conversion is used only to
*evaluate* the segments — it is never a clustering feature, so this separation
is not circular.

### Reported honestly

- **Silhouette score 0.087** on this dataset. That is low: the behavioural
  clusters overlap heavily and are not cleanly separated. The segments are
  commercially useful (see the conversion spread) without being geometrically
  tidy, and both facts belong in the report.
- **41% of users have all three methods disagreeing** (confidence 0.60). The
  hybrid engine falls back to the interpretable rule for them and says so.
  Only 460 users (5.8%) get unanimous agreement.
- On the live web audience the silhouette is much higher (**0.47**) — but that
  audience is currently mostly simulated traffic, whose archetypes are more
  separable than real visitors would be. Simulated visitors are flagged
  `is_synthetic = TRUE` in the database precisely so this cannot be misread.
