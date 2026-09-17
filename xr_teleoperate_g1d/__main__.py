import argparse
import json
import sys
import time
from typing import Iterable

from .drivers import DirectDdsMotionDriver, DryRunDriver, Sdk2BridgeDriver
from .input_schema import TeleopInput
from .mapping import map_input, xrobotoolkit_mapping
from .recorder import Recorder
from .xr_adapter import XRoboToolkitSource


def _jsonl_samples(path: str) -> Iterable[TeleopInput]:
    stream = sys.stdin if path == "-" else open(path, "r", encoding="utf-8")
    try:
        for line in stream:
            if line.strip():
                yield TeleopInput.from_mapping(json.loads(line))
    finally:
        if stream is not sys.stdin:
            stream.close()


def _demo_samples() -> Iterable[TeleopInput]:
    yield TeleopInput(left_y=0.5, right_x=-0.25, right_y=0.4, left_trigger=0.2, right_trigger=0.8)
    yield TeleopInput(motion_ready=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="G1-D normalized motion and collection bridge")
    parser.add_argument("--source", choices=["demo", "jsonl", "xrobotoolkit"], default="demo")
    parser.add_argument("--input", default="-", help="JSONL path, or - for stdin")
    parser.add_argument("--driver", choices=["dry-run", "dds", "sdk2-bridge"], default="dry-run")
    parser.add_argument("--network-interface", default="eth0")
    parser.add_argument("--bridge-binary", default="./build/g1d_agv_bridge")
    parser.add_argument("--watchdog-ms", type=int, default=300)
    parser.add_argument("--no-dex1", action="store_true", help="disable Dex1 in direct DDS mode")
    parser.add_argument("--mapping", choices=["g1d", "xrobotoolkit"], default="g1d")
    parser.add_argument("--record")
    parser.add_argument("--rate", type=float, default=30.0)
    args = parser.parse_args()

    if args.driver == "dds":
        driver = DirectDdsMotionDriver(args.network_interface, enable_dex1=not args.no_dex1)
    elif args.driver == "sdk2-bridge":
        driver = Sdk2BridgeDriver(args.bridge_binary, args.network_interface, args.watchdog_ms)
    else:
        driver = DryRunDriver()

    source = None
    if args.source == "jsonl":
        samples = _jsonl_samples(args.input)
    elif args.source == "xrobotoolkit":
        source = XRoboToolkitSource()

        def live_samples() -> Iterable[TeleopInput]:
            while True:
                yield source.read()

        samples = live_samples()
    else:
        samples = _demo_samples()

    recorder = Recorder(args.record) if args.record else None
    map_fn = xrobotoolkit_mapping if args.mapping == "xrobotoolkit" else map_input
    period = 1.0 / args.rate
    try:
        for sample in samples:
            start = time.monotonic()
            frame = map_fn(sample)
            states = driver.send(frame)
            if recorder:
                recorder.write(frame, states=states)
            time.sleep(max(0.0, period - (time.monotonic() - start)))
    except KeyboardInterrupt:
        pass
    finally:
        if recorder:
            recorder.close()
        if source:
            source.close()
        driver.close()


if __name__ == "__main__":
    main()
