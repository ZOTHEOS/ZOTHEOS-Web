# Releasing and updating zotheos.org

One tool does the routine work: `tools/release.py`. It edits `index.html`, `download.html` and `vercel.json` for you,
checks everything, and shows you what changed before anything is saved.

Run every command from PowerShell in `C:\ZOTHEOS-Web`, with Python 3.10:

```powershell
cd C:\ZOTHEOS-Web
py -3.10 tools\release.py show          # what the site says right now (writes nothing)
```

Add `--dry-run` to any command to see the diff and the checks without writing. Use it the first few times.

## The two states

The site is always in one of two release states, set on `<html data-release>` in both pages:

| State | The one button reads | Status line under the hero | /download shows |
|---|---|---|---|
| `prerelease` (now) | Join the release list (to #waitlist) | Windows desktop: internal testing, Updated Oct 4, 2026 | its summary, the status card, the dated Updates log |
| `available` | Download for Windows, v1.0.0, 904 MB (to the installer) | Windows desktop v1.0.0, installer and checksum | file, size, SHA-256, download |

Both versions of every affected line already exist in the pages. CSS shows one of them, so switching is one
attribute plus the release details. No page script decides it.

## Post an update

1. Write the entry. It goes at the top of the Updates log on /download.html, with its date.

   ```powershell
   py -3.10 tools\release.py log --title "Clean-machine install checked" `
       --body "First paragraph." --body "Second paragraph." --date 2026-10-14 --dry-run
   ```

   For longer notes, put the text in a file (blank lines between paragraphs) and use `--body-file notes.txt`.
   Save it as UTF-8 (`Set-Content notes.txt -Encoding utf8`, or Save As UTF-8 in your editor); the UTF-16 that
   PowerShell's `>` writes is read too. Without `--date`, today is used. A date after tomorrow is refused.

2. Read the "Still says" list the dry run prints. A newer entry moves the "Updated" date in the hero and on
   /download, and the release page's fixed development copy then sits under that new date: its summary (the
   sentence under the heading, also its search description), the "What still needs to work" list, the
   installation notes, the landing's search text. Each line comes with its `file:line`. Then:

   - all still true: run again without `--dry-run`, adding `--summary-unchanged`;
   - the summary changed: add `--summary "The new one or two sentences."` (it also becomes the search description,
     with the date in front);
   - anything else changed (a list item done, a paragraph out of date): edit it by hand in `download.html` first,
     then run with `--summary-unchanged` or `--summary`;
   - the entry should not move the date: add `--keep-date`.

   A real run that moves the date without one of these is refused, so a new date never lands on copy nobody read.

3. Change the one-line status if it moved. The hero shows it as "Windows desktop: <status>", so give only the part
   after the colon, in lower case. 22 characters at most; 17 or fewer fit even the smallest phones (320 px), and
   past that the line ends in an ellipsis there, cutting the date short:

   ```powershell
   py -3.10 tools\release.py status "clean-machine checks"
   ```

   On its own, `status "<text>"` keeps the date. To move it too: `--date 2026-10-14` (or `--date today`), with
   `--summary-unchanged` or `--summary` as in step 2. Or do it all with the entry: `log ... --status "clean-machine checks"`.

An older date slots into the log below newer entries and leaves the dates alone. Posting the same title on the same
date twice is refused.

To fix or remove an entry, edit its `<li class="update">` in `download.html` by hand. Keep its shape: the opening
`<li class="update" id="update-YYYY-MM-DD">`, the `<h3>` title, the `<time datetime="YYYY-MM-DD">` date, and `</li>`
on its own line at the same indent. Then run `py -3.10 tools\release.py check`: it fails if an entry no longer reads
as one entry, if two share an id, or if the dates are not newest first.

## Ship a release

1. Build and test the installer. Put it where it will be served, and get its address: a path on this site such as
   `/download/ZOTHEOS_Setup_1.0.0_x64.exe`, or an `https://` address. A large installer may exceed what the site's
   hosting accepts, so confirm where it lives first. A site path must exist in this repo (the tool refuses a path
   that would 404; `--allow-missing` only when another step deploys the file there). The tool cannot check another
   host: for an `https://` address, open it in a browser and confirm it downloads the same file before you push.
2. Switch the site, with the exact file you uploaded:

   ```powershell
   py -3.10 tools\release.py go-live --version 1.0.0 --url /download/ZOTHEOS_Setup_1.0.0_x64.exe `
       --installer C:\ZOTHEOS\release\ZOTHEOS_Setup_1.0.0_x64.exe --dry-run
   ```

   `--installer` measures the size and the SHA-256 from the file itself. Without the file at hand, pass
   `--size "904 MB" --sha256 <64 hex digits>` (PowerShell: `Get-FileHash <file> -Algorithm SHA256`). When you pass
   both, the tool refuses if the size or the checksum and the file disagree. A site path that is in the repo is
   measured the same way.
3. Read the "Becomes visible" list the dry run prints: the release copy every visitor will now read. Every sentence
   must be true for this installer. Edit any that is not (its `file:line` is listed) before you go on.
4. Drop `--dry-run`, then post a log entry saying the release is out.

go-live flips both pages, fills the version, size, file name, checksum and link everywhere they appear, updates the
link previews and the search data (JSON-LD), and re-hashes the CSP.

## Roll back

```powershell
py -3.10 tools\release.py prerelease                    # back to "Join the release list"; details kept for next time
py -3.10 tools\release.py prerelease --clear-details    # the installer was pulled: remove its link and checksum too
```

If nothing else changed in between, `prerelease --clear-details` returns all three files byte for byte to how they
were before go-live (tested). The log keeps its entries: they are dated history. The development copy from before
the release shows again with its old date (the tool lists it): post a log entry or a status that says what is true
now. If something else went wrong, `git revert` the commit and push.

## Publish

After any command: open both pages locally and look (for example `py -3.10 -m http.server 8000`, then
http://localhost:8000/ and http://localhost:8000/download.html), then commit and push to the branch the live site
deploys from.

## The CSP rule

The pages allow only scripts whose SHA-256 is listed in their Content-Security-Policy, in two places: the `<meta>` tag
in each page and the headers in `vercel.json`. Change one character inside an inline `<script>` (the JSON-LD block
counts) and the browser silently refuses that script until the hash is updated.

- `release.py` re-hashes for you on every command.
- After editing any inline script by hand, run `py -3.10 tools\csp_sync.py`, then `py -3.10 tools\csp_sync.py --check`.
- `download.html` has no scripts and stays `script-src 'none'`.

## What every command checks

Each command builds the new pages in a temporary copy, and writes your files only when all of these pass there:

- `csp_sync --check`: the CSP hashes match the inline scripts in both pages and in `vercel.json`.
- `lint_copy`: no em dash anywhere a visitor or a search engine can see. Use a comma, a colon or a period.
- the release switch check (`tools/release_switch.py --check`): both pages in the same state, no placeholder left
  while available, no wording of the other state showing. The Updates log is exempt: it is dated history.
- the log and status slots: every log entry reads as one entry, ids unique, dates newest first; every status slot
  says the same thing and carries the same date on both pages.

It also refuses when a page changed on disk while it ran (an editor saved it): run it again.
`py -3.10 tools\release.py check` runs the same checks on the files as they are.

## Copy

Calm, factual, dated. Say what was built or checked, and what still needs to work. Name only what is true at that
date, and keep civic or wider hopes framed as possibility.
