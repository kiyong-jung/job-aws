import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from curriculum_generator import InputError, generate, main  # noqa: E402

P = json.loads((ROOT / 'examples/project_adapt.example.json').read_text())
M = json.loads((ROOT / 'examples/materials.example.json').read_text())


class CurriculumTests(unittest.TestCase):
    def test_weekly_capacity_changes_work_that_fits(self):
        cases = [
            (4, 'blocked', ['W1', 'W2', 'W3']),
            (7, 'ready', ['W1', 'W2', 'W3']),
            (18, 'ready', ['W1', 'W2', 'W3', 'W4']),
        ]
        for hours, status, packages in cases:
            with self.subTest(hours=hours), tempfile.TemporaryDirectory() as dest:
                code = main(['--project', str(ROOT / 'examples/project_adapt.example.json'),
                             '--materials', str(ROOT / 'examples/materials.example.json'),
                             '--weeks', '5', '--hours-per-week', str(hours), '--output-dir', dest])
                result = json.loads((Path(dest) / 'curriculum.json').read_text())
                self.assertEqual(code, 3 if status == 'blocked' else 0)
                self.assertNotIn('size', result['constraints'])
                self.assertEqual(result['constraints']['hours_per_week'], hours)
                self.assertEqual(result['constraints']['capacity_hours'], hours * 5)
                self.assertEqual(result['status'], status)
                self.assertEqual(result['summary']['included_packages'], packages)
                self.assertTrue(all(w['used_minutes'] <= hours * 60 for w in result['weeks']))
                if status == 'blocked':
                    self.assertEqual(result['summary']['core_shortfall_minutes'], 11 * 60)
                    self.assertEqual(result['summary']['minimum_weekly_minutes'], 380)

    def run_plan(self, project=None, materials=None, **kwargs):
        return generate(copy.deepcopy(project if project is not None else P),
                        copy.deepcopy(materials if materials is not None else M),
                        weeks=kwargs.pop('weeks', 4), hours_per_week=kwargs.pop('hours_per_week', 9), **kwargs)

    def test_core_preserved_extension_dropped(self):
        r = self.run_plan()
        self.assertEqual(r['status'], 'ready')
        self.assertEqual(r['summary']['included_packages'], ['W1', 'W2', 'W3'])
        self.assertIn('W4', [x['id'] for x in r['summary']['excluded_packages']])
        self.assertEqual(r['summary']['implementation_hours'], 19)
        self.assertEqual(r['summary']['learning_hours'], 12)
        self.assertEqual(r['summary']['selected_material_ids'], ['M01', 'M02', 'M03'])

    def test_extension_included_if_capacity(self):
        r = self.run_plan(weeks=5, hours_per_week=9)
        self.assertEqual(r['status'], 'ready')
        self.assertEqual(r['summary']['included_packages'], ['W1', 'W2', 'W3', 'W4'])
        self.assertEqual(r['summary']['learning_hours'], 15)
        self.assertIn('M04', r['summary']['selected_material_ids'])

    def test_deterministic(self):
        self.assertEqual(self.run_plan(), self.run_plan())

    def test_spreads_available_work_across_requested_weeks(self):
        r = self.run_plan(weeks=12, hours_per_week=7)
        minutes = [week['used_minutes'] for week in r['weeks']]
        self.assertEqual(minutes, [210] * 6 + [200] * 6)
        self.assertEqual(r['summary']['scheduled_hours'], 41)
        self.assertTrue(all(week['capacity_minutes'] == 420 for week in r['weeks']))
        uneven = self.run_plan(weeks=11, hours_per_week=7)
        minutes = [week['used_minutes'] for week in uneven['weeks']]
        self.assertEqual(sum(minutes), 2460)
        self.assertEqual(max(minutes) - min(minutes), 10)

    def test_week_cap_and_full_assignment(self):
        r = self.run_plan()
        self.assertEqual(len(r['weeks']), 4)
        self.assertTrue(all(w['used_minutes'] <= w['capacity_minutes'] for w in r['weeks']))
        all_minutes = sum(a['minutes'] for w in r['weeks'] for a in w['activities'])
        self.assertEqual(all_minutes, 31 * 60)
        seq = [a['kind'] for w in r['weeks'] for a in w['activities']]
        self.assertEqual(seq[0], 'learning')

    def test_missing_required_learning_blocks(self):
        materials = copy.deepcopy(M)
        materials['references'][0]['competencies'] = ['UNRELATED']
        materials['references'][2]['competencies'] = ['UNRELATED']
        r = self.run_plan(materials=materials)
        self.assertEqual(r['status'], 'blocked')
        self.assertIn('C46', r['summary']['uncovered_competencies'])

    def test_core_material_missing_duration_blocks(self):
        materials = copy.deepcopy(M)
        del materials['core'][0]['hours']
        r = self.run_plan(materials=materials)
        self.assertEqual(r['status'], 'blocked')
        self.assertFalse(r['weeks'])

    def test_core_time_exceeds_budget_blocks(self):
        r = self.run_plan(weeks=1, hours_per_week=9)
        self.assertEqual(r['status'], 'blocked')
        self.assertFalse(r['checks']['within_total_capacity'])

    def test_dependency_cycle_fails(self):
        project = copy.deepcopy(P)
        project['packages'][0]['depends_on'] = ['W2']
        with self.assertRaisesRegex(InputError, '순환'):
            self.run_plan(project=project)

    def test_unresolved_dependency_fails(self):
        project = copy.deepcopy(P)
        project['packages'][1]['depends_on'] = ['UNKNOWN']
        with self.assertRaisesRegex(InputError, '존재하지 않는'):
            self.run_plan(project=project)

    def test_core_field_required(self):
        project = copy.deepcopy(P)
        del project['packages'][0]['core']
        with self.assertRaises(InputError):
            self.run_plan(project=project)

    def test_existing_sources_are_retained(self):
        r = self.run_plan()
        act = [a for w in r['weeks'] for a in w['activities']
               if a['kind'] == 'project' and a['id'] == 'W1'][0]
        self.assertEqual(act['sources'][0]['project'], 'example/original-project')
        self.assertEqual(act['added'], [])

    def test_prerequisite_extension_promoted_to_core_plan(self):
        project = copy.deepcopy(P)
        project['packages'][0]['depends_on'] = ['W4']
        project['packages'][3]['depends_on'] = []
        r = self.run_plan(project=project, weeks=5, hours_per_week=9)
        self.assertIn('W4', r['summary']['promoted_dependencies'])
        self.assertTrue(r['checks']['core_not_dropped'])

    def test_strict_rejects_unverified(self):
        project = copy.deepcopy(P)
        project['unverified'] = ['W1 리뷰 필요']
        r = self.run_plan(project=project, strict=True)
        self.assertEqual(r['status'], 'blocked')

    def test_project_budget_rejects_optional_extension(self):
        project = copy.deepcopy(P)
        project['hours']['budget'] = 20
        r = self.run_plan(project=project, weeks=5, hours_per_week=9)
        self.assertEqual(r['status'], 'ready')
        self.assertNotIn('W4', r['summary']['included_packages'])
        self.assertTrue(r['checks']['project_implementation_within_budget'])

    def test_project_budget_core_overage_blocks(self):
        project = copy.deepcopy(P)
        project['hours']['budget'] = 15
        r = self.run_plan(project=project)
        self.assertEqual(r['status'], 'blocked')
        self.assertFalse(r['checks']['project_implementation_within_budget'])

    def test_missing_core_provider_identifies_affected_task(self):
        materials = copy.deepcopy(M)
        materials['core'][0]['competencies'] = ['UNRELATED']
        r = self.run_plan(materials=materials)
        self.assertEqual(r['status'], 'blocked')
        self.assertIn('W1', r['prerequisite_gaps'])

    def test_missing_evidence_requires_review(self):
        materials = copy.deepcopy(M)
        del materials['core'][0]['evidence']
        r = self.run_plan(materials=materials)
        self.assertEqual(r['status'], 'needs_review')
        self.assertFalse(r['checks']['educational_evidence_complete'])

    def test_read_unified_material_list(self):
        mats = [{**m, 'role': 'core'} for m in M['core']] + \
               [{**m, 'role': 'reference'} for m in M['references']]
        r = self.run_plan(materials={'materials': mats})
        self.assertEqual(r['status'], 'ready')

    def test_data_not_limited_to_12_weeks_or_fixed_ids(self):
        project = {'title': '임의 프로젝트', 'packages': [
            {'do': '작업', 'out': '결과', 'hours': 1.5, 'core': True, 'competencies': ['MY_SKILL']}],
            'checks': {'passed': True}}
        mats = [{'role': 'core', 'title': '참고', 'minutes': 30,
                 'competencies': ['MY_SKILL'], 'url': 'https://example.org', 'evidence': '예시 목차'}]
        r = self.run_plan(project=project, materials=mats, weeks=2, hours_per_week=2)
        self.assertEqual(r['status'], 'needs_review')
        self.assertTrue(r['weeks'])
        self.assertEqual(r['summary']['included_packages'], ['W1'])


if __name__ == '__main__':
    unittest.main()
