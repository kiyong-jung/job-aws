"""수집·정리 명령이 겹쳐 돌지 않게: 같은 모듈의 다른 프로세스가 돌고 있으면 멈춘다."""
import os
import subprocess


def others_running(module, skip=()):
    """`python -m <module> …` 로 도는 다른 프로세스의 명령줄 목록. 이 프로세스와 skip 에 든 pid 는 뺀다."""
    out = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True, text=True).stdout
    mine = {os.getpid(), os.getppid(), *skip}
    found = []
    for line in out.splitlines():
        pid, _, cmd = line.strip().partition(" ")
        if pid.isdigit() and int(pid) not in mine and f"-m {module}" in cmd:
            found.append(cmd.strip())
    return found


def refuse_if_running(module, what):
    busy = others_running(module)
    if busy:
        raise SystemExit(f"{what}: {module} 프로세스가 돌고 있어 멈춘다 ({len(busy)}개). 끝난 뒤 다시 실행.\n" + "\n".join(busy))
