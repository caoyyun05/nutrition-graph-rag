"""Run or prepare a multi-model, repeated LLM recommendation audit."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ..config import DATA_DIR, RESULTS_DIR, ROOT_DIR


DEFAULT_USDA_FOODS = ROOT_DIR / "data_usda_55" / "foods_usda_55.csv"
DEFAULT_USDA_SCENARIOS = ROOT_DIR / "data_usda_55" / "test_scenarios_usda_90.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        action="append",
        required=True,
        help=(
            "Model spec in provider:model format, for example "
            "kimi:moonshot-v1-8k or openai:gpt-4o-mini. Repeat for multiple models."
        ),
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--scenario-id", action="append")
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate prompts and manifest without calling external LLM APIs.",
    )
    parser.add_argument("--foods-csv", default=str(DEFAULT_USDA_FOODS))
    parser.add_argument("--constraints-csv", default=str(DATA_DIR / "nutrient_constraints.csv"))
    parser.add_argument("--scenarios-csv", default=str(DEFAULT_USDA_SCENARIOS))
    parser.add_argument(
        "--output-dir",
        default="multi_llm_audit_usda_pilot",
        help="Directory under results_v2, or an absolute path.",
    )
    args = parser.parse_args()

    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be >= 1")

    output_dir = _resolve_results_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    for spec in args.model:
        provider, model = _parse_model_spec(spec)
        model_slug = _slug(f"{provider}_{model}")
        for repeat in range(1, args.repeats + 1):
            run_id = f"{model_slug}_r{repeat:02d}"
            run_output_json = output_dir / f"{run_id}.json"
            raw_dir = output_dir / "raw_outputs" / run_id
            command = _build_command(
                provider=provider,
                model=model,
                repeat=repeat,
                output_json=run_output_json,
                raw_dir=raw_dir,
                args=args,
            )
            print(f"[{run_id}] {'dry-run' if args.dry_run else 'calling API'}")
            process = subprocess.run(
                command,
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
            manifest_rows.append(
                {
                    "run_id": run_id,
                    "provider": provider,
                    "model": model,
                    "repeat": repeat,
                    "dry_run": args.dry_run,
                    "returncode": process.returncode,
                    "output_json": str(run_output_json),
                    "raw_output_dir": str(raw_dir),
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                }
            )
            if process.returncode != 0:
                print(process.stdout)
                print(process.stderr, file=sys.stderr)
                raise SystemExit(process.returncode)

    manifest = {
        "metadata": {
            "runner": "run_multi_llm_audit",
            "dry_run": args.dry_run,
            "models": [_parse_model_spec(spec) for spec in args.model],
            "repeats": args.repeats,
            "limit": args.limit,
            "scenario_ids": args.scenario_id or [],
            "foods_csv": args.foods_csv,
            "constraints_csv": args.constraints_csv,
            "scenarios_csv": args.scenarios_csv,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "sleep_seconds": args.sleep_seconds,
        },
        "runs": manifest_rows,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved multi-LLM audit manifest to {manifest_path}")


def _build_command(
    provider: str,
    model: str,
    repeat: int,
    output_json: Path,
    raw_dir: Path,
    args: argparse.Namespace,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "src_v3.experiments.run_real_llm_baseline",
        "--provider",
        provider,
        "--model",
        model,
        "--temperature",
        str(args.temperature),
        "--max-tokens",
        str(args.max_tokens),
        "--sleep-seconds",
        str(args.sleep_seconds),
        "--output-json",
        str(output_json),
        "--raw-output-dir",
        str(raw_dir),
        "--foods-csv",
        args.foods_csv,
        "--constraints-csv",
        args.constraints_csv,
        "--scenarios-csv",
        args.scenarios_csv,
    ]
    if args.limit:
        command.extend(["--limit", str(args.limit)])
    for scenario_id in args.scenario_id or []:
        command.extend(["--scenario-id", scenario_id])
    if args.dry_run:
        command.append("--dry-run")
    # Repeat number is encoded in output paths. The LLM prompt is intentionally
    # unchanged so repeated calls measure generation variability.
    _ = repeat
    return command


def _parse_model_spec(spec: str) -> tuple[str, str]:
    provider, sep, model = spec.partition(":")
    if not sep or not provider.strip() or not model.strip():
        raise SystemExit(f"Invalid --model spec '{spec}'. Use provider:model.")
    return provider.strip(), model.strip()


def _slug(value: str) -> str:
    chars = []
    for char in value.lower():
        chars.append(char if char.isalnum() else "_")
    return "_".join(part for part in "".join(chars).split("_") if part)


def _resolve_results_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else RESULTS_DIR / path


if __name__ == "__main__":
    main()
