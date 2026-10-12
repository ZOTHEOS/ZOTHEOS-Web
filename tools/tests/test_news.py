import datetime as dt
import json

import news_fetch as N

ITEMS = "".join(f"<item><title>Story {i}</title><link>https://ictnews.org/news/s{i}</link>"
                f"<pubDate>Sat, 10 Oct 2026 0{i % 10}:00:00 GMT</pubDate></item>" for i in range(12))
RSS = ("<?xml version='1.0'?><rss version='2.0'><channel><title>ICT</title><language>en-us</language>"
       "<item><title>Tribes meet &#8212; and agree</title><link>https://ictnews.org/news/one?utm_source=rss&amp;id=4</link>"
       "<pubDate>Sun, 11 Oct 2026 10:00:00 GMT</pubDate><description>dropped</description></item>"
       "<item><title>Same story again</title><link>https://ictnews.org/news/one?id=4&amp;fbclid=zz</link>"
       "<pubDate>Sun, 11 Oct 2026 09:00:00 GMT</pubDate></item>"
       "<item><title>From the future</title><link>https://ictnews.org/news/future</link><pubDate>Fri, 16 Oct 2026 10:00:00 GMT</pubDate></item>"
       "<item><title>Too old</title><link>https://ictnews.org/news/old</link><pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate></item>"
       "<item><title>Elsewhere</title><link>https://evil.example/news</link><pubDate>Sun, 11 Oct 2026 10:00:00 GMT</pubDate></item>"
       "<item><title><![CDATA[<b>Bold</b> &amp; plain]]></title><link>http://ictnews.org/news/plain</link>"
       "<pubDate>Sun, 11 Oct 2026 10:00:00 GMT</pubDate></item>" + ITEMS + "</channel></rss>")
ATOM = ("<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom' xml:lang='mi'><title>W</title>"
        "<entry><title>Kōrero hou</title><link rel='alternate' href='https://waateanews.com/a'/>"
        "<updated>2026-10-11T08:00:00Z</updated></entry></feed>")
ICT = {"id": "ict", "name": "ICT", "allow": ["ictnews.org"], "region": "us", "lang": "en", "enabled": True,
       "leadership": {"evidence": "Native-led"}}
WAATEA = {"id": "waatea", "name": "Waatea News", "allow": ["waateanews.com"], "region": "oceania", "enabled": True,
          "leadership": {"evidence": "x"}}


def test_sanitize_allowlist_window_dedupe_and_cap():
    now = dt.datetime(2026, 10, 12, 12, 0, tzinfo=dt.timezone.utc)
    items = N.gather({"outlets": [ICT]}, now, lambda _o: RSS.encode())
    titles = [i["title"] for i in items]
    assert "Tribes meet - and agree" in titles                      # the em dash became a spaced hyphen
    assert "Same story again" not in titles                        # one canonical link, once
    assert not {"From the future", "Too old", "Elsewhere"} & set(titles)
    assert not any("Bold" in t for t in titles)                    # an http link is refused
    assert len(items) == 10                                        # at most 10 per outlet
    one = next(i for i in items if i["title"].startswith("Tribes"))
    assert one["link"] == "https://ictnews.org/news/one?id=4" and one["lang"] == "en" and one["date"] == "2026-10-11"
    assert set(one) == {"title", "link", "outlet", "date", "lang", "region"}


def test_atom_disabled_and_unled_outlets():
    now = dt.datetime(2026, 10, 12, tzinfo=dt.timezone.utc)
    off = dict(WAATEA, id="off", enabled=False)
    items = N.gather({"outlets": [WAATEA, off]}, now, lambda o: ATOM.encode())
    assert [(i["title"], i["lang"]) for i in items] == [("Kōrero hou", "mi")]
    assert N.gather({"outlets": [dict(WAATEA, leadership=None)]}, now, lambda o: ATOM.encode()) == []


def test_round_robin_by_region():
    now = dt.datetime(2026, 10, 12, 12, 0, tzinfo=dt.timezone.utc)
    feeds = {"ict": RSS.encode(), "waatea": ATOM.encode()}
    items = N.gather({"outlets": [ICT, WAATEA]}, now, lambda o: feeds[o["id"]])
    assert {items[0]["region"], items[1]["region"]} == {"us", "oceania"}


def test_hidden_shelf_polls_nothing(tmp_path):
    d = tmp_path / "data" / "news"
    d.mkdir(parents=True)
    (d / "flags.json").write_text('{"shelf_visible": false}')
    (d / "sources.json").write_text(json.dumps({"outlets": [dict(ICT, feed="https://example.invalid/")]}))
    assert N.main(["--root", str(tmp_path)]) == 0
    assert not (d / "headlines.json").exists()


def test_titles_are_capped():
    t = N.clean_title("word " * 60)
    assert len(t) <= 160 and t.endswith("...")
