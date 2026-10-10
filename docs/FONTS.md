# Fonts

The site serves its own fonts from `static/fonts/`. No page asks Google (or any other host) for a font, and the
Content-Security-Policy allows `font-src 'self'` only. For an offline, private product, a landing page that phones a
third party on every visit would be off-message.

## The brand set

| Role | Family | Files | Axes in the file | Declared range |
| --- | --- | --- | --- | --- |
| Display (hero, H2, card titles) | Instrument Serif, regular + italic | `instrument-serif-*.woff2` | none (static) | 400 |
| Reading (body, buttons) | DM Sans, roman + italic | `dm-sans-*-var-*.woff2` | opsz 9-40, wght 100-1000 | 300 700 |
| Labels, codes, receipts | JetBrains Mono | `jetbrains-mono-var-*.woff2` | wght 400-800 | 400 600 |

All three are under the SIL Open Font License 1.1, which permits self-hosting and redistribution with the licence.
The licence text and each project's copyright line are in `static/fonts/OFL.txt`.

The declared ranges match what the site used from Google Fonts, so the switch rendered pixel-identical. The variable
files carry more weight range than is declared; widening `font-weight` in the block makes it available.

## Subsets

Each face ships two subsets, chosen by `unicode-range`, so a page downloads only what its text needs:

- `-latin`: Basic Latin and Latin-1 (English, and Spanish letters such as n with tilde, accented vowels, inverted
  question and exclamation marks), plus general punctuation.
- `-latin-ext`: Latin Extended (vowels with macron as used in Nahuatl orthographies, and most European letters).

Instrument Serif and DM Sans have no glyph for the modifier-letter apostrophe U+02BC (JetBrains Mono does); no face
has the saltillo U+A78C. For a glottal stop in Nahuatl, use the right single quotation mark (U+2019), which every face
has, or the letter h, and keep one spelling site-wide, including in mono labels. Arrows and the full block character fall back to the system font, as they did before.

## Where it lives in the pages

Both `index.html` and `download.html` carry the same `<style id="zth-fonts">` block plus one
`<link rel="preload" as="font" ... crossorigin>` for `instrument-serif-italic-latin.woff2`, the hero display face.
The block is inline so the browser can start the font requests without fetching a stylesheet first.
`vercel.json` serves `/static/fonts/*` with a one-year immutable cache.

## Updating or adding a face

1. Download the woff2 files (from the font project's releases, or the Google Fonts CSS API with a current Chrome
   user agent, taking only the `latin` and `latin-ext` blocks).
2. Give the file a **new name** (for example add `-v2`). The cache is immutable, so a changed file under an old name
   would never reach returning visitors.
3. Edit the `@font-face` rules in the `zth-fonts` block of **both** pages, identically, and delete any file the block
   no longer names.
4. If the family has a new licence or copyright line, add it to `static/fonts/OFL.txt`.
5. Record the new files in the hash manifest, then run the checks:

   ```
   py -3.10 tools/fonts_check.py --record
   py -3.10 tools/fonts_check.py
   py -3.10 tools/csp_sync.py --check
   py -3.10 tools/lint_copy.py
   ```

`fonts_check.py` fails when the two blocks differ, when a referenced file is missing, when the preload points at a
file the block does not use, when the licence is missing, when any page or header mentions a Google font host or a
page says "Google Fonts", when `vercel.json` loses the immutable cache rule for `/static/fonts/(.*)`, when a `.woff2`
in `static/fonts/` is not named by the block (an orphan would still be published and cached for a year), or when a
file's bytes no longer match its hash in `tools/fonts.sha256`. That last check is the rename rule from step 2 turned
into a check: `--record` adds new files and drops deleted ones, but it never approves a changed file under an old name.
The manifest lives in `tools/` rather than `static/fonts/` so the manifest itself is not served under the immutable
rule.
