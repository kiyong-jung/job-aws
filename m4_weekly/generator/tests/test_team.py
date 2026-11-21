import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from curriculum_generator import format_md, generate, main
from team_csv import prepare_team, read_rows

DATA = Path(__file__).resolve().parents[1] / "data/aws_fde"


class TeamCurriculumTest(unittest.TestCase):
    def test_exports_twelve_populated_weeks_and_discloses_gaps(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(main(["--hours-per-week", "7", "--output-dir", folder]), 3)
            result = json.loads((Path(folder) / "curriculum.json").read_text())
            markdown = (Path(folder) / "curriculum.md").read_text()
        self.assertNotIn("전체 범위를 다루지 않는 목표 역량", markdown)
        self.assertNotIn("educational_coverage_complete", markdown)
        self.assertNotIn("checks.passed", markdown)
        self.assertNotIn("upstream_project_passed", markdown)
        self.assertNotIn("## 확인 및 경고", markdown)
        self.assertNotIn("> 주의:", markdown)
        self.assertTrue(any("checks.passed" in warning for warning in result["warnings"]))
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(len(result["weeks"]), 12)
        self.assertTrue(all(0 < week["used_minutes"] <= 420 for week in result["weeks"]))
        self.assertTrue(all(a["minutes"] % 10 == 0 for w in result["weeks"] for a in w["activities"]))
        self.assertEqual(len(result["team_export"]["input_files"]), 2)
        self.assertTrue(all(unit["section"] for unit in result["learning_matches"]))
        self.assertTrue(any("The Flow Class" in unit["section"] for unit in result["learning_matches"]))
        self.assertTrue(any("원문 절 미확인" in unit["section"] for unit in result["learning_matches"]))
        self.assertFalse(result["checks"]["educational_coverage_complete"])
        self.assertIn("C14", result["competency_coverage"]["missing_materials"])

    def test_short_csv_row_reports_line_and_field(self):
        with tempfile.TemporaryDirectory() as folder:
            csv_file = Path(folder) / "materials.csv"
            csv_file.write_text("id,covers\nM01\n")
            with self.assertRaisesRegex(ValueError, r"materials\.csv.*2.*covers"):
                read_rows(folder, csv_file.name, {"id", "covers"})

    def test_bedrock_proposal_changes_team_schedule(self):
        project, materials, _ = prepare_team(DATA)

        def proposal(tasks, units, *args):
            return {
                "tasks": [{"id": t.id, "quote": t.out, "requires": ["C52"] if t.id == "P01" else [],
                           "depends_on": ["P05"] if t.id == "P04" else [],
                           "completion_check": "테스트로 확인"} for t in tasks],
                "units": [{"id": u.id, "quote": u.title, "teaches": list(u.competencies),
                           "requires": [], "study_method": "비교 실습"} for u in units],
            }

        with patch("lesson_analysis.propose", side_effect=proposal), patch("lesson_analysis.weekly_guides"):
            result = generate(project, materials, weeks=12, hours_per_week=7, model="test-model")
        tasks = result["summary"]["included_packages"]
        self.assertLess(tasks.index("P05"), tasks.index("P04"))
        self.assertEqual(result["task_preparation"][0]["required"], ["C52"])
        self.assertEqual(result["task_preparation"][0]["study_before_task"], ["LRN6a568bbf93"])
        self.assertEqual(result["weeks"][0]["activities"][0]["study_method"], "비교 실습")

    def test_unconfirmed_llm_guidance_stays_in_generated_draft(self):
        project, materials, _ = prepare_team(DATA)

        def proposal(tasks, units, *args):
            return {
                "tasks": [{"id": t.id, "quote": "", "requires": list(t.requires),
                           "depends_on": [], "completion_check": t.completion_check} for t in tasks],
                "units": [{"id": u.id, "quote": "입력에서 확인되지 않는 문장", "teaches": list(u.competencies),
                           "requires": [], "study_method": "예제를 실행하고 결과를 비교합니다.",
                           "suggested_scope": "두 리전 구성의 차이를 살펴보기"} for u in units],
            }

        with patch("lesson_analysis.propose", side_effect=proposal), patch("lesson_analysis.weekly_guides"):
            result = generate(project, materials, weeks=12, hours_per_week=7, model="test-model")
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(len(result["weeks"]), 12)
        unit = result["analysis_provenance"]["units"]["E03732779fa"]
        self.assertFalse(unit["input_quote_matched"])
        self.assertEqual(unit["suggested_scope"], "두 리전 구성의 차이를 살펴보기")
        self.assertNotIn("suggested_scope", result["analysis_provenance"]["units"]["LRN624bcb0ae0"])
        self.assertIn("LLM 생성 제안 · 원문 미확인", format_md(result))
        self.assertIn("두 리전 구성의 차이를 살펴보기", format_md(result))
        self.assertNotIn("입력에서 확인되지 않는 문장", format_md(result))

    def test_requested_reference_adds_followup_without_replacing_prerequisites(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(main(["--hours-per-week", "7", "--include-reference", "E564ad08f67",
                                   "--include-reference", "E2a4fa23ce7", "--output-dir", folder]), 3)
            result = json.loads((Path(folder) / "curriculum.json").read_text())
        self.assertEqual(result["summary"]["scheduled_hours"], 80.5)
        self.assertEqual(result["summary"]["remaining_hours"], 3.5)
        activities = [a for w in result["weeks"] for a in w["activities"]]
        self.assertTrue(all(w["used_minutes"] <= 420 for w in result["weeks"]))
        self.assertLess(max(a["sequence"] for a in activities if a["id"] == "P05"),
                        min(a["sequence"] for a in activities if a["id"] == "E564ad08f67"))
        self.assertTrue(all(a["learning_purpose"] == "supplemental" for a in activities
                            if a["id"] in {"E564ad08f67", "E2a4fa23ce7"}))
        self.assertIn("E365c3dd16b", result["summary"]["selected_material_ids"])
        self.assertEqual(activities[-1]["id"], "E2a4fa23ce7")

    def test_requested_reference_respects_remaining_budget_and_prerequisites(self):
        project, materials, _ = prepare_team(DATA)
        options = {"weeks": 12, "include_references": ["E564ad08f67"]}
        result = generate(project, materials, hours_per_week=6.5, **options)
        self.assertEqual(result["supplemental_references"][0]["status"], "skipped")
        self.assertIn("시간", result["supplemental_references"][0]["reason"])
        reference = next(u for u in materials["materials"] if u["id"] == "E564ad08f67")
        reference["requires"] = ["C999"]
        result = generate(project, materials, hours_per_week=7, **options)
        self.assertEqual(result["supplemental_references"][0]["status"], "skipped")
        self.assertIn("선수", result["supplemental_references"][0]["reason"])

    def test_team_llm_draft_discloses_missing_prerequisite_material(self):
        project, materials, _ = prepare_team(DATA)

        def proposal(tasks, units, *args):
            return {
                "tasks": [{"id": t.id, "quote": "", "requires": list(t.requires) + (["C14"] if t.id == "P03" else []),
                           "depends_on": [], "completion_check": t.completion_check} for t in tasks],
                "units": [{"id": u.id, "quote": "", "teaches": list(u.competencies),
                           "requires": [], "study_method": "프로젝트와 비교"} for u in units],
            }

        with patch("lesson_analysis.propose", side_effect=proposal), patch("lesson_analysis.weekly_guides") as guides:
            result = generate(project, materials, weeks=12, hours_per_week=7, model="test-model")
            strict = generate(project, materials, weeks=12, hours_per_week=7, model="test-model", strict=True)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(len(result["weeks"]), 12)
        self.assertIn("C14", str(result["prerequisite_gaps"]["P03"]))
        self.assertTrue(any("P03 선수학습 확인 필요" in warning for warning in result["warnings"]))
        self.assertFalse(result["checks"]["educational_coverage_complete"])
        self.assertEqual(strict["status"], "blocked")
        self.assertEqual(guides.call_count, 1)
        _, _, result["team_export"] = prepare_team(DATA)
        markdown = format_md(result)
        self.assertIn("## 추가 학습 참고", markdown)
        self.assertIn("검색 파이프라인(RAG) 설계 및 개발", markdown.split("## 추가 학습 참고", 1)[1])
        self.assertIn("공식 문서 예제", markdown)
        self.assertNotIn("## 확인 및 경고", markdown)
        self.assertNotIn("필요한 선수지식 · C14", markdown)
        _, _, strict["team_export"] = prepare_team(DATA)
        strict_markdown = format_md(strict)
        self.assertIn("## 확인 및 경고", strict_markdown)
        self.assertNotIn("## 추가 학습 참고", strict_markdown)
        self.assertNotIn("학습 경로를 확보하지 못한 항목", markdown)
        self.assertNotIn("선수학습 확인 필요:", markdown)

    def test_user_selects_one_weekly_size(self):
        for size, hours in (("소형", 7), ("중형", 14), ("대형", 30)):
            with self.subTest(size=size), tempfile.TemporaryDirectory() as folder:
                self.assertEqual(main(["--size", size, "--output-dir", folder]), 3)
                result = json.loads((Path(folder) / "curriculum.json").read_text())
                self.assertEqual(result["constraints"]["size"], size)
                self.assertEqual(result["constraints"]["hours_per_week"], hours)
                self.assertEqual(result["constraints"]["capacity_hours"], hours * 12)
                self.assertEqual(len(result["weeks"]), 12)
                self.assertTrue(all(w["used_minutes"] <= hours * 60 for w in result["weeks"]))
