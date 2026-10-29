"""W02-G4: canonical hashes and deterministic offline replay CLI."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from erratascope_domain import evaluate, parse_bundle
from erratascope_domain.canonical import dump_model

from tests import helpers as H


class ReplayTests(unittest.TestCase):
    def _fixture_copy(self, directory: Path, name: str = "applicable.json") -> Path:
        source = H.FIXTURE_DIR / name
        target = directory / name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return target

    def test_connected_fixture_journey(self) -> None:
        raw = H.load_fixture("applicable.json")
        bundle = parse_bundle(raw)
        result = evaluate(bundle)
        self.assertEqual(result.rules[0].applicability, "applicable")
        self.assertEqual(len(result.input_hash), 64)
        self.assertEqual(len(result.result_hash), 64)
        self.assertEqual(result.rules[0].overall, "true")
        self.assertEqual(
            [item.selector for item in result.selector_dependencies],
            [
                "component.silicon_revision",
                "firmware.initial_software_reset",
                "operating.external_reset_used",
                "operating.reset_pulse_ns",
            ],
        )

    def test_cli_twice_in_fresh_processes_is_byte_identical(self) -> None:
        with H.temp_dir("w02-test") as temp:
            directory = Path(temp)
            first = directory / "replay-a.json"
            second = directory / "replay-b.json"
            completed_a = H.run_replay(H.FIXTURE_DIR / "applicable.json", first)
            completed_b = H.run_replay(H.FIXTURE_DIR / "applicable.json", second)
            self.assertEqual(completed_a.returncode, 0, completed_a.stderr)
            self.assertEqual(completed_b.returncode, 0, completed_b.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            first_result = json.loads(first.read_text(encoding="utf-8"))
            second_result = json.loads(second.read_text(encoding="utf-8"))
            self.assertEqual(first_result["result_hash"], second_result["result_hash"])
            self.assertIn(f"result_hash={first_result['result_hash']}", completed_a.stdout)

    def test_changed_semantic_input_changes_hashes(self) -> None:
        short_pulse = H.evaluate_raw(H.build_raw())
        long_pulse = H.evaluate_raw(
            H.build_raw(
                facts=(
                    H.fact("component.silicon_revision", H.text("B")),
                    H.fact("operating.external_reset_used", H.boolean(True)),
                    H.fact("operating.reset_pulse_ns", H.quantity("30", "ns")),
                    H.fact("firmware.initial_software_reset", H.boolean(False)),
                )
            )
        )
        self.assertNotEqual(short_pulse.input_hash, long_pulse.input_hash)
        self.assertNotEqual(short_pulse.result_hash, long_pulse.result_hash)
        self.assertEqual(short_pulse.rules[0].applicability, "applicable")
        self.assertEqual(long_pulse.rules[0].applicability, "not_applicable")

    def test_invalid_input_never_replaces_existing_output(self) -> None:
        with H.temp_dir("w02-test") as temp:
            directory = Path(temp)
            output = directory / "result.json"
            output.write_text('{"previous": "valid"}\n', encoding="utf-8")
            invalid_input = directory / "invalid.json"
            raw = H.load_fixture("applicable.json")
            raw["snapshot"]["content_hash"] = "0" * 64
            invalid_input.write_text(json.dumps(raw), encoding="utf-8")
            completed = H.run_replay(invalid_input, output)
            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), '{"previous": "valid"}\n')
            self.assertIn("HASH_MISMATCH", completed.stderr)

    def test_malformed_json_input_exit_2(self) -> None:
        with H.temp_dir("w02-test") as temp:
            directory = Path(temp)
            bad = directory / "bad.json"
            bad.write_text("{not-json", encoding="utf-8")
            job = H.run_replay(bad, directory / "out.json")
            self.assertEqual(job.returncode, 2)

    def test_missing_input_exit_1(self) -> None:
        with H.temp_dir("w02-test") as temp:
            directory = Path(temp)
            job = H.run_replay(directory / "missing.json", directory / "out.json")
            self.assertEqual(job.returncode, 1)

    def test_successful_output_is_atomic_and_normalized(self) -> None:
        with H.temp_dir("w02-test") as temp:
            directory = Path(temp)
            output = directory / "result.json"
            completed = H.run_replay(H.FIXTURE_DIR / "applicable.json", output)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(output.read_bytes().endswith(b"\n"))
            self.assertEqual(list(directory.glob(".*.tmp")), [])
            first = json.loads(output.read_text(encoding="utf-8"))
            in_process = H.evaluate_raw(H.load_fixture("applicable.json"))
            self.assertEqual(first["result_hash"], in_process.result_hash)
            self.assertEqual(
                json.dumps(first["rules"][0]["applicability"]),
                json.dumps("applicable"),
            )

    def test_unknown_results_still_exit_zero(self) -> None:
        with H.temp_dir("w02-test") as temp:
            directory = Path(temp)
            completed = H.run_replay(
                H.FIXTURE_DIR / "unknown_revision.json", directory / "unknown.json"
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((directory / "unknown.json").read_text(encoding="utf-8"))
            self.assertEqual(result["rules"][0]["applicability"], "unknown")

    def test_in_process_evaluation_is_repeatable(self) -> None:
        bundle = parse_bundle(H.load_fixture("conflicting.json"))
        first = dump_model(evaluate(bundle))
        second = dump_model(evaluate(bundle))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

