"""Early preference hydration and late adapter palette are separate cascade requirements.

Static ordering guards do not certify computed contrast. The deliberately reordered in-memory
control reproduces the former palette-before-page-CSS failure without changing production files.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import os
import pytest

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))

class HeadAssets(HTMLParser):
    def __init__(self,text):
        super().__init__();self.text=text;self.starts=[0]
        for i,c in enumerate(text):
            if c=='\n':self.starts.append(i+1)
        self.rows=[];self.ordinal=0;self.in_head=False;self.in_noscript=0;self.active=None;self.feed(text)
    def source_offset(self):
        line,col=self.getpos();return self.starts[line-1]+col
    def handle_starttag(self,tag,attrs):
        self.ordinal+=1
        if tag=='head':self.in_head=True
        if tag=='noscript':self.in_noscript+=1
        if not self.in_head:return
        data={'tag':tag,'attrs':dict(attrs),'ordinal':self.ordinal,'start':self.source_offset(),'end':self.source_offset()+len(self.get_starttag_text()),'body':'','noscript':bool(self.in_noscript)}
        if tag in ('script','style'):
            self.active=data
        elif tag=='link'and data['attrs'].get('rel')=='stylesheet':self.rows.append(data)
    def handle_data(self,text):
        if self.active is not None:self.active['body']+=text
    def handle_endtag(self,tag):
        if self.active is not None and tag==self.active['tag']:
            self.active['end']=self.source_offset()+len('</'+tag+'>');self.rows.append(self.active);self.active=None
        if tag=='noscript':self.in_noscript-=1
        if tag=='head':self.in_head=False

def adapter_order(text):
    rows=HeadAssets(text).rows
    prepaint=[r for r in rows if r['tag']=='script'and r['attrs'].get('id')=='site-theme-prepaint']
    assert len(prepaint)==1,'Each adapter needs one early saved-preference script'
    early=prepaint[0]
    assert 'zotheos_landing_theme'in early['body']and'data-motion'in early['body']
    assert 'async'not in early['attrs']and'defer'not in early['attrs']
    styles=[r for r in rows if r['tag']=='style'or r['tag']=='link']
    assert styles and early['ordinal']<min(r['ordinal']for r in styles),'Saved preference must precede the first visible stylesheet'
    palette=[r for r in styles if(r['tag']=='link'and urlsplit(r['attrs'].get('href','')).path=='/static/appearance/palette.css')or(r['tag']=='style'and r['attrs'].get('id')=='site-appearance-styles')]
    assert len(palette)==1,'One local palette link or inline game palette must own named theme tokens'
    own_styles=[r for r in styles if r['tag']=='style'and r is not palette[0]and not r['noscript']]
    assert own_styles,'The adapter must retain the page’s original style blocks'
    assert max(r['ordinal']for r in own_styles)<palette[0]['ordinal'],'Named-theme palette must follow every original page style so inherited ink does not revert'
    if palette[0]['tag']=='link':
        source=urlsplit(palette[0]['attrs']['href']);assert not source.scheme and not source.netloc
    else:
        assert '[data-theme="codex"]'in palette[0]['body']and'--ink-2:'in palette[0]['body']
    return early,palette[0],own_styles

@pytest.mark.parametrize('rel',['download.html','game/index.src.html'])
def test_adapter_hydrates_early_but_named_palette_wins_after_original_page_styles(rel):
    text=(R/rel).read_text(encoding='utf8')
    early,palette,own_styles=adapter_order(text)
    # Negative control: put just the palette immediately before the page's last own style,
    # keeping the prepaint script in its valid early position. This was the real contrast bug.
    pivot=max(own_styles,key=lambda row:row['start'])['start']
    assert early['end']<=pivot<palette['start']
    block=text[palette['start']:palette['end']]
    without=text[:palette['start']]+text[palette['end']:]
    broken=without[:pivot]+block+'\n'+without[pivot:]
    with pytest.raises(AssertionError,match='palette must follow'):
        adapter_order(broken)
