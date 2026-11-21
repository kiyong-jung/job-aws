"""① 공고 은행과 이력서 은행. shared.schema 의 postings·posting_lines, resumes·resume_lines 표를 채우고 읽는다.

공고 스냅샷은 m1_competency/data/postings.jsonl 한 파일이다 (줄마다 공고 하나, batch 는 함께 모은 묶음. 출처는 data/README.md).
이력서는 m1_competency/data/resumes/*.md 다. 공고를 넣을 때 정제한 줄(competencies.refine)도 함께 넣는다.
표의 줄을 손으로 고치면(method 를 '사람'으로) 다음 실행부터 그 분류를 쓴다.

  python -m m1_competency.collect           # 스냅샷과 이력서 파일 → 표 (data/banks/*.csv). 정제한 줄이 없는 공고만 정제한다
  python -m m1_competency.collect refine    # 정제 규칙을 고친 뒤: 모든 공고의 줄을 다시 정제한다 (손으로 고친 줄도 덮어쓴다)
  python -m m1_competency.collect fetch     # 회사 공식 채용 사이트에서 공고를 모아 postings.jsonl 의 그 묶음을 바꾼다 (표는 건드리지 않고 LLM 도 부르지 않는다)
  python -m m1_competency.collect fetch naver toss   # 이름이 든 회사만
"""
import html
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urljoin, urlparse

from shared import config, schema, web

from . import competencies


def load_postings(company=None):
    return sorted((p for p in schema.read("postings") if not company or p["company"] == company),
                  key=lambda p: (p["collected_at"], p["id"]))


def get_posting(posting_id="J01"):
    got = [p for p in schema.read("postings") if p["id"] == posting_id]
    if not got:
        raise KeyError(f"공고 {posting_id} 가 postings 표에 없다 (python -m m1_competency.collect 로 스냅샷을 넣는다)")
    return got[0]


def _stored_lines(posting_id):
    return sorted((r for r in schema.read("posting_lines") if r["posting_id"] == posting_id), key=lambda r: r["n"])


def from_text(title, text):
    text = text.strip()
    return {"id": schema.stable_id("P", text), "title": title or "붙여넣은 공고", "source": "붙여넣기",
            "collected_at": datetime.now().isoformat(timespec="minutes"), "text": text}


def lines(posting):
    """공고 → 정제한 줄 [{line_id, tier, section, text, importance}]. 표에 있으면 표의 줄, 없으면 그 자리에서 정제한다."""
    rows = _stored_lines(posting["id"])
    if not rows:
        return competencies.refine(posting)["lines"]
    return [{"line_id": r["id"], "tier": r["tier"], "section": r["section"], "text": r["text"],
             "importance": r["importance"]} for r in rows]


def _line_rows(posting):
    r = competencies.refine(posting)
    return [{"id": x["line_id"], "posting_id": posting["id"], "n": n, "section": x["section"], "tier": x["tier"],
             "importance": x["importance"], "method": "규칙" if r["method"] == "규칙" else "llm", "text": x["text"]}
            for n, x in enumerate(r["lines"], 1)]


def save_posting(posting):
    """공고 하나와 정제한 줄을 표에 넣는다. 줄이 이미 있으면 그대로 둔다."""
    schema.write("postings", [posting])
    if not _stored_lines(posting["id"]):
        schema.write("posting_lines", _line_rows(posting))


def resume_lines(text):
    """이력서 글 → 면접관이 볼 줄 [{line_id, text}]. 머리 기호를 떼고 너무 짧은 줄은 뺀다."""
    rid = schema.stable_id("R", text.strip())
    rows = [s.strip().lstrip("-•·*#> ").strip() for s in text.splitlines()]
    return [{"line_id": f"{rid}-{n:02d}", "text": s} for n, s in enumerate([s for s in rows if len(s) >= 6][:60], 1)]


def save_resume(text, label=None, source=None):
    rid = schema.stable_id("R", text.strip())
    schema.write("resumes",
                 [{"id": rid, "label": label, "source": source,
                   "created_at": datetime.now().isoformat(timespec="minutes"), "text": text.strip()}])
    schema.write("resume_lines",
                 [{"id": x["line_id"], "resume_id": rid, "n": n, "text": x["text"]}
                  for n, x in enumerate(resume_lines(text), 1)])
    return rid


POSTINGS = config.COMPETENCY_DATA / "postings.jsonl"


def snapshots():
    return [json.loads(x) for x in POSTINGS.open(encoding="utf-8")] if POSTINGS.exists() else []


def build(refine=False):
    snaps = [{k: v for k, v in p.items() if k != "batch"} for p in snapshots()]
    schema.write("postings", snaps, replace=True)
    done = set() if refine else {r["posting_id"] for r in schema.read("posting_lines")}
    rows = [x for p in load_postings() if p["id"] not in done for x in _line_rows(p)]
    schema.write("posting_lines", rows, replace=refine)
    print(f"공고 {len(snaps)}건 → postings 표 {len(load_postings())}건, 새로 정제한 줄 {len(rows)}개")
    for path in sorted((config.COMPETENCY_DATA / "resumes").glob("*.md")):
        save_resume(path.read_text(encoding="utf-8"), label=path.name, source=str(path.relative_to(config.ROOT)))
    print(f"이력서 → resumes 표 {len(schema.read('resumes'))}건")


# 구직 사이트(사람인, 원티드 등)는 약관이 막으므로 쓰지 않는다.

KR_ID = "K"
MIN_BODY = 120


def _day(s):
    return (s or "")[:10] if re.match(r"\d{4}-\d\d-\d\d", s or "") else (s or "")


def _next_data(page):
    return json.loads(re.search(r'__NEXT_DATA__[^>]*>(.*?)</script>', page, re.S).group(1))


def from_greenhouse(c):
    for j in json.loads(web.polite_get(
            f"https://boards-api.greenhouse.io/v1/boards/{c['token']}/jobs?content=true"))["jobs"]:
        yield {"title": j["title"], "url": j["absolute_url"], "location": j["location"]["name"],
               "updated": _day(j["updated_at"]), "html": j["content"]}


def from_ashby(c):
    for j in json.loads(web.polite_get(f"https://api.ashbyhq.com/posting-api/job-board/{c['token']}"))["jobs"]:
        yield {"title": j["title"], "url": j["jobUrl"], "location": j["location"], "updated": _day(j["publishedAt"]),
               "html": j["descriptionHtml"]}


def from_lever(c):
    for j in json.loads(web.polite_get(f"https://api.lever.co/v0/postings/{c['token']}?mode=json")):
        yield {"title": j["text"], "url": j["hostedUrl"], "location": j["categories"].get("location", ""),
               "updated": "",
               "html": j["description"] + "".join(f"<h3>{x['text']}</h3>{x['content']}" for x in j["lists"])}


def from_greeting(c):
    """Greeting 채용 사이트: sitemap.xml 의 /o/번호 가 공고, 본문은 페이지 안 __NEXT_DATA__ 에 있다."""
    base = f"https://{c['token']}.career.greetinghr.com"
    for n in dict.fromkeys(re.findall(r"/o/(\d+)", web.polite_get(f"{base}/sitemap.xml"))):
        q = next(q
                 for q in _next_data(
                         web.polite_get(f"{base}/o/{n}"))["props"]["pageProps"]["dehydratedState"]["queries"]
                 if q["queryKey"][1] == "getOpeningById")
        o = q["state"]["data"]["data"]["openingsInfo"]
        if o["status"] == "OPEN":
            yield {"title": o["title"], "url": f"{base}/o/{n}", "updated": _day(o["openDate"]), "html": o["detail"]}


def from_kakao(c):
    page, last = 1, 1
    while page <= last:
        d = json.loads(web.polite_get(
            f"https://careers.kakao.com/public/api/job-list?skillSet=&part=TECHNOLOGY&company=ALL&keyword=&employeeType=&page={page}"))
        page, last = page + 1, d["totalPage"]
        for j in d["jobList"]:
            body = "".join(f"<h3>{h}</h3>{j[k]}"
                           for h, k in (("조직소개", "introduction"), ("업무내용", "workContentDesc"),
                                        ("자격요건", "qualification"), ("전형절차", "jobOfferProcessDesc"))
                           if j.get(k) not in (None, "", "-"))
            yield {"company": j["companyName"], "title": j["jobOfferTitle"],
                   "url": f"https://careers.kakao.com/jobs/{j['realId']}", "updated": _day(j["regDate"]), "html": body}


_NAVER_HOSTS = ("recruit.navercorp.com", "recruit.navercloudcorp.com", "recruit.naverfincorp.com",
                "recruit.naverins.com", "recruit.naverlabs.com", "recruit.snowcorp.com", "recruit.webtoonscorp.com")


def from_naver(c):
    """네이버 대표 채용 사이트와 계열사 채용 사이트는 같은 loadJobList.do 를 쓴다. 쪽마다 10건, totalSize 까지 읽고 annoId 가 같은 것은 한 번만 낸다."""
    seen = set()
    for host in _NAVER_HOSTS:
        first, total = 0, 1
        while first < total:
            d = json.loads(web.polite_get(f"https://{host}/rcrt/loadJobList.do?firstIndex={first}"))
            first, total = first + len(d["list"]), d["totalSize"]
            if not d["list"]:
                break
            for j in d["list"]:
                if j["annoId"] in seen:
                    continue
                seen.add(j["annoId"])
                page = web.polite_get(j["jobDetailLink"])
                ymd = j["staYmd"]
                yield {"company": j["sysCompanyCdNm"], "title": j["annoSubject"], "url": j["jobDetailLink"],
                       "updated": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}",
                       "html": page[page.find('class="detail_wrap">'):page.find("© NAVER")]}


def from_toss(c):
    """토스: career/sitemap.xml 의 job-detail 주소를 읽는다. 본문이 job["content"] 에만 있다고 보면 안 된다.
    공고 79건은 content 가 '#LI-DNI' 한 줄이고 진짜 본문(팀 소개·업무·자격)은 job["description"](마크다운)에 든다. 둘을 이어 붙인다."""
    for u in dict.fromkeys(re.findall(r"<loc>(https://toss\.im/career/job-detail\?job_id=\d+)",
                                      web.polite_get("https://toss.im/career/sitemap.xml"))):
        q = next((q
                  for q in _next_data(
                          web.polite_get(u))["props"]["pageProps"]["prefetchResult"]["dehydratedState"]["queries"]
                  if q["queryKey"][1] == "job-detail"), None)
        job = json.loads(q["state"]["data"])["job"] if q and q["state"]["data"] else None
        if job:
            yield {"title": job["title"], "url": u, "updated": _day(job.get("updatedAt") or job.get("createdAt")),
                   "html": f"{job.get('content') or ''}\n{job.get('description') or ''}"}


def from_line(c):
    """LINE: page-data.json 에 목록과 본문이 모두 있다. 한국 도시(분당·서울·과천)의 게시 중(publish) 공고만 읽는다."""
    base = "https://careers.linecorp.com"
    for e in json.loads(web.polite_get(
            f"{base}/page-data/ko/jobs/page-data.json"))["result"]["data"]["allStrapiJobs"]["edges"]:
        n = e["node"]
        if n["publish"] and any(x["name"] in ("Bundang", "Seoul", "Gwacheon") for x in n["cities"]):
            j = json.loads(web.polite_get(
                f"{base}/page-data/ko/jobs/{n['strapiId']}/page-data.json"))["result"]["data"]["strapiJobs"]
            yield {"company": n["companies"][0]["name"] if n["companies"] else None, "title": n["title"],
                   "url": f"{base}/ko/jobs/{n['strapiId']}", "location": "Korea", "updated": _day(n["start_date"]),
                   "html": j["content"]}


def from_smilegate(c):
    base = "https://careers.smilegate.com"
    body = json.dumps({"careerTypeCd": [], "companyCd": [], "gameGenreCd": [], "hireTypeCd": [], "jobDtlCd": [],
                       "jobMainCd": [], "keyword": None, "pageIndex": 1, "pageSize": 500, "projectSeq": None,
                       "usreId": None})
    for a in json.loads(web.polite_get(f"{base}/api/apply/announce/guest", body.encode(),
                                       {"Content-Type": "application/json"}))["announce"]:
        j = json.loads(web.polite_get(f"{base}/api/apply/announce/guest/{a['announceSeq']}"))
        parts = (("담당업무", "workInfo"), ("자격요건", "qualificationDesc"), ("우대사항", "specialDesc"), ("요구 역량", "abilityDesc"),
                 ("기타 안내", "description"))
        yield {"company": a["companyNm"], "title": a["title"],
               "url": f"{base}/apply/announce/view?seq={a['announceSeq']}", "updated": "",
               "html": "".join(f"<h3>{h}</h3>{j[k]}" for h, k in parts if j.get(k) not in (None, "", "-"))}


def from_workable(c):
    for j in json.loads(web.polite_get(
            f"https://apply.workable.com/api/v1/widget/accounts/{c['token']}?details=true"))["jobs"]:
        yield {"title": j["title"], "url": j["url"], "location": f"{j['city']}, {j['country']}",
               "updated": j["published_on"], "html": j["description"]}


def from_list(c):
    for u in dict.fromkeys(urljoin(c["careers_url"], m)
                           for m in re.findall(c["link_re"], web.polite_get(c["careers_url"]))):
        yield from from_page({**c, "urls": [u]})


def from_page(c):
    for u in c["urls"]:
        page = web.polite_get(u)
        body = re.search(c["body_re"], page, re.S).group(1) if c.get("body_re") else page
        title = (re.search(c["title_re"], page, re.S).group(1) if c.get("title_re")
                 else re.search(r"<title[^>]*>(.*?)</title>", page, re.S).group(1))
        yield {"title": web.html_text(title), "url": u, "updated": "", "html": body}


_JSON = {"Content-Type": "application/json"}


def _korea_facets(facets):
    """Workday 필터 목록을 끝까지 뒤져 'Korea' 값을 찾는다. 나라 필터가 있으면 그것을 먼저 쓴다."""
    found = []

    def walk(items, param):
        for f in items:
            p = f.get("facetParameter") or param
            if "Korea" in (f.get("descriptor") or "") and f.get("id"):
                found.append((p, f["id"]))
            walk(f.get("values") or [], p)

    walk(facets, None)
    found.sort(key=lambda x: "ountry" not in x[0])
    return found[:1]


def from_workday(c):
    """Workday 공개 JSON (/wday/cxs). 첫 요청의 필터 목록에서 한국 값을 찾아 그 필터로 목록만 받는다.
    c: host(예 'salesforce.wd12'), site(예 'External_Career_Site'), 선택 tenant(기본은 host 의 앞부분)."""
    tenant = c.get("tenant") or c["host"].split(".")[0]
    api = f"https://{c['host']}.myworkdayjobs.com/wday/cxs/{tenant}/{c['site']}"
    body = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
    first = json.loads(web.polite_get(f"{api}/jobs", json.dumps(body).encode(), _JSON))
    kr = _korea_facets(first.get("facets", []))
    if not kr:
        return
    body["appliedFacets"] = {kr[0][0]: [kr[0][1]]}
    rows, offset = [], 0
    while True:
        d = json.loads(web.polite_get(f"{api}/jobs", json.dumps({**body, "offset": offset}).encode(), _JSON))
        rows += d["jobPostings"]
        offset += 20
        if not d["jobPostings"] or offset >= d["total"]:
            break
    for r in rows:
        j = json.loads(web.polite_get(f"{api}{r['externalPath']}"))["jobPostingInfo"]
        yield {"title": j["title"], "url": j["externalUrl"],
               "location": "Korea, " + (j.get("location") or r.get("locationsText", "")),
               "updated": _day(j.get("startDate")), "html": j["jobDescription"]}


def from_amazon(c):
    """amazon.jobs 의 search.json. normalized_country_code 로 한국 공고만 받고 본문도 목록에 들어 있다."""
    offset, total = 0, 1
    while offset < total:
        d = json.loads(web.polite_get(
            f"https://www.amazon.jobs/en/search.json?normalized_country_code[]=KOR&result_limit=100&offset={offset}&sort=recent"))
        total, offset = d["hits"], offset + len(d["jobs"])
        if not d["jobs"]:
            break
        for j in d["jobs"]:
            body = "".join(f"<h3>{h}</h3>{j[k]}"
                           for h, k in (("업무", "description"), ("기본 자격", "basic_qualifications"),
                                        ("우대", "preferred_qualifications")) if j.get(k))
            yield {"title": j["title"], "url": f"https://www.amazon.jobs{j['job_path']}",
                   "location": "Korea, " + j["normalized_location"],
                   "updated": _day(j["posted_date"]) if re.match(r"\d{4}-", j["posted_date"]) else "", "html": body}


def from_kakaobank(c):
    """카카오뱅크 인재영입: POST /api/recruits 가 쪽(20건)별 목록, GET /api/recruits/번호 가 본문(contents)을 준다."""
    base = "https://recruit.kakaobank.com"
    page, last = 1, 1
    while page <= last:
        d = json.loads(web.polite_get(f"{base}/api/recruits", json.dumps({"pageNumber": page}).encode(), _JSON))
        page, last = page + 1, d["paging"]["totalPages"]
        for j in d["list"]:
            body = json.loads(web.polite_get(f"{base}/api/recruits/{j['recruitNoticeSn']}"))
            yield {"title": j["recruitNoticeName"], "url": f"{base}/jobs/{j['recruitNoticeSn']}", "location": "Korea",
                   "updated": _day(j["receiveStartDatetime"]),
                   "html": f"<h3>{j['recruitClassName']}</h3>{body.get('contents') or ''}"}


def from_lgcareers(c):
    """LG Careers(LG 그룹 전 계열사 공용): api.careers.lg.com/rmk 의 목록과 상세. 본문은 직무·자격요건·기타 안내 글이다."""
    api = "https://api.careers.lg.com/rmk/job"
    body = {"lnbSearch": "", "hashTagText": "", "recDate": "POST_START_DATE", "order": "DESC", "careerList": [],
            "companyCodeList": [], "desireLocList": [], "jobGroupList": []}
    for j in json.loads(web.polite_get(f"{api}/retrieveJobNoticesList", json.dumps(body).encode(),
                                       _JSON))["data"]["jobNoticeList"]:
        d = json.loads(web.polite_get(f"{api}/retrieveJobNoticesDetail",
                                      json.dumps({"jobNoticeId": j["jobNoticeId"]}).encode(),
                                      _JSON))["data"]["jobNoticesDetail"]["jobNoticesDetail"]
        parts = (("직군", j["jobGroupName"]), ("모집 분야", d.get("recruitJobName")), ("자격요건", d.get("qualForAppInfo")),
                 ("기타 안내", d.get("otherInfo")))
        yield {"company": j["companyName"], "title": j["jobNoticeName"],
               "url": f"https://careers.lg.com/apply/detail?id={j['jobNoticeId']}", "location": "Korea",
               "updated": _day(d["recStartDate"].replace(".", "-")),
               "html": "".join(f"<h3>{h}</h3><p>{(v or '').replace(chr(10), '<br>')}</p>" for h, v in parts if v)}


def from_ktgroup(c):
    """KT 그룹 채용(recruit.kt.com): /api/recruit 한 번에 진행 중 공고 전부와 본문(contents)이 온다. kt cs·kt cloud 등 계열사 공고가 함께 든다."""
    q = "currentPage=1&pageSize=200&isInProgress=true&isContainsContents=true"
    for j in json.loads(web.polite_get(f"https://recruit.kt.com/api/recruit?{q}"))["data"]:
        sectors = "".join(f"<li>{s['recruitSectorName']}</li>" for s in j.get("recruitSectorList") or [])
        yield {"company": j.get("company"), "title": j.get("title") or j["recruitNoticeName"],
               "url": f"https://recruit.kt.com/careers/{j['recruitNoticeSn']}", "location": "Korea",
               "updated": _day(j["receiveStartDatetime"]),
               "html": f"<h3>모집 분야</h3><ul>{sectors}</ul>{j.get('contents') or ''}"}


def from_netmarble(c):
    """넷마블: career.netmarble.com 의 공개 JSON. 목록 /api/v1/apply/announces, 본문 /announces/{id}/view 의 annoContents."""
    base = "https://career.netmarble.com/api/v1/apply/announces"
    for a in json.loads(web.polite_get(f"{base}?page=1&size=1000"))["content"]:
        j = json.loads(web.polite_get(f"{base}/{a['carAnnoId']}/view"))
        yield {"company": a["companyNm"], "title": a["annoSubject"],
               "url": f"https://career.netmarble.com/announce/view?anno_id={a['carAnnoId']}",
               "location": "Korea", "updated": _day(a["staDate"]), "html": j.get("annoContents") or ""}



def from_ninehire(c):
    """c['token'] 은 {token}.ninehire.site 의 앞부분. 목록은 api.ninehire.com 의 공개 JSON, 본문은 /job_posting/{addressKey} 페이지에 든다."""
    base = f"https://{c['token']}.ninehire.site"
    company_id = _next_data(web.polite_get(f"{base}/"))["props"]["pageProps"]["homepageProps"]["homepage"]["companyId"]
    for j in json.loads(web.polite_get(
            f"https://api.ninehire.com/identity-access/homepage/recruitments?companyId={company_id}"))["results"]:
        if j.get("status") != "in_progress" or not j.get("jobPostingIsActive"):
            continue
        url = f"{base}/job_posting/{j['addressKey']}"
        content = _next_data(web.polite_get(url))["props"]["pageProps"]["jobPosting"].get("content") or ""
        places = " ".join(p.get("addressName") or "" for p in j.get("jobLocations") or [])
        group = (j.get("jobGroup") or {}).get("title") or ""
        yield {"title": j["title"], "url": url, "location": places or None, "updated": _day(j["createdAt"]),
               "html": f"<h3>{group}</h3>{content}"}


def from_phenom(c):
    """Phenom 채용 사이트(HPE, Cisco 등): POST /widgets 로 나라 필터 목록, 상세 페이지의 JobPosting JSON-LD 에 본문이 있다.
    c: host(예 'careers.hpe.com'), path(상세 주소 앞부분, 예 'us/en'), country(필터 값, 예 'Korea, Republic of')."""
    base = f"https://{c['host']}"
    body = {"lang": "en_us", "deviceType": "desktop", "country": "us", "pageName": "search-results",
            "ddoKey": "refineSearch", "sortBy": "", "subsearch": "", "from": 0, "jobs": True, "counts": True,
            "all_fields": ["country"], "size": 50, "clearAll": False, "jdsource": "facets", "isSliderEnable": False,
            "pageId": "page11", "siteType": "external", "keywords": "", "global": True,
            "selected_fields": {"country": [c["country"]]}, "sort": {"order": "desc", "field": "postedDate"},
            "locationData": {}}
    offset, total = 0, 1
    while offset < total:
        d = json.loads(web.polite_get(f"{base}/widgets", json.dumps({**body, "from": offset}).encode(),
                                      _JSON))["refineSearch"]
        total, jobs = d["totalHits"], d["data"]["jobs"]
        offset += len(jobs)
        if not jobs:
            break
        for j in jobs:
            url = f"{base}/{c['path']}/job/{j['jobId']}"
            page = web.polite_get(url)
            ld = next((json.loads(m)
                       for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
                       if '"JobPosting"' in m), {})
            yield {"title": j["title"], "url": url, "location": j.get("cityStateCountry") or j.get("location", ""),
                   "updated": _day(j.get("postedDate")),
                   "html": html.unescape(ld.get("description") or j.get("descriptionTeaser", ""))}


def _apple_state(url):
    page = web.polite_get(url)
    return json.loads(json.loads('"' + re.search(r'window\.__staticRouterHydrationData = JSON\.parse\("(.*?)"\);', page,
                                                 re.S).group(1) + '"'))["loaderData"]


def from_apple(c):
    """Apple 채용(jobs.apple.com): 검색·상세 페이지에 든 __staticRouterHydrationData 에 목록(쪽당 20건)과 본문이 있다. c: location(예 'korea-republic-of-KOR')."""
    base = "https://jobs.apple.com/en-us"
    page, seen = 1, 0
    while True:
        sr = _apple_state(f"{base}/search?location={c['location']}&page={page}")["search"]
        for r in sr["searchResults"]:
            j = _apple_state(
                f"{base}/details/{r['positionId']}/{r['transformedPostingTitle']}")["jobDetails"]["jobsData"]
            parts = (("요약", "jobSummary"), ("업무", "description"), ("책임", "responsibilities"),
                     ("최소 자격", "minimumQualifications"), ("우대", "preferredQualifications"))
            yield {"title": r["postingTitle"],
                   "url": f"{base}/details/{r['positionId']}/{r['transformedPostingTitle']}",
                   "location": "Korea, " + ", ".join(x.get("name", "") for x in r["locations"]),
                   "updated": _day(r["postDateInGMT"]),
                   "html": "".join(f"<h3>{h}</h3><p>{(j.get(k) or '').replace(chr(10), '<br>')}</p>" for h, k in parts
                                   if j.get(k))}
        seen += len(sr["searchResults"])
        if not sr["searchResults"] or seen >= sr["totalRecords"]:
            return
        page += 1



ADAPTERS = {"greenhouse": from_greenhouse, "ashby": from_ashby, "lever": from_lever, "greeting": from_greeting,
            "kakao": from_kakao, "naver": from_naver, "toss": from_toss, "line": from_line, "smilegate": from_smilegate,
            "workable": from_workable,
            "workday": from_workday, "amazon": from_amazon, "kakaobank": from_kakaobank, "lgcareers": from_lgcareers,
            "ktgroup": from_ktgroup, "netmarble": from_netmarble,
            "ninehire": from_ninehire, "phenom": from_phenom, "apple": from_apple}
METHODS = {"list": from_list, "page": from_page}


def listings(c):
    return ADAPTERS[c["ats"]](c) if c["method"] == "api" else METHODS[c["method"]](c)


_PREFIX = re.compile(r"^\s*(\[[^\]]*\]\s*)+")
_TITLE = re.compile(
    r"(?<![A-Za-z])(AI|ML|LLM|NLP|MLOps|LLMOps|AIOps|GenAI|RAG|VLM|CV|GPU|NPU|SRE|FDE|ETL|DW|DBA|AX)(?![a-z])"
    r"|machine ?learning|deep ?learning|\bM/L\b|data ?(scien|engineer|analy|platform|infra|ops|warehouse|lake|mining|architect|governance)"
    r"|\banalytics?\b|research (scientist|engineer)|applied (scientist|research)|computer vision|speech|recommend|ranking|relevance|\bsearch"
    r"|devops|site reliability|(data|ml|ai|cloud|infra)[ -]?platform|infrastructure|kubernetes|\bk8s\b|foundation model|inference|agent\b|prompt|\bcloud|\baws\b|\bgcp\b|azure"
    r"|인공지능|머신러닝|딥러닝|데이터|분석가|애널리스트|연구|클라우드|추천|음성|비전|생성형|언어 ?모델|검색|에이전트|프롬프트|인프라|추론", re.I)
_ROLE = re.compile(r"engineer|developer|scientist|researcher|개발|엔지니어|연구|분석", re.I)
_BODY = re.compile(r"머신러닝|딥러닝|machine learning|deep learning|LLM|PyTorch|TensorFlow|MLOps|인공지능|생성형|데이터 ?(분석|엔지니어|사이언)",
                   re.I)
_NOT = re.compile(
    r"영업|마케|인사|재무|회계|법무|디자인|\bsales\b|marketing|recruit|\bHR\b|\bPR\b|홍보|총무|구매|세무|콘텐츠 ?제작|번역|통역|localization|counsel|legal|변호사|비서|세일즈|MD\b|정산|편집|"
    r"사업개발|business development|마케터|marketer|서비스 운영|사업기획|account (executive|manager)|go-to-market|operation manager",
    re.I)
_SOFT_NOT = re.compile(r"security|보안|compliance|컴플라이언스|\bCS\b|\bQA\b|\bhead\b|director|기획자|\bPM\b|\bPO\b|product (owner|manager)|program manager|운영기획|test automation", re.I)
_DATA_ML = re.compile(
    r"data ?(scien|engineer|analy|architect)|데이터|머신러닝|machine ?learning|\bML\b|\bAI\b|\bAX\b|\bDBA\b|\bSRE\b", re.I)
_KOREA = re.compile(r"korea|seoul|서울|판교|pangyo|성남|gyeonggi|경기|busan|부산|daejeon|대전|jeju|제주|대한민국|한국", re.I)


def is_ai_role(title, text):
    t = _PREFIX.sub("", title)
    if _NOT.search(t) or (_SOFT_NOT.search(t) and not _DATA_ML.search(t)):
        return False
    return bool(_TITLE.search(t)) or bool(_ROLE.search(t) and len(_BODY.findall(text)) >= 3)


def collect_company(c, now):
    """회사 하나 → (스냅샷에 넣을 공고, 집계). 집계 found 는 목록에 있던 전부, kept 는 직무·본문 검사를 통과한 수."""
    st = {"company": c["company"], "method": f"{c['method']}/{c.get('ats', '')}".rstrip("/"), "found": 0, "kept": 0,
          "final": 0, "thin": 0, "image": 0, "failures": []}
    out = []
    try:
        if c.get("skip"):
            raise web.Skipped(c["skip"])
        for r in listings(c):
            st["found"] += 1
            if r.get("location") and not _KOREA.search(r["location"]):
                continue
            text = web.html_text(r["html"])
            if len(text) < MIN_BODY:
                st["image" if "<img" in r["html"] else "thin"] += 1
                continue
            if is_ai_role(r["title"], text):
                out.append({"id": schema.stable_id(KR_ID, r["url"]), "company": r.get("company") or c["company"],
                            "title": web.html_text(r["title"]).replace("\n", " "), "url": r["url"],
                            "source": f"{c['method']}:{urlparse(r['url']).netloc}", "updated": r["updated"],
                            "collected_at": now, "text": text})
    except web.Skipped as e:
        st["failures"].append(str(e))
    except Exception as e:   # 한 회사가 실패해도 나머지는 계속한다. 이미 읽은 공고는 남긴다.
        st["failures"].append(f"{type(e).__name__}: {e}")
    st["kept"] = len(out)
    return out, st


def dedup(rows):
    """주소가 같거나 본문(문장부호 무시)이 같은 공고는 먼저 나온 것만 남긴다."""
    seen, out = set(), []
    for p in rows:
        keys = (p["url"], hash(schema.norm(p["text"])))
        if not seen & set(keys):
            out.append(p)
        seen |= set(keys)
    return out


def fetch(names=()):
    path = config.COMPETENCY_DATA / "companies.json"
    companies = [c for c in json.loads(path.read_text(encoding="utf-8")) if not names or c["key"] in names]
    now = datetime.now().isoformat(timespec="minutes")
    with ThreadPoolExecutor(8) as ex:   # 호스트마다 따로 초당 1번이므로 서로 다른 회사는 함께 돈다
        results = list(ex.map(lambda c: collect_company(c, now), companies))
    keep = {id(p) for p in dedup([p for posts, _ in results for p in posts])}
    batches = {}
    for c, (posts, st) in zip(companies, results):
        st["final"] = sum(id(p) in keep for p in posts)
        batches.setdefault(c["batch"], []).extend(p for p in posts if id(p) in keep)
    fresh = [{"batch": f"kr_{b}", **p} for b, posts in batches.items() for p in posts]
    kept = [p for p in snapshots() if p["batch"] not in {f"kr_{b}" for b in batches}]
    lines =[json.dumps(p, ensure_ascii=False) for p in sorted(kept + fresh, key=lambda p: p["batch"])]
    POSTINGS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report([st for _, st in results], now)


def report(stats, now):
    cols = ("found", "kept", "final", "image", "thin")
    total = Counter({k: sum(s[k] for s in stats) for k in cols})
    lines = [f"# 한국 회사 공고 수집 보고서\n\n수집 시각 {now}\n",
             "| 회사 | 방법 | 목록에 있던 공고 | 직무 검사 통과 | 중복 뺀 최종 | 본문 이미지 | 본문 빔·JS 전용 | 실패 |",
             "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {s['company']} | {s['method']} | {s['found']} | {s['kept']} | {s['final']} | {s['image']} | {s['thin']} | {'; '.join(s['failures'])[:160]} |" for s in stats]
    robots = sorted({f for s in stats for f in s["failures"] if f.startswith("robots")})
    lines += ["",
              f"합계: 회사 {len(stats)}곳, 실패 없음 {sum(not s['failures'] for s in stats)}곳. 목록 {total['found']}건, 직무 검사 통과 {total['kept']}건, 중복을 뺀 최종 {total['final']}건.",
              f"본문이 이미지라 뺀 공고 {total['image']}건, 본문이 비었거나 JS 전용이라 뺀 공고 {total['thin']}건.", "",
              "robots.txt 가 막은 곳:"] + [f"- {r}" for r in robots] * bool(robots)
    config.OUTPUTS.mkdir(parents=True, exist_ok=True)
    (config.OUTPUTS / "collect_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-5:]))


if __name__ == "__main__":
    if sys.argv[1:2] == ["fetch"]:
        fetch(sys.argv[2:])
    else:
        build(refine=sys.argv[1:] == ["refine"])
