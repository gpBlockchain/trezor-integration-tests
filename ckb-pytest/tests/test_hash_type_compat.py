from __future__ import annotations

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.device, pytest.mark.p1]


def test_ckb_tx_030_lock_script_data1_hash_type(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-030", fixture_name="lock-hash-type-data1")
    assert result.tx_hash_matches is True


def test_ckb_tx_031_lock_script_data2_hash_type(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-031", fixture_name="lock-hash-type-data2")

    assert result.tx_hash_matches is True


def test_ckb_tx_032_type_script_data1_or_data2_hash_type(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-032", fixture_name="type-hash-type-data1-data2")

    assert result.tx_hash_matches is True


@pytest.mark.xfail(reason="data3 has no supported final firmware mapping yet.")
@pytest.mark.skip("fixture is not generated yet")
def test_ckb_tx_033_future_data3_fixture_rejected(onchain_compare_case):
    onchain_compare_case("CKB-TX-033", fixture_name="future-data3")


@pytest.mark.skip("fixture is not generated yet")
def test_ckb_tx_034_numeric_hash_type_3_rejected(onchain_compare_case):
    with pytest.raises(RuntimeError):
        onchain_compare_case("CKB-TX-034", fixture_name="numeric-hash-type-3")
