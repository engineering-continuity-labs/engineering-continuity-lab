"""Small JSON CLI; identical evidence and configuration across all views."""
import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys
import tomllib

from continuity.analysis.service import analyze, resolve_person, simulate_departure
from continuity.domain.models import DirectoryComponents
from continuity.git.history import GitHistory
from continuity.scoring.model import ScoringConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experimental Git activity proxy for continuity risk")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("analyze", "person", "simulate-departure"):
        cmd = commands.add_parser(name)
        if name != "analyze":
            cmd.add_argument("contributor", help="exact author name or email")
        cmd.add_argument("--repo", type=Path, default=Path("."))
        cmd.add_argument("--component-depth", type=int, default=1)
        cmd.add_argument("--config", type=Path, help="TOML scoring configuration")
        cmd.add_argument("--as-of", help="ISO timestamp with timezone; defaults to newest author date")
    args = parser.parse_args(argv)
    try:
        raw = tomllib.loads(args.config.read_text()) if args.config else {}
        if set(raw) - {"weights", "half_life_days"}:
            raise ValueError("unknown configuration keys")
        if "weights" in raw and (not isinstance(raw["weights"], dict) or
                any(not isinstance(v, (int, float)) for v in raw["weights"].values())):
            raise ValueError("weights must be a table of numbers")
        if "half_life_days" in raw and not isinstance(raw["half_life_days"], (int, float)):
            raise ValueError("half_life_days must be a number")
        config = ScoringConfig(**raw)
        strategy = DirectoryComponents(args.component_depth)
        report = analyze(GitHistory(args.repo).read(), strategy, config,
                         datetime.fromisoformat(args.as_of) if args.as_of else None)
        output = {"model": "experimental-v0.1", "warning": "Git activity is only a proxy for knowledge.",
                  "configuration": {"weights": dict(config.weights), "half_life_days": config.half_life_days,
                                    "component_depth": strategy.depth},
                  "revision": report.revision, "as_of": report.as_of.isoformat(),
                  "shallow": report.shallow, "commit_count": report.commit_count}
        if args.command == "analyze":
            output["components"] = [asdict(c) for c in report.components]
        else:
            person = resolve_person(report, args.contributor)
            output["contributor"] = person
            if args.command == "person":
                output["components"] = [{"component": c.component, **asdict(p)}
                    for c in report.components for p in c.contributors if p.contributor == person]
            else:
                output["impacts"] = [asdict(i) for i in simulate_departure(report, person)]
        print(json.dumps(output, indent=2, ensure_ascii=True))
        return 0
    except (ValueError, OSError, TypeError, OverflowError) as exc:
        print(f"continuity: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
