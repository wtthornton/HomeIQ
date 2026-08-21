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

    @pytest.mark.parametrize(
        "filename,line",
        [
            (".env", "MQTT_PASSWORD=Zt7pQm4wLx"),
            (".env.production", "DB_PASSWORD=Zt7pQm4wLx"),
            ("env.websocket-ingestion", "MQTT_PASSWORD=Zt7pQm4wLx"),
            ("settings.ini", "password=Zt7pQm4wLx"),
            ("app.conf", "password = Zt7pQm4wLx"),
        ],
    )
    def test_unquoted_values_in_env_files_are_caught(self, tmp_path, filename, line):
        # The first password rule required a quoted value, so every one of these
        # slipped past. admin-api's config writer emits `f"{key}={value}\n"` into
        # a read-write bind mount, so this is the shape a credential written back
        # through that route would actually take.
        assert _scan(tmp_path, filename, line), f"missed unquoted: {filename} :: {line}"

    @pytest.mark.parametrize(
        "filename,line",
        [
            ("docker-compose.yml", "  MQTT_PASSWORD: Zt7pQm4wLx"),
            ("config.yaml", "password: Zt7pQm4wLx"),
            ("pyproject.toml", "password = Zt7pQm4wLx"),
        ],
    )
    def test_unquoted_yaml_and_toml_are_a_deliberate_gap(self, tmp_path, filename, line):
        # Characterisation, not aspiration. The unquoted rule is scoped to
        # env/ini-shaped files on purpose: extending it to YAML flagged every CI
        # workflow's throwaway service-container password
        # (`POSTGRES_PASSWORD: homeiq_test`), and a hook that blocks unrelated
        # workflow edits gets switched off. YAML and TOML conventionally quote
        # their values, which the quoted rule above already covers.
        #
        # If you widen `_is_config_file`, this test fails — which is the point.
        # Decide consciously and update it, rather than widening by accident.
        assert not _scan(tmp_path, filename, line)

    def test_the_quoted_rule_still_covers_yaml(self, tmp_path):
        # The gap above is only the unquoted form.
        assert _scan(tmp_path, "docker-compose.yml", '  MQTT_PASSWORD: "Zt7pQm4wLx"')

    @pytest.mark.parametrize(
        "line",
        [
            "password=None",
            "password = None",
            "password: str",
            "password: bool = False",
            "self.password = get_password()",
            "password = self._password",
        ],
    )
    def test_unquoted_matching_does_not_fire_in_source_code(self, tmp_path, line):
        # Unquoted matching is meaningless in code: a default, a type annotation
        # and a call are all four-plus characters and none is a secret.
        assert not _scan(tmp_path, "service.py", line), f"false positive: {line}"


class TestPlaceholderFilteringDoesNotWeakenOtherRules:
    """A filter added for one rule must not silently disarm the others.

    Both of these shipped broken and were caught by an adversarial verifier, not
    by the suite — which is why they are pinned here now.
    """

    def test_a_marker_word_elsewhere_on_the_line_does_not_silence_the_quoted_rule(self, tmp_path):
        # The literal markers for the unquoted rule were appended to the SHARED
        # placeholder tuple, and placeholder matching is a substring test over
        # the whole line — so the word "undefined" in a trailing comment
        # suppressed a real finding from the pre-existing quoted rule.
        findings = _scan(tmp_path, "config.py", 'PASSWORD = "s3cretValue"  # undefined behavior')
        assert findings, "a marker word elsewhere on the line disarmed the quoted rule"

    @pytest.mark.parametrize(
        "line",
        [
            "DB_PASSWORD=Falsetto99xyz",  # starts with "false"
            "API_PASSWORD=Nonesuch7781",  # starts with "none"
            "X_PASSWORD=Truebeliever42",  # starts with "true"
            "Y_PASSWORD=Nullifier5566",  # starts with "null"
        ],
    )
    def test_a_value_merely_starting_with_a_literal_is_not_suppressed(self, tmp_path, line):
        # Matched as substrings, "=false"/"=none"/"=true" silenced any credential
        # whose value happened to begin with those letters — in exactly the file
        # type the rule exists to cover. The check is now an exact match against
        # the captured value.
        assert _scan(tmp_path, ".env", line), f"substring bypass: {line}"

    @pytest.mark.parametrize(
        "line",
        ["password=None", "password=null", "password = false", "password: undefined"],
    )
    def test_bare_literals_are_still_not_values(self, tmp_path, line):
        assert not _scan(tmp_path, ".env", line), f"false positive: {line}"


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
