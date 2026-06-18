from __future__ import annotations

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.device, pytest.mark.p1]


def test_ckb_tx_012_output_with_type_script(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-012", fixture_name="output-with-type-script")
    assert result.tx_hash_matches is True


def test_ckb_tx_013_self_send_change_only(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-013", fixture_name="self-send-change-only")

    assert result.tx_hash_matches is True


def test_ckb_tx_014_external_output_plus_change(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-014", fixture_name="external-output-plus-change")

    assert result.tx_hash_matches is True


@pytest.mark.p2
def test_ckb_tx_015_multiple_inputs_same_account(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-015", fixture_name="multiple-inputs-same-account")

    assert result.tx_hash_matches is True


@pytest.mark.p2
def test_ckb_tx_016_multiple_cell_deps_ordered(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-016", fixture_name="multiple-cell-deps-ordered")

    assert result.tx_hash_matches is True


@pytest.mark.p2
def test_ckb_tx_017_output_data_present(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-017", fixture_name="output-data-present")

    assert result.tx_hash_matches is True


def test_ckb_tx_054_top_level_header_dep(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-054", fixture_name="top-level-header-dep")

    assert result.tx_hash_matches is True
    assert result.signature_matches is True


def test_ckb_tx_049_xudt_mint(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-049", fixture_name="xudt-mint")

    assert result.tx_hash_matches is True
    assert result.signature_matches is True


def test_ckb_tx_050_xudt_transfer(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-050", fixture_name="xudt-transfer")

    assert result.tx_hash_matches is True
    assert result.signature_matches is True
