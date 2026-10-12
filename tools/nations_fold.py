#!/usr/bin/env python3
"""The search fold for /nations, written once here and emitted into the hub's herald.js (DESIGN_NATIONS 7.1).

fold(s) = NFKD -> drop Mn (combining marks) -> casefold
          -> drop  ' ʻ ʼ ’ ` ˊ · ‧ ʔ ǀ ǁ ǂ  and the digit 7 only when it stands between letters
          -> map   ł->l ø->o æ->ae œ->oe ß->ss ŋ->ng ɨ->i ə->e ʉ->u ɬ->l ɫ->l ɓ->b ɗ->d θ->th ⁿ->n
          -> any other punctuation or symbol separates words; collapse whitespace; split into tokens

Folding is for matching and sorting only. A displayed name is never folded or altered.
No fuzzy matching: a query token matches a word only as a prefix of that word.

Usage: python tools/nations_fold.py "Sḵwx̱wú7mesh Úxwumixw"     prints the folded tokens
       python tools/nations_fold.py --js                         prints the JavaScript fold (what the build emits)
"""
import json
import sys
import unicodedata

DROP = "'ʻʼ’`ˊ·‧ʔǀǁǂ"
MAP = {"ł": "l", "ø": "o", "æ": "ae", "œ": "oe", "ß": "ss", "ŋ": "ng", "ɨ": "i", "ə": "e", "ʉ": "u",
       "ɬ": "l", "ɫ": "l", "ɓ": "b", "ɗ": "d", "θ": "th", "ⁿ": "n"}


def _is_letter(c):
    return unicodedata.category(c).startswith("L")


def fold(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.casefold()
    s = "".join(c for c in s if c not in DROP)
    out = []
    for i, c in enumerate(s):
        if c == "7" and 0 < i < len(s) - 1 and _is_letter(s[i - 1]) and _is_letter(s[i + 1]):
            continue
        out.append(MAP.get(c, c))
    s = "".join(out)
    s = "".join(" " if unicodedata.category(c)[0] in "PSZC" else c for c in s)
    return " ".join(s.split())


def tokens(s):
    return fold(s).split()


def sort_key(s):
    return (fold(s), s)


def js():
    """The same fold in JavaScript (ES2017 plus Unicode property escapes, which every current browser has).
    JavaScript has no casefold: toLowerCase() is used, then the two differences that matter for this data are
    undone (Cherokee small letters fold to capitals, as Unicode case folding does; ß is in the map)."""
    drop = json.dumps(DROP)
    mp = json.dumps(MAP, ensure_ascii=False, sort_keys=True)
    return (
        "var FOLD_DROP = " + drop + ";\n"
        "var FOLD_MAP = " + mp + ";\n"
        "var RE_MN = /\\p{Mn}/gu, RE_SEP = /[\\p{P}\\p{S}\\p{Z}\\p{C}]/gu, RE_L = /\\p{L}/u;\n"
        "function fold(s) {\n"
        "  s = String(s).normalize('NFKD').replace(RE_MN, '').toLowerCase();\n"
        "  var o = '', i, c, k, a = Array.from(s), b = [];\n"
        "  for (i = 0; i < a.length; i++) {\n"
        "    c = a[i]; k = c.codePointAt(0);\n"
        "    if (k >= 0xAB70 && k <= 0xABBF) c = String.fromCodePoint(k - 0xAB70 + 0x13A0);\n"
        "    else if (k >= 0x13F8 && k <= 0x13FD) c = String.fromCodePoint(k - 8);\n"
        "    if (FOLD_DROP.indexOf(c) < 0) b.push(c);\n"
        "  }\n"
        "  for (i = 0; i < b.length; i++) {\n"
        "    c = b[i];\n"
        "    if (c === '7' && i > 0 && i < b.length - 1 && RE_L.test(b[i - 1]) && RE_L.test(b[i + 1])) continue;\n"
        "    o += Object.prototype.hasOwnProperty.call(FOLD_MAP, c) ? FOLD_MAP[c] : c;\n"
        "  }\n"
        "  return o.replace(RE_SEP, ' ').split(/\\s+/).filter(Boolean).join(' ');\n"
        "}\n"
    )


if __name__ == "__main__":
    if "--js" in sys.argv:
        sys.stdout.write(js())
    else:
        for a in sys.argv[1:]:
            print(json.dumps(tokens(a), ensure_ascii=False))
