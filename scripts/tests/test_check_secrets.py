"""Tests for the pre-commit secret scanner.

The scanner is a gate, and the only honest way to test a gate is to break it.
Every case here feeds it something that must trip it, or something that must
not, rather than asserting it stays quiet on a repo that happens to be clean —
a scanner that matches nothing passes such a test perfectly.

The motivating case is real: a plaintext MQTT broker password sat committed for
nine months and this scanner reported the file CLEAN. The generic key rule only
matched keys literally named api_key/apikey/secret_key, and the value was 14
characters against a 16-character floor — two independent reasons to miss it
(TAP-6399).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_SCANNER = Path(__file__).resolve().parents[1] / "check-secrets.py"
_spec = importlib.util.spec_from_file_location("check_secrets", _SCANNER)
check_secrets = importlib.util.module_from_spec(_spec)
sys.modules["check_secrets"] = check_secrets
_spec.loader.exec_module(check_secrets)


def _scan(tmp_path: Path, name: str, body: str) -> list[tuple[int, str, str]]:
    target = tmp_path / name
    target.write_text(body, encoding="utf-8")
    return check_secrets.check_file(str(target))


class TestTheRegressionThatMotivatedThis:
    def test_a_broker_config_with_a_plaintext_password_is_caught(self, tmp_path):
        # The exact shape of the file that was committed, with a synthetic
        # value. Before this rule existed the scanner returned no findings.
        findings = _scan(
            tmp_path,
            "mqtt_zigbee_config.json",
            "{\n"
            '  "MQTT_BROKER": "mqtt://192.168.1.100:1883",\n'
            '  "MQTT_PASSWORD": "Fake24synth!@",\n'
            '  "MQTT_USERNAME": "synthetic-user"\n'
            "}\n",
        )
        assert findings, "the scanner is blind to a plaintext password field again"
        assert any("password" in reason.lower() for _, _, reason in findings)

    def test_a_short_password_is_caught(self):
        # The real value was 14 characters; the pre-existing generic rule had a
        # 16-character floor. Length must not be what decides this.
        pattern = next(
            p for p, reason in check_secrets.SECRET_PATTERNS if reason == "Hardcoded password"
        )
        assert pattern.search('"MQTT_PASSWORD": "sh0rt!"')


class TestPasswordDetection:
    @pytest.mark.parametrize(
        "line",
        [
            '"MQTT_PASSWORD": "Fake24synth!@"',
            "PASSWORD = 'hunter2xyz'",
            'db_password: "s3cr3t-value"',
            "PASSWD='another-real-one'",
            'pwd = "yetanother1"',
            '"password":"nospacehere"',
        ],
    )
    def test_real_looking_values_trip_the_gate(self, tmp_path, line):
        assert _scan(tmp_path, "config.json", line), f"missed: {line}"

    @pytest.mark.parametrize(
        "line",
        [
            "MQTT_PASSWORD=replace-with-mqtt-password",
            "MQTT_PASSWORD=<YOUR_MQTT_PASSWORD>",
            "MQTT_PASSWORD=",
            'password = os.getenv("MQTT_PASSWORD")',
            "password: process.env.MQTT_PASSWORD",
            'password = "${MQTT_PASSWORD}"',
            'password: "changeme"',
            "# password: 'this-is-a-comment'",
            # A variable reference names a secret; it does not contain one.
            'PGPASSWORD="$TEST_PASSWORD"',
            'POSTGRES_PASSWORD="$DB_PASS"',
        ],
    )
    def test_placeholders_and_env_reads_do_not_trip_it(self, tmp_path, line):
        # A scanner that cries wolf on every template gets disabled, which is
        # how you end up with no scanner at all.
        assert not _scan(tmp_path, "config.yml", line), f"false positive: {line}"


class TestPreExistingRulesStillWork:
    @pytest.mark.parametrize(
        "line,expected",
        [
            ("VITE_API_KEY=abcdef1234567890", "VITE_ secret env var with hardcoded value"),
            ('api_key = "abcdefghij1234567890"', "Hardcoded API key or secret"),
            ('"Bearer abcdefghij1234567890abcdef"', "Hardcoded Bearer token"),
            ("AKIAIOSFODNN7EXAMPLE", "AWS access key"),
            ("-----BEGIN RSA PRIVATE KEY-----", "Private key"),
        ],
    )
    def test_each_original_pattern_still_fires(self, tmp_path, line, expected):
        findings = _scan(tmp_path, "app.py", line)
        assert findings, f"regressed: {line}"
        assert findings[0][2] == expected


class TestSkips:
    def test_this_files_own_corpus_is_skipped(self):
        # Deliberate, not an oversight: the vectors above are live-looking by
        # design, so the hook would block every commit touching this file.
        assert "test_check_secrets.py" in check_secrets.SKIP_PATTERNS

    def test_lockfiles_are_skipped(self, tmp_path):
        assert not _scan(tmp_path, "package.lock", 'password: "realvalue123"')

    def test_a_clean_file_yields_nothing(self, tmp_path):
        assert not _scan(tmp_path, "clean.py", "x = 1\ny = 2\n")
