# External Data Guide and Model-Placement Audit (M4)

## 1. What can be collected now versus later

| Need | Can obtain now? | Source / action | Why it matters |
|---|---|---|---|
| Existing local engagement corpus | Yes | Already in `data/raw/datasets/your_engagement_dataset.csv` | Train the generic text-and-platform engagement ranker. |
| Instagram owned-account analytics | Yes, with a professional account/access | [Meta Business Suite export](https://www.facebook.com/help/messenger-app/972879969525875/aide-ordinateur/) and [Instagram Insights requirements](https://www.facebook.com/help/684550305010470/) | Real reach, impressions and interactions for later validation/personalization. |
| LinkedIn post analytics | Yes, for content the account owns | [Organization Page statistics](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/page-statistics?view=li-lms-2026-06) and [Page analytics roles/export access](https://learn.microsoft.com/en-us/linkedin/marketing/getting-started?view=li-lms-2026-04) | Provides authorized organization reporting. API access can be restricted. |
| TikTok owned-account analytics | Yes for a Business Account; export access varies | [TikTok Web Business Suite analytics](https://ads.tiktok.com/help/article/navigate-web-business-suite/) | The Business Suite provides analytics downloads for reach, engagement, conversions and followers. |
| Email campaign analytics | Yes, through the email provider | [Mailchimp campaign-report CSV export](https://mailchimp.com/help/download-a-campaign-report/) | Provides delivered, opens, clicks and conversions for email-specific learning. |
| Goal/tone ground truth | Not reliably downloadable as a ready-made dataset | Human review/annotation | Needed for a defensible platform-conditioned strategy classifier. |
| Real uplift from generated content | Only after posts have outcomes | Export analytics after manual posting | Required to claim that selection/regeneration improved real engagement. |

Never scrape arbitrary users' posts or use private data without permission. Use owned-account exports, public data that permits research use, or data collected with explicit consent.

## 2. Exact place to add future files

```text
data/feedback/
├── analytics_import/                 # drop raw platform exports here
│   ├── instagram_brand_a_2026_08.csv
│   ├── linkedin_brand_a_2026_08.csv
│   ├── tiktok_brand_a_2026_08.csv
│   └── email_brand_a_2026_08.csv
└── feedback.db                       # created by the application; do not edit by hand
```

`data/feedback/` is intentionally ignored by Git because it can contain private business analytics. Keep the raw exports locally or in approved secure storage.

Run this workflow after placing files there:

```bash
# Record the M4 predictions for generated content.
python3 modules/m4_content/main.py --step feedback-log

# Import actual platform outcomes from the CSV files.
python3 modules/m4_content/main.py --step feedback-import

# Retrain the account-aware engagement ranker when enough actuals exist.
python3 modules/m4_content/main.py --step engagement-retrain --force

# Generate and select future Phi-3 candidates using the updated ranker.
python3 modules/m4_content/main.py --step generate-candidates
```

## 3. Minimum CSV schema

The importer already recognises several header aliases. Prefer this canonical schema for every platform:

```csv
platform,account_id,external_post_id,caption,published_at,followers_at_post_time,actual_impressions,actual_reach,actual_likes,actual_comments,actual_shares,actual_clicks,actual_conversions
instagram,brand_a,1789...,"Caption text",2026-08-01T10:00:00,12000,8400,7200,310,22,18,14,3
```

Required for useful learning:

- `platform`, `account_id`, `external_post_id`, `caption`
- `actual_impressions` **or** `actual_reach`
- likes, comments, shares when available
- publish date/time

Useful but optional:

- followers at posting time
- clicks and conversions
- campaign/product id
- media type (image, carousel, short video)

The important target is:

```text
engagement_rate = (likes + comments + shares) / impressions
```

When one account has enough posts, train on its **within-account percentile or z-score**, not raw likes. This controls the follower/reach confound.

## 4. Separate file for platform-specific goal/tone accuracy

Analytics do not label business goal or tone. Create a reviewed annotation file separately:

```text
data/private_annotations/platform_goal_tone_reviewed.csv
```

Suggested schema:

```csv
platform,product_context,caption,campaign_goal,tone,reviewer_id,review_status
linkedin,"Scheduling tool for clinics","Reduce no-shows...",lead_generation,professional,r1,approved
instagram,"Scheduling tool for clinics","Less waiting, more care...",awareness,friendly,r2,approved
```

Use two reviewers for a sample; resolve disagreements before creating the final train/test split. This file should normally stay private and out of Git.

### Minimum realistic collection target

| Purpose | Minimum | Better target |
|---|---:|---:|
| Platform-conditioned goal/tone classifier | 300 reviewed rows | 500–1,000 balanced rows |
| Per-platform test evidence | 30 reviewed rows/platform | 75–100/platform |
| Account-aware engagement ranker | 30 historical posts/account | 50–100 posts/account |
| Human evaluation of generated assets | 100 assets, 2 raters | 200+ assets, 3 raters |

## 5. Model-placement audit

| Component | Current appropriate use | Correction / caution |
|---|---|---|
| Goal classifier | Infer product-level campaign objective from product/website context. | Do not optimize this objective solely for predicted engagement. A high-engagement post can still have the wrong business goal. |
| Tone classifier | Infer or verify communication style. | Current data has no platform field, so do not claim platform-specific classifier accuracy yet. |
| Platform rules | Caption length, hashtags, CTA style and visual/video format. | These are format constraints, not evidence that LinkedIn is always professional or Instagram is always awareness. |
| Engagement model | Rank otherwise valid candidates. | It should never be the only score and must not use likes/comments/impressions as input features when those define the target. The current `engagement.py` has an explicit leakage guard. |
| BART summary | Legacy detailed M4 path. | The unified `content_service.py` already prefers website metadata/paragraph context; do not claim BART summary is used by every app run unless verified. |
| Phi-3 generator | Produce content conditioned on product context, platform rules, goal and tone. | Do not fine-tune it on weak 527-row strategy labels. First collect verified input→output→outcome examples. |
| Future personalized model | Rank content using actual account outcomes. | This is the correct place for future CSV data; it is not a current live-result claim. |

## 6. Correct automation policy

```text
product context + platform
 -> infer/choose business goal and tone
 -> generate several candidates that preserve that strategy
 -> reject/retry weak candidates using format/relevance/engagement feedback
 -> select the best candidate
```

Never do this:

```text
candidate has low engagement score -> change conversion goal to awareness
```

Changing the business objective to increase a proxy score is reward hacking, not campaign optimization. Regenerate the wording, hook, CTA, visual prompt, length or hashtag strategy while preserving the selected goal and tone.

## 7. What to say in the presentation

> The current system is a cold-start content ranker. It uses public data to rank candidates and enforces platform format rules. Future owner-authorized analytics exports enter through a separate feedback store, where engagement is normalized within account to reduce follower-count bias. Platform-specific goal/tone accuracy is reported only after a human-reviewed platform-labelled evaluation set is available.
