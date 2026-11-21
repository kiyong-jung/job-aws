# 논문 서고 (data/papers)

프로젝트 샘플을 웹 검색 없이 찾기 위한 로컬 논문 목록. 2020~2026 탑티어 AI 학회와 클라우드·시스템 학회의 본회의 논문. 모은 날짜 2026-11-16.
조각 파일은 git 에 올리지 않고 `python -m m2_project.library papers` 로 다시 만든다. 한 줄이 한 편이다.

## 폴더 (분야별)

- `ai/<학회>_<연도>.jsonl`: ACL·EMNLP·NAACL(+Findings), ICML, NeurIPS, ICLR, CVPR, ICCV, ECCV, AAAI, IJCAI, KDD, SIGIR, WWW, MM, CHI.
- `cloud/<학회>_<연도>.jsonl`: OSDI, NSDI, ATC, FAST, MLSys, SOSP, EuroSys, ASPLOS, SIGCOMM.
- 학회가 어느 분야인지는 `library.py` 의 `FIELD_OF` 한 곳에서 정한다. 표에 없는 학회는 오류로 멈춘다.
- `_raw/`: 내려받은 원본(dblp 덤프, ACL bib, PWC 보관본)과 로그. 맨 마지막 단계에서 지운다(아래 순서).
- `reorganize` 를 돌리기 전에는 옛 위치(`data/papers/<학회>_<연도>.jsonl`)의 조각도 읽힌다. 코드는 새 위치를 먼저 보고 없으면 옛 위치를 쓴다.

칸: `venue, year, title, abstract, url, doi, arxiv, abstract_source, has_code, code_url, code_source, pdf_url`.
`abstract` 가 `null` 이면 아직 못 채운 것, `""` 이면 찾아봤지만 없는 것이다.

## 코드 저장소 연결 (has_code)

`has_code` 는 `"T"` 또는 `"F"` 다. **F 는 링크를 찾지 못했다는 뜻이지 저장소가 없다는 증명이 아니다.**
`python -m m2_project.library code` 가 F 인 글만 다시 보고, 값은 F 에서 T 로만 바뀐다. 순서는 싼 것부터다.

1. 초록 속 github.com 주소 (`code_source = abstract`).
2. Papers with Code 보관본 (`paperswithcode-archive`). 원 운영팀 pwc-archive 가 Hugging Face 에 올린 `links-between-paper-and-code` (CC BY-SA 4.0, 2025-09 판). arXiv 번호나 제목이 정확히 같은 글에 이어 준다. 공식 저장소를 먼저 쓴다. 2025년 9월 이후 논문은 이 방법으로 못 찾는다.
3. 다른 담당이 모으는 `data/github_repos/*.jsonl` (읽기만). 저장소 설명에 arXiv 번호가 있거나 설명 전체가 제목과 같은 경우만 (`github_repos description`). 설명 필드만 있어 4편 정도로 적다.

쓰지 못한 방법이 있다. ACL Anthology bib 와 PMLR bib 에는 코드 칸이 없고, papers.nips.cc·CVF·ecva 논문 페이지에는 코드 링크가 없었다 (견본으로 확인). OpenReview 는 막혀 못 열었다.
방법별 T 개수는 아래 "방법별 T" 에 적는다.

## 출처와 이용 조건

| 학회 | 출처 | 초록 | 이용 조건·메모 |
|---|---|---|---|
| ACL, EMNLP, NAACL (+ Findings 는 `ACL-Findings` 처럼 따로) | ACL Anthology 일괄 파일 `anthology+abstracts.bib.gz` | 있음 | CC BY. 본회의(main·long·short)와 Findings 만. 워크숍·시연·튜토리얼은 뺀다. NAACL 은 2020·2023 년에 열리지 않았다 |
| ICML 2020~2025 | proceedings.mlr.press 권별 `bibliography.bib` (119, 139, 162, 202, 235, 267) | 있음 | 연구 이용. 2026 권은 PMLR 에 아직 없다 |
| NeurIPS 2020~2025 | papers.nips.cc 연도별 목록 + 논문 페이지 | 페이지에서 | 연구 이용. 2021 이후 Datasets & Benchmarks 논문도 같은 목록에 섞여 있다. 2026 은 아직 없다 |
| CVPR 2020~2026, ICCV 2021·2023·2025 | openaccess.thecvf.com 목록 + 논문 페이지 | 페이지에서 | 연구 이용. 워크숍 제외 |
| ECCV 2020·2022·2024 | ecva.net/papers.php + 논문 페이지 | 페이지에서 | 연구 이용. ECCV 2026 은 ecva 에 아직 없다 (dblp 에는 제목 약 2,800건) |
| OSDI, NSDI, ATC, FAST 2020~2026 | usenix.org 공식 프로그램 쪽 `/conference/<학회><yy>/technical-sessions` (제목·초록이 한 쪽에 있다) | 있음 | robots.txt Crawl-delay 10초라 요청 10초 간격. 초록·PDF 공개. 아직 열리지 않았거나 쪽이 없는 해는 건너뛴다 |
| MLSys 2020~2026 | proceedings.mlsys.org 연도별 목록 + 논문 페이지 | 페이지에서 | robots 파일 없음, 요청 1.1초 간격 |
| SOSP, EuroSys, ASPLOS, SIGCOMM | dblp 일괄 파일 (booktitle 이 `SOSP`, `EuroSys`, `SIGCOMM`, `ASPLOS`·`ASPLOS (1)`~`(4)` 인 것) | arXiv 로 채움 | SOSP 는 격년(2021·2023·2024·2025…)이라 없는 해가 있다. 부록·워크숍(`…@SOSP`)은 제외 |
| ICLR, AAAI, IJCAI, KDD, SIGIR, WWW, MM, CHI | dblp 일괄 파일 `dblp.xml.gz` (제목·주소·doi) | arXiv 로 채움 | dblp 는 CC0. 초록은 arXiv API 에서 제목이 똑같은 글만 받아 `abstract_source` 에 적는다. arXiv 에 없는 글은 `""` |

dblp 는 booktitle 이 학회 이름과 정확히 같은 항목만 쓴다 (`CHI Extended Abstracts`, `WWW (Companion Volume)` 같은 부록·워크숍 논문집은 제외, KDD 는 `KDD (1)`, `KDD (2)` 포함).

못 쓴 출처와 이유.
- OpenReview API (ICLR·NeurIPS·ICML): `api2.openreview.net` 이 확인 절차(challenge, HTTP 403)를 요구해 멈췄다. 우회하지 않았다.
- iclr.cc, neurips.cc, icml.cc 의 공식 JSON: robots.txt 가 `/static` 을 막아 쓰지 않았다.
- OpenAlex: 키(`OPENALEX_API_KEY`)가 없고 하루 한도가 이미 찼다. 그래서 AAAI·IJCAI·KDD·SIGIR·WWW·MM·CHI 는 dblp 제목 + arXiv 초록으로 갔다. 키가 있으면 `abstract` 가 null·"" 인 글을 OpenAlex 로 더 채울 수 있다 (CC0).
- Semantic Scholar: 키가 없어 쓰지 않았다.

## 처음 훑어본 편수 (가능성 확인)

dblp 일괄 파일에서 센 편수는 워크숍·부록을 일부 포함해 실제 본회의 편수보다 많거나, 학회마다 등록 방식이 달라 어긋난다 (예: ICML 은 dblp 에 1,100편 안팎이라 PMLR 와 같다). 출처 선택의 근거로만 썼다.

| 학회 | 출처에서 나온 편수 (연도) |
|---|---|
| ACL·EMNLP·NAACL | 연도당 400~2,700 (Anthology) |
| ICML | 1,084 / 1,183 / 1,233 / 1,828 / 2,610 / 3,330 (2020~2025) |
| NeurIPS | 2020 년 1,898 외에는 수집 로그 참고 |
| CVPR | 2021 년 1,660 |
| ECCV | 1,358 / 1,645 / 2,387 (2020·2022·2024) |
| dblp 학회 | AAAI 1,600~4,900, ICLR 690~5,350, CHI 640~1,700, 나머지 400~1,500 |

## 전문(PDF) 규칙과 실행 순서

전문을 내려받을 수 없는 글은 지운다. `pdf_url` 은 ① 학회 공식 공개 PDF (ACL Anthology, CVF, ecva, NeurIPS·MLSys 논문집, PMLR, IJCAI, USENIX, AAAI 공식 쪽), 없으면 ② arXiv PDF (`arxiv` 칸이 채워진 글), 없으면 ③ 그 글을 지운다.
ICLR·KDD·SIGIR·WWW·MM·CHI·SOSP·EuroSys·ASPLOS·SIGCOMM 은 공식 공개 PDF 규칙이 없어 arXiv 에서 찾은 글만 남는다. (ACM 논문은 공개 여부가 글마다 달라 따지지 않았다.) 공식 PDF 주소는 글 주소에서 규칙으로 만들고(`pdf_url_of`), 실제로 열어 보지는 않는다. USENIX 는 `system/files/…pdf` 가 `files.usenix.org` 로 넘어간다 (osdi20 한 편으로 확인).

순서. 앞 단계가 끝난 뒤에 다음 단계를 돌린다. 수집·채우기·`code` 프로세스가 돌고 있으면 `prune`·`reorganize` 는 스스로 멈춘다 (`m2_project/guard.py`).

```
export PYTHONPATH=.; PY=.venv/bin/python
$PY -m m2_project.library papers [출처…]      # 1. 수집 (acl icml nips cvf eccv dblp usenix mlsys). 이어하기
$PY -m m2_project.library fill [학회…]         # 2. dblp 학회 초록·arXiv 번호를 arXiv 로 (동시에 하나만)
$PY -m m2_project.library code                 # 3. has_code
$PY -m m2_project.library pdf                  # 4. (선택) AAAI 중 arXiv 에 없는 글의 공식 PDF 주소를 ojs.aaai.org 에서 읽기. 느리다(편당 1.1초)
$PY -m m2_project.library prune                # 5. pdf_url 채우고 전문 없는 글 삭제 (prune_report.json 에 조각별 전·후)
$PY -m m2_project.library reorganize           # 6. 옛 위치의 조각을 ai/ cloud/ 로 옮기기
rm -rf data/papers/_raw                        # 7. 원본·로그 지우기
```

`prune` 은 몇 번 돌려도 같은 결과다. 4번을 건너뛰면 AAAI 는 arXiv 에서 찾은 글만 남는다. 7번 뒤에는 `library.py` 가 `_raw` 를 읽는 곳이 `papers acl`(ACL bib), `papers dblp`(dblp 덤프 1.1GB), `code`(PWC 보관본)뿐이고, 이것들은 `_raw` 가 없으면 **다시 내려받는다**(dblp 는 자동이 아니라 오류로 멈추고 안내한다). 이미 있는 조각은 다시 만들지 않으므로, 일반 실행은 `_raw` 가 없어도 된다.
삭제는 되돌릴 수 없다. 규칙을 바꾸려면 `prune` 전에 바꾸고, `_raw` 에는 ACL·dblp 원본이 남아 있어 그 학회는 다시 만들 수 있다 (NeurIPS·CVF·ECCV·MLSys·USENIX 는 다시 수집).

## 조각별 편수

<!-- stats -->
| 조각 | 편수 | 초록 있음 | has_code=T |
|---|---|---|---|
| AAAI_2020 | 1864 | 0 | 0 |
| AAAI_2021 | 1961 | 0 | 0 |
| AAAI_2022 | 1624 | 0 | 0 |
| AAAI_2023 | 2021 | 0 | 0 |
| AAAI_2024 | 2866 | 0 | 0 |
| AAAI_2025 | 3486 | 0 | 0 |
| AAAI_2026 | 4920 | 0 | 0 |
| ACL-Findings_2021 | 458 | 0 | 0 |
| ACL-Findings_2022 | 332 | 331 | 0 |
| ACL-Findings_2023 | 902 | 901 | 0 |
| ACL-Findings_2024 | 976 | 953 | 0 |
| ACL-Findings_2025 | 1388 | 1387 | 0 |
| ACL-Findings_2026 | 2164 | 2158 | 0 |
| ACL_2020 | 779 | 778 | 0 |
| ACL_2021 | 712 | 710 | 0 |
| ACL_2022 | 702 | 700 | 0 |
| ACL_2023 | 1077 | 1075 | 0 |
| ACL_2024 | 942 | 939 | 0 |
| ACL_2025 | 1701 | 1699 | 0 |
| ACL_2026 | 2298 | 2295 | 0 |
| CHI_2020 | 758 | 0 | 0 |
| CHI_2021 | 746 | 0 | 0 |
| CHI_2022 | 637 | 0 | 0 |
| CHI_2023 | 879 | 0 | 0 |
| CHI_2024 | 1057 | 0 | 0 |
| CHI_2025 | 1249 | 0 | 0 |
| CHI_2026 | 1702 | 0 | 0 |
| CVPR_2021 | 1660 | 900 | 0 |
| ECCV_2020 | 1358 | 600 | 0 |
| ECCV_2022 | 1645 | 0 | 0 |
| ECCV_2024 | 2387 | 0 | 0 |
| EMNLP-Findings_2020 | 448 | 447 | 0 |
| EMNLP-Findings_2021 | 425 | 423 | 0 |
| EMNLP-Findings_2022 | 549 | 548 | 0 |
| EMNLP-Findings_2023 | 1060 | 1059 | 0 |
| EMNLP-Findings_2024 | 1004 | 976 | 0 |
| EMNLP-Findings_2025 | 1406 | 1402 | 0 |
| EMNLP-Findings_2026 | 2479 | 2478 | 0 |
| EMNLP_2020 | 752 | 751 | 0 |
| EMNLP_2021 | 848 | 847 | 0 |
| EMNLP_2022 | 829 | 826 | 0 |
| EMNLP_2023 | 1048 | 1047 | 0 |
| EMNLP_2024 | 1269 | 1237 | 0 |
| EMNLP_2025 | 1810 | 1809 | 0 |
| EMNLP_2026 | 2705 | 2704 | 0 |
| ICLR_2020 | 687 | 200 | 0 |
| ICLR_2021 | 860 | 0 | 0 |
| ICLR_2022 | 1094 | 0 | 0 |
| ICLR_2023 | 1573 | 0 | 0 |
| ICLR_2024 | 2260 | 0 | 0 |
| ICLR_2025 | 3718 | 0 | 0 |
| ICLR_2026 | 5351 | 0 | 0 |
| ICML_2020 | 1084 | 1084 | 0 |
| ICML_2021 | 1183 | 1183 | 0 |
| ICML_2022 | 1233 | 1233 | 0 |
| ICML_2023 | 1828 | 1828 | 0 |
| ICML_2024 | 2610 | 2610 | 0 |
| ICML_2025 | 3330 | 3330 | 0 |
| IJCAI_2020 | 778 | 0 | 0 |
| IJCAI_2021 | 721 | 0 | 0 |
| IJCAI_2022 | 863 | 0 | 0 |
| IJCAI_2023 | 846 | 0 | 0 |
| IJCAI_2024 | 1048 | 0 | 0 |
| IJCAI_2025 | 1280 | 0 | 0 |
| KDD_2020 | 421 | 0 | 0 |
| KDD_2021 | 482 | 0 | 0 |
| KDD_2022 | 534 | 0 | 0 |
| KDD_2023 | 564 | 0 | 0 |
| KDD_2024 | 641 | 0 | 0 |
| KDD_2025 | 839 | 0 | 0 |
| KDD_2026 | 1469 | 0 | 0 |
| MM_2020 | 584 | 0 | 0 |
| MM_2021 | 684 | 0 | 0 |
| MM_2022 | 829 | 0 | 0 |
| MM_2023 | 1014 | 0 | 0 |
| MM_2024 | 1232 | 0 | 0 |
| MM_2025 | 1613 | 0 | 0 |
| NAACL-Findings_2022 | 210 | 209 | 0 |
| NAACL-Findings_2024 | 297 | 286 | 0 |
| NAACL-Findings_2025 | 476 | 458 | 0 |
| NAACL_2021 | 478 | 477 | 0 |
| NAACL_2022 | 443 | 442 | 0 |
| NAACL_2024 | 564 | 562 | 0 |
| NAACL_2025 | 720 | 695 | 0 |
| NeurIPS_2020 | 1898 | 900 | 0 |
| SIGIR_2020 | 382 | 0 | 0 |
| SIGIR_2021 | 381 | 0 | 0 |
| SIGIR_2022 | 444 | 0 | 0 |
| SIGIR_2023 | 469 | 0 | 0 |
| SIGIR_2024 | 387 | 0 | 0 |
| SIGIR_2025 | 537 | 0 | 0 |
| SIGIR_2026 | 683 | 0 | 0 |
| WWW_2020 | 320 | 0 | 0 |
| WWW_2021 | 355 | 0 | 0 |
| WWW_2022 | 367 | 0 | 0 |
| WWW_2023 | 407 | 0 | 0 |
| WWW_2024 | 432 | 0 | 0 |
| WWW_2025 | 445 | 0 | 0 |
| WWW_2026 | 952 | 0 | 0 |
| **합계** | **118783** | **47477** | **0** |
<!-- /stats -->

## 방법별 T

<!-- code-stats -->
(`python -m m2_project.library code` 를 돌린 뒤 채운다)
<!-- /code-stats -->

## 다시 하는 법

```
cd code
PYTHONPATH=. .venv/bin/python -m m2_project.library papers          # 모든 출처 (이어하기). 출처 하나만: papers nips
PYTHONPATH=. .venv/bin/python -m m2_project.library fill [학회…]    # dblp 학회 초록을 arXiv 로 (이어하기, 동시에 하나만)
PYTHONPATH=. .venv/bin/python -m m2_project.library code            # has_code 열 채우기 (수집이 끝난 뒤 돌린다)
PYTHONPATH=. .venv/bin/python -m m2_project.library stats           # 이 표 새로 쓰기
```

`dblp` 는 `_raw/dblp.xml.gz` (약 1.1GB, https://dblp.org/xml/dblp.xml.gz) 가 있어야 한다. 요청 간격은 호스트마다 1.1초, dblp 4초, arXiv 3.5초.
