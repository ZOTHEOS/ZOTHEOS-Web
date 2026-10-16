"""The new catalogue extends exact source URLs, not whole-host trust.

Integration supplement written after the original43-case prebuild proof.
No requests are made: the actual local-link gate runs over fictional files.
"""
import json

from test_indigenous_pathways import fixture_catalogue
import nations_links


def miniature_site(tmp_path, url):
    data = tmp_path/'data/nations'
    data.mkdir(parents=True)
    (data/'nations.json').write_text(json.dumps({'nations':[]}), encoding='utf8')
    (data/'site.json').write_text(json.dumps({'contact':'fictional@example.test','repo_public':False}), encoding='utf8')
    (data/'pathways.json').write_text(json.dumps(fixture_catalogue()), encoding='utf8')
    page = tmp_path/'nations/paths-to-action.html'
    page.parent.mkdir()
    page.write_text('<main><a href="'+url+'" rel="noopener noreferrer" target="_blank">Original Source</a></main>', encoding='utf8')
    return page


def test_link_gate_accepts_exact_source_in_pathways_catalogue(tmp_path):
    miniature_site(tmp_path, 'https://publisher.example.test/river')
    assert nations_links.main(['--root',str(tmp_path)]) == 0


def test_same_source_host_does_not_allow_an_uncited_path_or_query(tmp_path):
    miniature_site(tmp_path, 'https://publisher.example.test/river?uncited=yes')
    assert nations_links.main(['--root',str(tmp_path)]) == 1


def test_native_plain_text_download_resolves_as_real_file(tmp_path):
    page = miniature_site(tmp_path, 'https://publisher.example.test/river')
    textfile = tmp_path/'static/nations/action-brief.txt'
    textfile.parent.mkdir(parents=True)
    textfile.write_text('An offline blank brief.\n', encoding='utf8')
    page.write_text('<main><a href="/static/nations/action-brief.txt" download>Download</a></main>', encoding='utf8')
    assert nations_links.main(['--root',str(tmp_path)]) == 0
