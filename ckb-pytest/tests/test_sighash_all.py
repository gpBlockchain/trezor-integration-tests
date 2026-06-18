from __future__ import annotations

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.device, pytest.mark.p1]


@pytest.mark.p0
def test_ckb_tx_036_one_input_default_witness_placeholder(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-036", fixture_name="one-input-default-witness")
    assert result.tx_hash_matches is True


def test_ckb_tx_037_two_inputs_same_default_lock_group(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-037", fixture_name="two-inputs-same-lock-group")

    assert result.tx_hash_matches is True


def test_ckb_tx_038_trailing_witness(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-038", fixture_name="trailing-witness")
    assert result.tx_hash_matches is True


def test_ckb_tx_039_first_group_witness_input_type(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-039", fixture_name="first-group-input-type")
    assert result.tx_hash_matches is True


def test_ckb_tx_040_first_group_witness_output_type(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-040", fixture_name="first-group-output-type")
    assert result.tx_hash_matches is True


def test_ckb_tx_041_mixed_lock_script_groups_primary_group(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-041", fixture_name="mixed-lock-groups-primary")

    assert result.tx_hash_matches is True


def test_ckb_tx_045_mixed_lock_script_groups_secondary_group(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-045", fixture_name="mixed-lock-groups-secondary")

    assert result.tx_hash_matches is True


def test_ckb_tx_046_mixed_lock_groups_input_output_type_primary_group(onchain_compare_case):
    result = onchain_compare_case(
        "CKB-TX-046",
        fixture_name="mixed-lock-groups-input-output-type-primary",
    )

    assert result.tx_hash_matches is True


def test_ckb_tx_047_mixed_lock_groups_input_output_type_secondary_group(onchain_compare_case):
    result = onchain_compare_case(
        "CKB-TX-047",
        fixture_name="mixed-lock-groups-input-output-type-secondary",
    )

    assert result.tx_hash_matches is True


def test_ckb_tx_048_witness_args_and_random_raw_witnesses(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-048", fixture_name="witness-args-and-random-raw")
    assert result.tx_hash_matches is True


def test_ckb_tx_042_same_lock_group_other_input_non_empty_witness(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-042", fixture_name="same-lock-group-non-empty-witness")
    assert result.tx_hash_matches is True


@pytest.mark.xfail(reason="Input ownership metadata is currently validated host-side, not by device.")
@pytest.mark.skip("fixture is not generated yet")
def test_ckb_tx_043_input_previous_lock_not_current_key_rejected(onchain_compare_case):
    onchain_compare_case("CKB-TX-043", fixture_name="input-lock-not-current-key")


def test_ckb_tx_044_first_group_witness_input_output_type(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-044", fixture_name="first-group-input-output-type")
    assert result.tx_hash_matches is True
