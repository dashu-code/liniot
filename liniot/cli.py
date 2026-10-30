"""LinIoT 命令行入口：liniot run / simulate / version。"""
from __future__ import annotations

import argparse

from . import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="liniot", description="LinIoT — 轻量级 AIoT 开源平台")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="启动平台服务（API + 仪表盘）")
    run_p.add_argument("--host", default="127.0.0.1")
    run_p.add_argument("--port", type=int, default=8000)

    sim_p = sub.add_parser("simulate", help="启动虚拟设备模拟器")
    sim_p.add_argument("--url", default="http://127.0.0.1:8000")
    sim_p.add_argument("--sensors", type=int, default=2)
    sim_p.add_argument("--lights", type=int, default=2)
    sim_p.add_argument("--interval", type=float, default=5.0)
    sim_p.add_argument("--duration", type=float, default=0.0, help="演示时长秒数，0 表示一直运行")
    sim_p.add_argument("--seed", type=int, default=42)

    sub.add_parser("version", help="显示版本")

    args = parser.parse_args()
    if args.command == "run":
        _run(args.host, args.port)
    elif args.command == "simulate":
        _simulate(args)
    else:
        print(f"LinIoT v{__version__}")


def _run(host: str, port: int) -> None:
    import uvicorn

    from .main import create_app

    print(f"LinIoT v{__version__} 启动中 → http://{host}:{port}"
          f"（API 文档: http://{host}:{port}/docs）")
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


def _simulate(args: argparse.Namespace) -> None:
    from .simulator import Simulator

    Simulator(base_url=args.url, sensors=args.sensors, lights=args.lights,
              interval=args.interval, seed=args.seed,
              duration=args.duration).run()


if __name__ == "__main__":
    main()
