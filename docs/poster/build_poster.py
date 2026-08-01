"""Build the A2 exhibition poster.

    python3 docs/poster/build_poster.py

Reads  docs/poster/poster.html  and writes, beside it:

    poster_standalone.html   images inlined as data URIs — one file, mails anywhere
    poster.pdf               420 x 594 mm, print-ready, backgrounds on
    poster_preview.png       on-screen check at 150 dpi

Rendering uses the Google Chrome already installed on the machine (Playwright's
`channel="chrome"`), so no browser download is required.  The script prints an
overflow report: the poster is a fixed 594 mm canvas and content that does not
fit is silently clipped, so this is the check that matters.
"""
import base64
import mimetypes
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SRC = HERE / "poster.html"
STANDALONE = HERE / "poster_standalone.html"
PDF = HERE / "poster.pdf"
PREVIEW = HERE / "poster_preview.png"

A2_W_MM, A2_H_MM = 420, 594


def inline_images(html: str, base: pathlib.Path) -> str:
    """Replace every local <img src> with a base64 data URI."""

    def repl(m: re.Match) -> str:
        src = m.group(2)
        if src.startswith(("data:", "http://", "https://")):
            return m.group(0)
        path = (base / src).resolve()
        if not path.exists():
            sys.exit(f"missing image: {src} -> {path}")
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'{m.group(1)}data:{mime};base64,{b64}{m.group(3)}'

    return re.sub(r'(<img[^>]*\ssrc=")([^"]+)(")', repl, html)


def main() -> None:
    html = SRC.read_text(encoding="utf-8")
    STANDALONE.write_text(inline_images(html, SRC.parent), encoding="utf-8")
    kb = STANDALONE.stat().st_size // 1024
    print(f"wrote {STANDALONE.relative_to(ROOT)}  ({kb} KB, self-contained)")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright not importable — run with the project venv:\n"
                 "  venv/bin/python docs/poster/build_poster.py")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(
            viewport={"width": 1588, "height": 2245},  # 420x594 mm at 96 dpi
            device_scale_factor=2,
        )
        page.goto(STANDALONE.as_uri())
        page.wait_for_load_state("networkidle")
        page.emulate_media(media="print")

        report = page.evaluate(
            """() => {
              const PX = 96 / 25.4;                       // CSS px per mm
              const el = document.querySelector('.poster');
              const rows = [];
              for (const s of document.querySelectorAll('.pad > section, .frame > .col')) {
                const h2 = s.querySelector('h2');
                const box = s.clientHeight;
                // scrollHeight is floored at clientHeight, so a section with
                // slack looks identical to one that exactly fits. Release the
                // fixed height to read what the content actually wants.
                // (and grid items stretch to the row, so release that too)
                const fixed = s.style.height, align = s.style.alignSelf;
                s.style.height = 'auto'; s.style.alignSelf = 'start';
                const need = s.scrollHeight;
                s.style.height = fixed; s.style.alignSelf = align;
                const isCol = s.classList.contains('col');
                const h = s.querySelector('h3, h2');
                rows.push({
                  name: (isCol ? '    · ' : '') +
                        (h ? h.textContent.trim().replace(/\\s+/g, ' ') : s.className)
                          .slice(0, isCol ? 44 : 48),
                  box: box / PX, need: need / PX, col: isCol,
                });
              }
              const parts = {};
              for (const [k, sel] of [['header', '.band'], ['footer', '.ftr'],
                                      ['grid', '.pad']]) {
                const n = document.querySelector(sel);
                if (n) parts[k] = n.getBoundingClientRect().height / PX;
              }
              return { posterH: el.scrollHeight / PX, posterBox: el.clientHeight / PX,
                       rows, parts };
            }"""
        )

        p = report["parts"]
        print(f"\ncanvas   594.0 mm   "
              f"title {p.get('header', 0):.1f} · body {p.get('grid', 0):.1f} · "
              f"footer {p.get('footer', 0):.1f}")
        slack = report["posterBox"] - report["posterH"]
        print(f"content  {report['posterH']:.1f} mm   slack {slack:+.1f} mm  "
              f"{'OK' if slack >= -0.5 else '<-- CANVAS OVERFLOW'}")

        print(f"\n  {'section':52s} {'box':>7s} {'needs':>7s}   over")
        bad = 0
        for r in report["rows"]:
            over = r["need"] - r["box"]
            flag = "" if over <= 0.4 else f"  +{over:.1f} mm  CLIPPED"
            if over > 0.4:
                bad += 1
            print(f"  {r['name']:52s} {r['box']:6.1f}mm "
                  f"{r['need']:6.1f}mm{flag}")
        print(f"\n  {bad} section(s) clipping" if bad else "\n  nothing clipped")

        page.pdf(path=str(PDF), width=f"{A2_W_MM}mm", height=f"{A2_H_MM}mm",
                 print_background=True, margin={"top": "0", "right": "0",
                                                "bottom": "0", "left": "0"})
        page.screenshot(path=str(PREVIEW), full_page=True)
        browser.close()

    print(f"\nwrote {PDF.relative_to(ROOT)}          ({PDF.stat().st_size // 1024} KB)")
    print(f"wrote {PREVIEW.relative_to(ROOT)}  ({PREVIEW.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
