from orchestrator.controlled_self_healer import extract_patch_payload, validate_patch


VALID_TEST_PATCH = """diff --git a/tests/test_patch_target.py b/tests/test_patch_target.py
--- a/tests/test_patch_target.py
+++ b/tests/test_patch_target.py
@@ -1 +1 @@
-assert False
+assert True
"""


def test_extracts_explicit_fenced_unified_diff():
    fence = chr(96) * 3
    response = "Here is the requested patch:\n" + fence + "diff\n" + VALID_TEST_PATCH + fence
    extracted = extract_patch_payload(response)
    assert extracted == VALID_TEST_PATCH.strip()
    valid, reason, paths = validate_patch(extracted)
    assert valid, reason
    assert "tests/test_patch_target.py" in paths


def test_extracts_json_patch_envelope_without_relaxing_validation():
    import json
    response = json.dumps({"patch": VALID_TEST_PATCH})
    extracted = extract_patch_payload(response)
    assert extracted == VALID_TEST_PATCH.strip()
    assert validate_patch(extracted)[0] is True


def test_does_not_turn_prose_or_source_code_into_a_patch():
    response = "I would change the test to assert true, but I cannot generate a diff."
    extracted = extract_patch_payload(response)
    assert extracted == response
    valid, reason, _ = validate_patch(extracted)
    assert valid is False
    assert "unified diff" in reason


def test_json_evidence_without_patch_field_is_not_accepted_as_a_patch():
    response = '{"summary": "repair complete", "tests_passed": true}'
    extracted = extract_patch_payload(response)
    assert extracted == response
    assert validate_patch(extracted)[0] is False
