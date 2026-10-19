"""The hero's four captions fit a 320px phone (Task B, Living Gallery).

Each caption was a fixed --fw-wide box with its word centred inside. On a tall 320px phone the stage reaches its
340px height, the boxes reach 3.5px past each side, and the right pair widened the page to 324px, so phone Chrome
scaled the whole page down. Each box is now its own words, centred on the same point (fx + fw / 2 from the axis),
so every glyph stands where it did (measured in Chrome: within 0.03px at 320 and 1440) and nothing passes the page.
"""
import os
from pathlib import Path
import re

R = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
PAGE = (R / 'index.html').read_text(encoding='utf-8')
CSS = re.sub(r'/\*.*?\*/', '', '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', PAGE, re.S)), flags=re.S)


def test_each_caption_box_is_its_own_words_centred_where_the_old_box_centred_them():
    assert '.forge-mind { width: max-content; text-align: center; text-indent: 0.34em; }' in CSS
    assert '.fm-tl, .fm-bl { right: calc(50% + var(--fx) + var(--fw) / 2); transform: translate(50%, -50%); }' in CSS
    assert '.fm-tr, .fm-br { left: calc(50% + var(--fx) + var(--fw) / 2); transform: translate(-50%, -50%); }' in CSS
    # No later rule gives a caption a width, a side anchor or a transform that would move it off that centre.
    at = CSS.index('.fm-tr, .fm-br { left: calc(50% + var(--fx) + var(--fw) / 2)')
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', CSS[at:]):
        if re.search(r'\.(forge-mind|fm-(tl|tr|bl|br)|forge-you)(?![\w-])', sel):
            if 'max-content' in body or 'var(--fw) / 2' in body:
                continue
            assert not re.search(r'(^|[;\s])(width|left|right|transform)\s*:', body), sel.strip()


def test_the_four_captions_keep_their_words():
    for cls, word in (('fm-tl', 'Analyst'), ('fm-tr', 'Skeptic'), ('fm-bl', 'Humanist'), ('fm-br forge-you', 'You')):
        assert re.search(r'<span class="forge-mind ' + cls + r'"[^>]*>' + word + '</span>', PAGE), word
