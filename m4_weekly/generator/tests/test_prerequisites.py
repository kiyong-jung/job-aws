import copy
import unittest
from test_generator import P, M, generate

class PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.p, self.m = copy.deepcopy(P), copy.deepcopy(M)
        self.p['packages'][0]['requires'] = ['search']
        for t in self.p['packages'][1:]:
            t['requires'] = []
        first, second = self.m['core'][1]['sections']
        first.update(teaches=['search'], requires=['vectors'])
        second.update(teaches=['vectors'], requires=['python'])
        self.p['learner'] = {'known': ['python']}

    def plan(self):
        return generate(self.p,self.m,weeks=12,hours_per_week=7)

    def test_order_and_known(self):
        r=self.plan()
        steps=[a['id'] for w in r['weeks'] for a in w['activities']]
        self.assertLess(steps.index('M02/S2'),steps.index('M02/S1'))
        self.assertLess(steps.index('M02/S1'),steps.index('W1'))
        self.assertEqual(r['summary']['learning_hours'],5)
        self.assertEqual(r['weeks'][0]['recommended_learning_percent'],60)

    def test_cycle_with_and_without_alternative(self):
        self.m['core'][1]['sections'][1]['requires']=['search']
        r=self.plan()
        self.assertEqual(r['status'],'blocked')
        self.assertIn('W1', str(r['prerequisite_gaps']))
        self.assertIn('순환', str(r['prerequisite_gaps']))
        self.m['references'][0]['teaches']=['vectors']
        self.assertTrue(self.plan()['weeks'])

    def test_known_removes_learning(self):
        self.p['learner']['known']=['search']
        self.assertEqual(self.plan()['summary']['learning_hours'],0)

    def test_missing_optional_prerequisite_does_not_block_core(self):
        self.p['packages'][-1]['requires']=['외부교육']
        result=self.plan()
        self.assertTrue(result['weeks'])
        self.assertIn('외부교육',str(result['summary']['excluded_packages']))
        self.assertNotIn('W4',result['summary']['included_packages'])

    def test_unknown_duration_blocks_with_task_and_material(self):
        del self.m['core'][1]['sections'][1]['minutes']
        result=self.plan()
        self.assertFalse(result['weeks'])
        self.assertIn('M02/S2',str(result['prerequisite_gaps']['W1']))
        self.assertFalse(result['checks']['material_durations_known'])

    def test_falls_back_to_shorter_reference_when_core_path_exceeds_budget(self):
        project = {"title": "예제", "checks": {"passed": True}, "packages": [
            {"id": "W1", "do": "구현", "out": "코드", "hours": 4, "core": True,
             "competencies": ["X"], "requires": ["X"], "depends_on": [],
             "completion_check": "실행", "sources": ["과제 설명"]}]}
        materials = {"core": [{"id": "long", "title": "핵심", "hours": 48, "teaches": ["X"]}],
                     "references": [{"id": "short", "title": "참고", "hours": 1, "teaches": ["X"]}]}
        result = generate(project, materials, weeks=12, hours_per_week=4)
        self.assertTrue(result["weeks"])
        self.assertEqual(result["summary"]["selected_material_ids"], ["short"])
        self.assertEqual(result["summary"]["scheduled_hours"], 5)
