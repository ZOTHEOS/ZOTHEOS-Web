import sys, re, unicodedata, io
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("­", "")  # soft hyphen
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s)
    return s.lower()

def load(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    # de-hyphenate line-break hyphens: "exam-\n ple" -> "example"
    raw2 = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", raw)
    return norm(raw2)

iwgia = sys.argv[1]
tanger = sys.argv[2]
souss = sys.argv[3]
texts = {"iwgia": load(iwgia), "tanger": load(tanger), "souss": load(souss)}

checks = [
 ("afar0", "iwgia", "which has an Afar population of 1.8 million"),
 ("afar1", "iwgia", "inhabited their traditional territories for approximately 2,000 years"),
 ("benet0", "iwgia", "inhabited Mount Elgon for over 500 years"),
 ("benet2", "iwgia", "ordering the UWA to cease evictions and raids on the community"),
 ("karimojong0", "iwgia", "live in the north-east of the country (mainly drylands)"),
 ("tshwa0", "iwgia", "indicate that there are 3,207 Tshwa and 1,579 Doma"),
 ("tshwa1", "iwgia", "Work was done on the Tjwao language by the"),
 ("korana1", "iwgia", "the Koranna mainly in Kimberley and the Free State province"),
 ("griqua0", "iwgia", "the Griqua in the Western Cape, Eastern Cape, Northern Cape, Free State"),
 ("bagyeli0", "iwgia", "particularly in the districts of Akom II, Bipindi, Kribi and Lolodorf"),
 ("iqbayliyen0", "iwgia", "Kabyls represent around 50% of Algeria’s Amazigh population"),
 ("toubou0", "iwgia", "who are originally from the Tibesti plateau in Chad"),
 ("toubou1", "iwgia", "practise pastoralism across an area that extends from northern Niger"),
 ("baka0", "iwgia", "grant access for Baka communities living around the Lobéké National Park"),
 ("baka1", "iwgia", "nine ethnic groups (Baka, Babongo, Bakoya, Baghame, Barimba, Akoula, Akowa,"),
 ("khoikhoi0", "iwgia", "now exercising their right to self-identification"),
 ("mbuti0", "iwgia", "as the first inhabitants of the national rainforests"),
 ("khwe0_xun0", "iwgia", "who reside primarily in Platfontein, Kimberley"),
 ("khwe1", "iwgia", "Khwe San in and around Bwabwata National Park"),
 ("xun1", "iwgia", "Each of the San groups speaks its own language"),
 ("irifiyen0", "tanger", "Le Tarifit est plus utilisé à la province d’Al Hoceima (53,6%)"),
 ("irifiyen1", "tanger", "Tarifit 7,5 8,2 7,8 3,1 3,3 3,2"),
 ("ishelhin1", "tanger", "Tachelhit 1,6 1,4 1,5 14,2 14,2 14,2"),
 ("ishelhin0", "souss", "Darija 82,1 76,3 79,2 Tachelhit 62,9 63,5 63,2"),
]

W = 450
for label, key, phrase in checks:
    t = texts[key]
    p = norm(phrase)
    idxs = [m.start() for m in re.finditer(re.escape(p), t)]
    print("=" * 100)
    print(f"[{label}] ({key}) phrase: {phrase!r}")
    if not idxs:
        print("  >>> NOT FOUND verbatim. Trying key tokens:")
        toks = [w for w in re.findall(r"[a-z0-9,\.%]+", p) if len(w) > 3][:4]
        for tok in toks:
            hits = [m.start() for m in re.finditer(re.escape(tok), t)][:3]
            for h in hits:
                print(f"    tok {tok!r} @ {h}: ...{t[max(0,h-200):h+250]}...")
    else:
        print(f"  FOUND x{len(idxs)}")
        for i in idxs[:2]:
            print(f"  @ {i}: ...{t[max(0,i-W):i+len(p)+W]}...")

# extra context searches for fact-level checks
extras = [
 ("iwgia", "1.8 million"), ("iwgia", "1.09"), ("iwgia", "karimojong"), ("iwgia", "3,207"),
 ("iwgia", "asbabuk"), ("iwgia", "50,000 toubou"), ("iwgia", "12,000"), ("iwgia", "coloured"),
 ("iwgia", "mbuti"), ("iwgia", "platfontein"), ("iwgia", "bwabwata"), ("iwgia", "kabyl"),
 ("iwgia", "prime minister"), ("iwgia", "tjwao"), ("iwgia", "koisan"), ("iwgia", "koranna"),
 ("iwgia", "griqua"), ("iwgia", "2,000 years"), ("iwgia", "tibesti"), ("iwgia", "self-identification"),
 ("tanger", "tarifit"), ("tanger", "tachelhit"), ("souss", "tachelhit"), ("souss", "darija"),
 ("tanger", "langues"), ("souss", "langues"),
]
print("\n\n" + "#" * 100 + "\nEXTRA CONTEXT\n")
for key, tok in extras:
    t = texts[key]
    hits = [m.start() for m in re.finditer(re.escape(tok.lower()), t)]
    print("-" * 100)
    print(f"[{key}] {tok!r}: {len(hits)} hits")
    for h in hits[:6]:
        print(f"  @ {h}: ...{t[max(0,h-300):h+350]}...")
