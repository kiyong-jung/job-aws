import copy
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from test_generator import P, M, generate
from curriculum_generator import normalize_materials, normalize_project, format_md
import lesson_analysis


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.p = copy.deepcopy(P)
        self.p['packages'][1].pop('depends_on')
        self.p['packages'][1].pop('requires')
        _, tasks, _ = normalize_project(self.p)
        units, _, _ = normalize_materials(M)
        self.proposal = {
            'tasks': [dict(id=t.id, quote=t.do, requires=list(t.competencies),
                           depends_on=['W1'] if t.id == 'W2' else [], completion_check='산출물 실행 확인') for t in tasks],
            'units': [dict(id=u.id, quote=u.title, teaches=list(u.competencies), requires=list(u.requires),
                           study_method='예제를 실행하고 결과를 작업에 연결한다') for u in units]}

    def test_untraceable_quote_and_cycle_are_rejected(self):
        bad = copy.deepcopy(self.proposal)
        bad['tasks'][0]['quote'] = '원본에 없는 인용'
        with self.assertRaisesRegex(ValueError,'인용'):
            generate(self.p,M,weeks=12,hours_per_week=7,analysis=bad)
        self.proposal['tasks'][1]['depends_on'] = ['W3']
        with self.assertRaisesRegex(ValueError,'순환'):
            generate(self.p,M,weeks=12,hours_per_week=7,analysis=self.proposal)

    def test_converse_input_and_weekly_guides(self):
        def fake_cli(cmd, **kwargs):
            arg = cmd[cmd.index('--cli-input-json') + 1]
            self.assertTrue(arg.startswith('file://'))
            request_path = Path(arg.removeprefix('file://'))
            self.assertTrue(request_path.is_file())
            self.assertNotEqual(request_path, Path('/dev/stdin'))
            req = json.loads(request_path.read_text(encoding='utf-8'))
            tool = req['toolConfig']['toolChoice']['tool']['name']
            if tool == 'lesson_plan':
                result = self.proposal
            else:
                weeks = json.loads(req['messages'][0]['content'][0]['text'])
                result = {'weeks':[dict(week=w['week'],activities=list(dict.fromkeys(a['id'] for a in w['activities'])),
                                        goal='검색 동작 확인',method='검색 예제 실행',reason='선행 작업 완료 후 적용')
                                   for w in weeks]}
            return subprocess.CompletedProcess(cmd,0,json.dumps({'stopReason':'tool_use',
                'output':{'message':{'content':[{'toolUse':{'name':tool,'input':result}}]}}}))
        with patch('lesson_analysis.subprocess.run',side_effect=fake_cli) as mock:
            plan=generate(self.p,M,weeks=12,hours_per_week=7,model='example-model')
        self.assertEqual(mock.call_count,2)
        self.assertEqual(plan['status'],'needs_review')
        self.assertIn('검색 예제 실행',format_md(plan))
        self.assertEqual(plan['weeks'][0]['guide']['goal'],'검색 동작 확인')

    def test_weekly_guide_cannot_insert_activities(self):
        weeks=[{'week':1,'activities':[{'id':'W1'}]}]
        row=dict(week=1,activities=['NEW'],goal='목표',method='방법',reason='이유')
        with patch('lesson_analysis.invoke',return_value={'weeks':[row]}):
            with self.assertRaisesRegex(ValueError,'일치하지'):
                lesson_analysis.weekly_guides(weeks,'model',None,None)
