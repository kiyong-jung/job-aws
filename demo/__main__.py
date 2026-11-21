"""python -m demo [--live] [--port 8770] [--speed 1.0]

--live   예시가 아닌 새 공고도 끝까지 돈다 (역량 뽑기에 AI 비용이 든다). 없으면 예시 공고만 다시 튼다
--speed  다시 틀기 간격 배수. 0 이면 기다리지 않는다
"""
import argparse

from demo.server import serve


def main():
    ap = argparse.ArgumentParser(prog="python -m demo")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()
    srv = serve(a.host, a.port, a.live, a.speed)
    print(f"데모: http://{a.host}:{a.port}/  ({'새 공고도 실제로 분석' if a.live else '예시 공고만'}). 끄려면 Ctrl+C", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
