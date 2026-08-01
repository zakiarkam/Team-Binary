# Exhibition poster — A2 portrait

**Group 01 · Team Binary · AI-Powered Digital Marketing Orchestration**

`poster.pdf` is the print file: **420 × 594 mm (A2), portrait, no margins.**
Send it to the printer as-is — do **not** let the print shop "fit to page,"
which would scale it and add a white border.

```bash
venv/bin/python docs/poster/poster_figures.py   # result charts, poster-scale
venv/bin/python docs/poster/build_poster.py     # -> poster.pdf + preview
```

| File | What it is |
| --- | --- |
| `poster.html` | the source — edit this |
| `poster.pdf` | **the print file**, 420 × 594 mm |
| `poster_standalone.html` | one self-contained file, images inlined — mails anywhere |
| `poster_preview.png` | on-screen check |
| `poster_figures.py` | the four result charts, drawn at the size they print |
| `figures/` | the charts it writes |

## Layout

The structure follows the departmental reference poster:

```
  title band                     project title + one-line scope
  intro strip                    Problem in Brief | Aim & Objectives | Overall System Design
  module band  (four columns)    each repeating the same six sub-sections:
                                   description → Literature Review → Research Gaps
                                   → Methodology → Evaluation & Results → Future work
  closing band                   Conclusion | Final Integration of Modules
  footer                         institution · supervisors · group · members
```

Each module column carries its owner's index number under the heading, and a
coloured top rule that matches the module's colour in the system diagram and in
the integration figure — so a reader can follow one module across the poster.

## Typography

Body text, headings and the footer are **Times New Roman**. The system diagram,
the four methodology flowcharts and the result charts stay in a sans face on
purpose: a schematic label is read at a glance rather than in a line of prose,
and Times at 7 pt inside an 8 mm box does not hold up in print. The rule lives
in one CSS line — `.fc, .loop { font-family: … sans-serif }` — and the charts
set their own family in `poster_figures.py`.

## Editing without breaking the print

The canvas is a fixed 594 mm and anything past it is **silently clipped**, so
the intro and closing bands carry explicit `height` values in mm (the module
band is `flex:1` and absorbs whatever is left). `build_poster.py` prints, per
band *and per column*, the box it has against the height its content wants:

```
  section                                        box   needs   over
  Problem in Brief                             88.1mm  88.1mm
      · Problem in Brief                       88.1mm  75.4mm
      · Aim                                    88.1mm  88.1mm      <- the binding column
      · Overall System Design                  88.1mm  73.0mm
  Module 01 — Audience Targeting …            336.5mm 336.5mm
  ...
  nothing clipped
```

Add a sentence, rebuild, and read that table. A band is as tall as its tallest
column, so the column whose `needs` equals the band's is the one to cut. If a
band reports `CLIPPED`, either trim that column or take the millimetres from a
band with slack — the totals have to balance, because the poster is full.

## Where the numbers come from

Every figure and every statistic traces to `research/results/*.csv`, the tables
`make research` writes. `poster_figures.py` re-reads those tables rather than
recomputing anything, so if an experiment is re-run and a value moves, the
poster moves with it. The report's own figures in `research/figures/` are drawn
at page width and render their axis labels at about 3 pt when placed on A2 —
that is why the poster has its own set, drawn at 95 mm, the width it prints at.

The categorical palette used for the attribution chart was checked against
colour-vision, contrast and lightness criteria before use; keep the channel
order in `CAT` if you edit it, since adjacency is what those checks score.

The Module 04 scoring weights on the poster (0.40 semantic / 0.40 platform fit /
0.20 engagement) are read from `modules/m4_content/config.py`. Note that
`docs/METHODOLOGY.md` still documents the **pre-correction** weights
(0.30 / 0.25 / 0.45) from before experiment E7 cut the engagement term — that
file is stale, not the poster.
