"""Source-linked practical reading. No browser code, submissions or external requests."""
from datetime import date, datetime, timezone
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ID = re.compile(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*')
SCOPES = {'website-now': 'Website Now', 'reader-controlled': 'Work You Control', 'future-app': 'Proposed App Workflow'}

def text(value, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError('pathways: invalid or oversized text')
    return value

def ident(value):
    if not isinstance(value, str) or len(value)>80 or not ID.fullmatch(value):
        raise ValueError('pathways: invalid identifier')
    return value

def calendar(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        raise ValueError('pathways: invalid date')
    try: parsed=date.fromisoformat(value)
    except ValueError as error: raise ValueError('pathways: invalid date') from error
    if parsed>datetime.now(timezone.utc).date(): raise ValueError('pathways: future date')
    return value

def address(value):
    text(value,2000)
    try:
        p=urlsplit(value)
        if p.scheme!='https' or not p.hostname or p.username is not None or p.password is not None or p.port not in (None,443) or p.netloc.endswith(':'):
            raise ValueError('pathways: invalid HTTPS source')
        if '\\' in value or any(c.isspace() or ord(c)<33 or ord(c)==127 for c in value):
            raise ValueError('pathways: invalid URL characters')
    except (TypeError,ValueError) as error: raise ValueError('pathways: invalid source URL') from error
    return value

def array(value, minimum=0, maximum=32):
    if not isinstance(value,list) or not minimum<=len(value)<=maximum:
        raise ValueError('pathways: invalid bounded list')
    return value

def strings(value, minimum=1, maximum=12):
    for item in array(value,minimum,maximum): text(item)
    return value

def load(root, model):
    path=Path(root)/'data/nations/pathways.json'
    if path.stat().st_size>128*1024: raise ValueError('pathways: catalogue exceeds128KiB')
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or type(data.get('version')) is not int or data['version']!=1:
        raise ValueError('pathways: unsupported version')
    text(data.get('title'),180);strings(data.get('intro'),1,4)
    capabilities=data.get('capabilities')
    if not isinstance(capabilities,dict): raise ValueError('pathways: missing capability boundaries')
    for key in ('now','limits','future'): strings(capabilities.get(key),1,8)
    known={n['id']:{f['id'] for f in n['facts']} for n in model.raw['nations']}
    sources={}
    for source in array(data.get('sources'),1,32):
        if not isinstance(source,dict):raise ValueError('pathways: invalid source')
        sid=ident(source.get('id'))
        if sid in sources:raise ValueError('pathways: duplicate source')
        text(source.get('title'),250);text(source.get('publisher'),250)
        address(source.get('url'));calendar(source.get('reviewed'))
        if 'as_of' in source:calendar(source['as_of'])
        if 'nation' in source and (not isinstance(source['nation'],str) or source['nation'] not in known):raise ValueError('pathways: unknown source Nation')
        sources[sid]=source
    def references(value):
        refs=array(value,1,8)
        if any(not isinstance(s,str) or s not in sources for s in refs) or len(set(refs))!=len(refs):
            raise ValueError('pathways: unknown or duplicate source reference')
        return refs
    chapters=[]; seen=set()
    for item in array(data.get('chapters'),1,12):
        if not isinstance(item,dict):raise ValueError('pathways: invalid chapter')
        cid=ident(item.get('id'))
        if cid in seen:raise ValueError('pathways: duplicate chapter')
        seen.add(cid)
        text(item.get('title'),180);text(item.get('intro'))
        text(item.get('deliverable'));text(item.get('reflection'));strings(item.get('verify'),1,8)
        required=set(references(item.get('source_ids')))
        for step in array(item.get('steps'),1,8):
            if not isinstance(step,dict) or not isinstance(step.get('scope'),str) or step['scope'] not in SCOPES:raise ValueError('pathways: invalid step scope')
            text(step.get('title'),180);text(step.get('text'))
            required.update(references(step.get('source_ids')))
        for example in array(item.get('examples',[]),0,4):
            if not isinstance(example,dict) or not isinstance(example.get('nation'),str) or example['nation'] not in known:raise ValueError('pathways: unknown example Nation')
            facts=array(example.get('fact_ids'),1,4)
            if any(not isinstance(f,str) for f in facts) or len(facts)!=len(set(facts)) or not set(facts)<=known[example['nation']]:
                raise ValueError('pathways: unknown, empty or duplicate example fact')
            if 'practice' in example:
                practice=example['practice']
                if not isinstance(practice,dict) or set(practice)!={'question','steps','boundary','reflection'}:
                    raise ValueError('pathways: invalid practice fields')
                for key in ('question','boundary','reflection'):text(practice[key])
                strings(practice['steps'],1,8)
        # All required evidence is validated first. Named source holds hide the complete dependent chapter.
        if any(sources[s].get('nation') and sources[s]['nation'] not in model.by_id for s in required):continue
        chapters.append(item)
    visible_sources={sid:s for sid,s in sources.items() if not s.get('nation') or s['nation'] in model.by_id}
    return data,chapters,visible_sources

def stamp(value):
    return '<time datetime="'+escape(value,quote=True)+'">'+date.fromisoformat(value).strftime('%d %b %Y').lstrip('0')+'</time>'

def ext(url,label):
    return '<a href="'+escape(url,quote=True)+'" target="_blank" rel="noopener noreferrer">'+escape(label)+'</a>'

def visible_examples(chapter, model):
    result=[]
    for example in chapter.get('examples',[]):
        nation=model.by_id.get(example['nation'])
        if not nation:continue
        facts={f['id']:f for f in nation['facts']}
        if all(fid in facts for fid in example['fact_ids']):
            result.append((example,nation,[facts[fid] for fid in example['fact_ids']]))
    return result


def render(root, model):
    data,chapters,sources=load(root,model);e=escape
    cases={c['id']:visible_examples(c,model) for c in chapters}
    out=['<div class="pathways">','<header class="pw-hero">',
         '<p class="eyebrow">Truth · Dignity · Sovereignty</p><h1 class="page-h">'+e(data['title'])+'</h1>']
    out.extend('<p class="pw-lede">'+e(p)+'</p>' for p in data['intro'])
    out+=['<div class="pw-entry"><a class="pill" href="#pw-chapters">Choose A Starting Point ↓</a>',
          '<a class="txt-link" id="pw-brief" href="/static/nations/action-brief.txt" download>Download The Action Brief ↗</a></div>',
          '<ol class="pw-route" aria-label="From Reading To A Decision"><li>Choose A Need</li><li>Check The Evidence</li><li>Prepare A Concrete Ask</li><li>Decide And Review</li></ol></header>',
          '<section class="pw-capabilities" aria-label="What Is Available And What Is Proposed">']
    for key,title in [('now','Available On This Website'),('limits','Clear Boundaries'),('future','App Workflows Are Proposed')]:
        out.append('<div class="pw-capability"><p class="eyebrow">'+e(title)+'</p>')
        out.extend('<p>'+e(p)+'</p>' for p in data['capabilities'][key]);out.append('</div>')
    out.append('</section>')
    if any(cases.values()):
        out+=['<section class="pw-case-index" aria-label="Examples In This Guide"><div><p class="eyebrow">From Evidence To A Useful Question</p><h2>Start With A Sourced Example.</h2><p>Read what a Nation has published, then try a hypothetical planning exercise. These are learning examples, not ZOTHEOS interventions, promised outcomes or permission to act for a Nation.</p></div><ul>']
        for c in chapters:
            if cases[c['id']]:
                names=', '.join(n['name'] for _,n,_ in cases[c['id']])
                out.append('<li><a href="#pw-cases-'+e(c['id'],quote=True)+'"><span>'+e(c['title'])+'</span><small>'+e(names)+'</small><span aria-hidden="true">↓</span></a></li>')
        out.append('</ul></section>')
    out+=['<div class="pw-layout" id="pw-chapters"><nav class="pw-index" aria-label="In This Guide"><p class="eyebrow">Choose A Starting Point</p><ol>']
    out.extend('<li><a href="#pw-'+e(c['id'],quote=True)+'">'+e(c['title'])+'</a></li>' for c in chapters)
    out+=['</ol><p>One continuous guide. Every chapter is open to read.</p></nav><div class="pw-reading">']
    for number,c in enumerate(chapters,1):
        target='pw-'+c['id']
        out+=['<section class="pw-chapter" aria-labelledby="'+e(target,quote=True)+'">',
              '<p class="eyebrow">Pathway '+str(number).zfill(2)+'</p><h2 id="'+e(target,quote=True)+'" tabindex="-1">'+e(c['title'])+'</h2>',
              '<p class="pw-intro">'+e(c['intro'])+'</p><div class="pw-steps">']
        for step in c['steps']:
            out+=['<article class="pw-step pw-'+e(step['scope'],quote=True)+'"><p class="pw-scope">'+SCOPES[step['scope']]+'</p>',
                  '<h3>'+e(step['title'])+'</h3><p>'+e(step['text'])+'</p></article>']
        out+=['</div><div class="pw-result"><p class="eyebrow">Something You Can Prepare</p><p>'+e(c['deliverable'])+'</p></div>',
              '<div class="pw-verify"><h3>Who Decides And What To Verify</h3><ul>']
        out.extend('<li>'+e(p)+'</li>' for p in c['verify'])
        out+=['</ul></div><aside class="pw-reflection" aria-label="Reflection"><span class="eyebrow">Reflection</span><p>'+e(c['reflection'])+'</p></aside>']
        if cases[c['id']]:
            out.append('<section class="pw-cases" aria-label="Sourced Examples"><h3 class="pw-case-heading" id="pw-cases-'+e(c['id'],quote=True)+'" tabindex="-1">A Published Account. A Practical Starting Point.</h3>')
        for example,nation,facts in cases[c['id']]:
            out.append('<article class="pw-example"><p class="eyebrow">From The Nation&#39;s Own Published Account</p><h3><a href="/nations/'+e(nation['id'],quote=True)+'">'+e(nation['name'])+'</a></h3>')
            for fact in facts:
                receipt=ext(address(fact['url']),fact['title'])+' · '+e(fact['publisher'])
                receipt+=(' · Checked By A Person On ' if fact.get('human') else ' · Checked ')+stamp(fact['date'])
                if fact.get('as_of'):receipt+=' · As Of '+e(str(fact['as_of']))
                if fact.get('grace') and fact.get('note'):
                    receipt+=' · The tool could not reach the page on '+stamp(fact['note'])
                out.append('<article class="pw-example-fact"><p>'+e(fact['text'])+'</p><p class="pw-receipt">'+receipt+'</p></article>')
            if 'practice' in example:
                practice=example['practice']
                out+=['<section class="pw-practice" aria-label="Hypothetical Planning Exercise"><p class="pw-scope">Hypothetical Planning Exercise · Work You Control</p><h4>Try This With The Evidence</h4>',
                      '<p class="pw-question">'+e(practice['question'])+'</p><ol>']
                out.extend('<li>'+e(step)+'</li>' for step in practice['steps'])
                out+=['</ol><p class="pw-boundary"><strong>What This Does Not Establish</strong> '+e(practice['boundary'])+'</p>',
                      '<p class="pw-practice-reflection"><strong>Reflect</strong> '+e(practice['reflection'])+'</p>',
                      '<a class="pw-brief-link" href="#pw-brief">Use The Blank Action Brief ↑</a></section>']
            out.append('</article>')
        if cases[c['id']]:out.append('</section>')
        refs=list(dict.fromkeys(c['source_ids']+[s for step in c['steps'] for s in step['source_ids']]))
        out.append('<div class="pw-sources"><h3>Sources And Further Reading</h3><ul>')
        for sid in refs:
            source=sources[sid]
            out.append('<li>'+ext(source['url'],source['title'])+'<span>'+e(source['publisher'])+' · Source Checked '+stamp(source['reviewed'])+((' · Context Dated '+stamp(source['as_of'])) if source.get('as_of') else '')+'</span></li>')
        out+=['</ul><p>Sources support the stated context. Planning steps and proposed workflows are ZOTHEOS suggestions; they are not endorsements by the cited organizations.</p></div>',
              '<a class="pw-back" href="#pw-chapters">Back To The Guide ↑</a></section>']
    out+=['</div></div><section class="pw-next" aria-labelledby="pw-next-title"><h2 id="pw-next-title">Choose One Useful Next Step.</h2>',
          '<p>Use the blank brief to record the question, the people with authority, the sources and what still needs checking. Fill it offline in a place you control. This page has no form or upload and does not receive your answers.</p>',
          '<div class="pw-links"><a class="pill" href="/nations/directory">Find A Nation’s Own Sources</a><a class="pill" href="/nations/resources">Keep Reading</a><a class="pill" href="/nations/for-nations">Corrections From Nations</a><a class="pill" href="/nations/coverage">Coverage And Gaps</a><a class="pill" href="/download">App Release Status</a></div>',
          '<p class="pw-receipt">Read online or use your browser’s Print option to keep a reading copy. Source-check dates record when a source was read; they do not make every rule, program or historical statement current.</p></section></div>']
    return '\n'.join(out)

def action_brief(root, model):
    data,chapters,sources=load(root,model)
    out=['ZOTHEOS | ACTION BRIEF','https://zotheos.org/nations/paths-to-action','',
         'A blank planning aid. Write offline in a place you control. This is not a submitted application, legal advice, community consent or a completed action.','',
         'Question or need: ____________________','Who is affected: ____________________',
         'Who has authority to decide and authorize this work: ____________________',
         'Requested change: ____________________','Sources, exact page references and actual check dates: ____________________',
         'What remains uncertain or disputed: ____________________','Permissions and information that must stay private: ____________________',
         'Verified deadline / next review date and source: ____________________','Responsible person or institution: ____________________',
         'Resources and ongoing responsibilities: ____________________','How affected people will evaluate, correct or stop the work: ____________________',
         'Next step I choose: ____________________','', 'PATHWAYS IN THIS EDITION','']
    for c in chapters:
        out+=[c['title'],'Prepare: '+c['deliverable'],'Reflect: '+c['reflection']]
        for sid in dict.fromkeys(c['source_ids']+[sid for step in c['steps'] for sid in step['source_ids']]):
            s=sources[sid];out.append(s['title']+' | '+s['url']+' | Source checked '+s['reviewed'])
        out.append('')
    out+=['Proposed app workflows are not released services. Check the original sources and current requirements with appropriate local expertise.','']
    return '\n'.join(out)
