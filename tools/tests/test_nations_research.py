"""Queue safety and unit distinctions. Stdlib unittest; pytest can collect this too."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nations_research as research


class ResearchQueue(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='zotheos-research-test-', dir=os.environ.get('ZOTHEOS_TEST_TMP'))
        self.root = Path(self.temp.name)
        self.folder = self.root / research.DATA
        self.folder.mkdir(parents=True)
        self.registry = self.root / 'data/nations/nations.json'
        self.registry.write_text(json.dumps({'nations':[{'id':'nuche','name':'Nuche','region':'southwest',
                                  'countries':['US'],'facts':[]}]}))
        self.initial = self.registry.read_bytes()
        source = {'source_id':'s','entity_unit':'federally_listed_tribal_entity','url':'https://www.govinfo.gov/list',
                  'allowed_hosts':['www.govinfo.gov'],'stated_count':1,'as_of':'2026-01-30'}
        self.save('directory_sources.json', {'sources':[source]})
        entities = []
        for n in (1,2):
            entities.append({'directory_id':str(n),'name':'Government '+str(n),'entity_type':'federally_listed_tribal_entity',
                             'countries':['US'],'directory_group':'contiguous','official_url':None,
                             'registry_crosswalk':{'status':'unreviewed','registry_id':None,'candidates':[{'registry_id':'nuche','basis':'exact_name_or_alias'}]}})
        self.save('us_federal_directory.json', {'entities':entities,'stated_count':1,'enumerated_count':2,
                  'group_counts':{'contiguous':2},'count_discrepancy':{'status':'unresolved'}})
        tasks = []
        for n,region in ((1,'americas'),(2,'americas'),(3,'africa'),(4,'asia')):
            tasks.append({'task_id':str(n),'task_type':'entity_profile','subject':'A '+str(n),'entity_id':'1','entity_type':'federally_listed_tribal_entity',
                          'countries':['US'],'region':region,'priority':50,'status':'pending','allowed_source_ids':['s'],
                          'risk':{'status':'unassessed','signals':[]},'receipts':[],'next_attempt_after':None})
        self.save('coverage_queue.json', {'max_subjects_per_run':3,'tasks':tasks})

    def tearDown(self):
        self.assertEqual(self.registry.read_bytes(), self.initial, 'Research must never edit published nation facts')
        self.temp.cleanup()

    def save(self,name,value):
        (self.folder/name).write_text(json.dumps(value))

    def test_mixed_people_aliases_do_not_become_government_coverage(self):
        self.assertEqual(research.validate(self.root), [])
        result = research.audit(self.root)
        self.assertEqual(result['registry_entries'],1)
        self.assertEqual(result['directory_enumerated_count'],2)
        self.assertEqual(result['directory_exact_candidate_rows'],2)
        self.assertEqual(result['directory_confirmed_crosswalks'],0)
        self.assertIsNone(result['coverage_percent'])

    def test_unresolved_count_discrepancy_cannot_be_hidden(self):
        directory = research.load(research.paths(self.root)[2])
        directory['count_discrepancy']['status'] = 'resolved'
        self.save('us_federal_directory.json',directory)
        self.assertTrue(research.validate(self.root))

    def test_confirmed_profile_link_requires_review(self):
        directory = research.load(research.paths(self.root)[2])
        directory['entities'][0]['registry_crosswalk']['registry_id'] = 'nuche'
        self.save('us_federal_directory.json',directory)
        self.assertTrue(research.validate(self.root))
        directory['entities'][0]['registry_crosswalk']['status'] = 'confirmed'
        self.save('us_federal_directory.json',directory)
        self.assertTrue(research.validate(self.root))

    def test_http_credentials_and_lookalike_hosts_fail_closed(self):
        source = {'allowed_hosts':['www.govinfo.gov']}
        self.assertTrue(research.source_allowed('https://www.govinfo.gov/list',source))
        for url in ('http://www.govinfo.gov/list','https://www.govinfo.gov.attacker.test/list',
                    'https://user:password@www.govinfo.gov/list','https://www.govinfo.gov:abc/list',
                    'https://127.0.0.1/list'):
            self.assertFalse(research.source_allowed(url,source),url)

    def test_bounded_plan_rotates_across_regions(self):
        selected = research.next_tasks(self.root,999,'2026-10-12T08:00:00Z')
        self.assertEqual(len(selected),3)
        self.assertEqual({t['region'] for t in selected},{'americas','africa','asia'})

    def test_claim_is_durable_and_expired_lease_can_resume(self):
        research.transition(self.root,'1','claim','2026-10-12T08:00:00Z')
        early = research.next_tasks(self.root,3,'2026-10-12T09:00:00Z')
        self.assertNotIn('1',[t['task_id'] for t in early])
        late = research.next_tasks(self.root,3,'2026-10-12T13:00:00Z')
        self.assertIn('1',[t['task_id'] for t in late])

    def test_handoff_needs_receipts_and_remains_unreviewed(self):
        research.transition(self.root,'1','claim','2026-10-12T08:00:00Z')
        with self.assertRaises(ValueError):
            research.transition(self.root,'1','finish','2026-10-12T09:00:00Z',note='Test handoff')
        receipt = {'source_id':'s','url':'https://www.govinfo.gov/list','retrieval_method':'browser_tool',
                   'retrieved_at':'2026-10-12T08:30:00Z','source_title':'Fixture source',
                   'evidence':'Fictional test phrase, not for publication.'}
        task = research.transition(self.root,'1','finish','2026-10-12T09:00:00Z',note='Test handoff',receipt=receipt)
        self.assertEqual(task['status'],'needs_review')
        self.assertNotIn('1',[t['task_id'] for t in research.next_tasks(self.root,3,'2026-10-13T09:00:00Z')])
        with self.assertRaises(ValueError):
            research.transition(self.root,'1','publish','2026-10-13T09:00:00Z')

    def test_failed_source_is_blocked_and_backed_off(self):
        research.transition(self.root,'1','claim','2026-10-12T08:00:00Z')
        task = research.transition(self.root,'1','block','2026-10-12T09:00:00Z',note='Test source unavailable')
        self.assertEqual(task['status'],'blocked')
        self.assertNotIn('1',[t['task_id'] for t in research.next_tasks(self.root,3,'2026-10-12T13:00:00Z')])

    def test_browser_receipt_cannot_invent_http_status(self):
        research.transition(self.root,'1','claim','2026-10-12T08:00:00Z')
        with self.assertRaises(ValueError):
            research.transition(self.root,'1','finish','2026-10-12T09:00:00Z',note='Test',receipt={
                'source_id':'s','url':'https://www.govinfo.gov/list','retrieval_method':'browser_tool',
                'retrieved_at':'2026-10-12T08:30:00Z','source_title':'Fixture','evidence':'Test only','http_status':200})

    def test_cli_defaults_do_not_write_queue(self):
        before = hashlib.sha256((self.folder/'coverage_queue.json').read_bytes()).hexdigest()
        tool = Path(research.__file__)
        for command in ('validate','audit','next'):
            result = subprocess.run([sys.executable,str(tool),'--root',str(self.root),command],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
        result = subprocess.run([sys.executable,str(tool),'--root',str(self.root),'claim','--task','1'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(hashlib.sha256((self.folder/'coverage_queue.json').read_bytes()).hexdigest(),before)

    def test_reconcile_separates_identity_from_new_profile_work(self):
        result = research.reconcile(self.root,'2026-10-12T08:00:00Z')
        self.assertEqual(len(result['changed_profile_tasks']),4)
        self.assertEqual(result['new_identity_tasks'],['identity-1'])
        selected = research.next_tasks(self.root,3,'2026-10-12T09:00:00Z')
        self.assertEqual([t['task_id'] for t in selected],['identity-1'])
        self.assertEqual(research.load(research.paths(self.root)[2])['entities'][0]['registry_crosswalk']['status'],'unreviewed')

    def test_reconcile_does_not_readd_a_source_reviewed_profile(self):
        directory = research.load(research.paths(self.root)[2])
        directory['entities'][0]['registry_crosswalk'].update(status='confirmed',registry_id='nuche',
                     reviewer='Fixture AI-assisted identity review',evidence_receipt='fixture-source-receipt')
        self.save('us_federal_directory.json',directory)
        result = research.reconcile(self.root,'2026-10-12T08:00:00Z')
        self.assertEqual(result['new_identity_tasks'],[])
        self.assertEqual(research.next_tasks(self.root,3,'2026-10-12T09:00:00Z'),[])

    def test_distinct_entity_review_can_resume_profile_research(self):
        research.reconcile(self.root,'2026-10-12T08:00:00Z')
        directory = research.load(research.paths(self.root)[2])
        directory['entities'][0]['registry_crosswalk'].update(status='not_same_entity',
                reviewer='Fixture AI-assisted identity review',evidence_receipt='fixture-distinct-government-receipt')
        self.save('us_federal_directory.json',directory)
        result = research.reconcile(self.root,'2026-10-12T09:00:00Z')
        self.assertEqual(len(result['changed_profile_tasks']),4)
        queue = research.load(research.paths(self.root)[0])
        self.assertEqual(queue['tasks'][0]['status'],'pending')
        self.assertEqual(queue['tasks'][0]['profile_disposition'],'distinct_entity_reviewed')

    def test_confirmed_crosswalk_resolves_a_previously_held_profile_and_identity(self):
        research.reconcile(self.root,'2026-10-12T08:00:00Z')
        queue = research.load(research.paths(self.root)[0])
        self.assertEqual(queue['tasks'][0]['profile_disposition'],'identity_crosswalk_first')
        broad = dict(queue['tasks'][-1])
        broad.update(task_id='identity-chiricahua-contemporary-bodies', entity_id=None,
                     subject='Broader cross-border identity research', profile_disposition=None)
        queue['tasks'].append(broad)
        self.save('coverage_queue.json',queue)
        directory = research.load(research.paths(self.root)[2])
        directory['entities'][0]['registry_crosswalk'].update(status='confirmed',registry_id='nuche',
                reviewer='Fixture AI-assisted identity review',review_kind='AI-assisted',
                evidence_receipt='fixture-source-receipt')
        self.save('us_federal_directory.json',directory)
        result = research.reconcile(self.root,'2026-10-12T09:00:00Z')
        self.assertEqual(len(result['changed_profile_tasks']),4)
        self.assertEqual(result['resolved_identity_tasks'],['identity-1'])
        queue = research.load(research.paths(self.root)[0])
        for task in queue['tasks'][:4]:
            self.assertEqual(task['status'],'needs_review')
            self.assertEqual(task['profile_disposition'],'exists_in_registry')
            self.assertEqual(task['identity_receipt'],'fixture-source-receipt')
            self.assertEqual(task['identity_review_kind'],'AI-assisted')
        identity = next(t for t in queue['tasks'] if t['task_id']=='identity-1')
        self.assertEqual(identity['status'],'needs_review')
        self.assertEqual(identity['profile_disposition'],'identity_resolved_in_crosswalk')
        planned = research.next_tasks(self.root,3,'2026-10-12T10:00:00Z')
        self.assertEqual([t['task_id'] for t in planned],['identity-chiricahua-contemporary-bodies'])
        before = (self.folder/'coverage_queue.json').read_bytes()
        again = research.reconcile(self.root,'2026-10-12T11:00:00Z')
        self.assertEqual(again['changed_profile_tasks'],[])
        self.assertEqual(again['resolved_identity_tasks'],[])
        self.assertEqual((self.folder/'coverage_queue.json').read_bytes(),before)

    def test_distinct_identity_resolution_stops_repeated_identity_research(self):
        research.reconcile(self.root,'2026-10-12T08:00:00Z')
        directory = research.load(research.paths(self.root)[2])
        directory['entities'][0]['registry_crosswalk'].update(status='not_same_entity',
                reviewer='Fixture AI-assisted identity review',review_kind='AI-assisted',
                evidence_receipt='fixture-distinct-government-receipt')
        self.save('us_federal_directory.json',directory)
        result = research.reconcile(self.root,'2026-10-12T09:00:00Z')
        self.assertEqual(result['resolved_identity_tasks'],['identity-1'])
        selected = research.next_tasks(self.root,3,'2026-10-12T10:00:00Z')
        self.assertTrue(selected)
        self.assertTrue(all(t['task_type']=='entity_profile' for t in selected))


if __name__ == '__main__':
    unittest.main()
