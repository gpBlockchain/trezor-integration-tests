from __future__ import annotations

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.device, pytest.mark.slow]


@pytest.mark.p1
# @pytest.mark.skip("large transaction fixture is kept for manual boundary testing; skip in full regression")
def test_ckb_tx_018_50_inputs_1_output(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-018", fixture_name="50-inputs-1-output")

    assert result.tx_hash_matches is True


@pytest.mark.p1
@pytest.mark.skip("large transaction fixture is kept for manual boundary testing; skip in full regression")
def test_ckb_tx_019_1_input_50_outputs(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-019", fixture_name="1-input-50-outputs")

    assert result.tx_hash_matches is True


@pytest.mark.p1
@pytest.mark.skip("large transaction fixture is kept for manual boundary testing; skip in full regression")
def test_ckb_tx_020_50_inputs_50_outputs(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-020", fixture_name="50-inputs-50-outputs")

    assert result.tx_hash_matches is True


@pytest.mark.skip("Data must be bytes and less or equal 65535 bytes in length")
@pytest.mark.p1
def test_ckb_tx_021_100kb_output_data(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-021", fixture_name="100kb-output-data")

    assert result.tx_hash_matches is True


@pytest.mark.p1
@pytest.mark.skip("requires special fixture with 100 unique live cell_deps")
def test_ckb_tx_022_100_cell_deps(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-022", fixture_name="100-cell-deps")

    assert result.tx_hash_matches is True


@pytest.mark.p1
def test_ckb_tx_023_long_lock_args_chunkify(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-023", fixture_name="long-lock-args-chunkify")

    assert result.tx_hash_matches is True


@pytest.mark.p1
def test_ckb_tx_024_long_type_args(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-024", fixture_name="long-type-args")

    assert result.tx_hash_matches is True


@pytest.mark.p1
@pytest.mark.skip("local JSON boundary: max uint32 output index is not a normal on-chain fixture")
def test_ckb_tx_025_max_uint32_output_index(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-025", fixture_name="max-uint32-output-index")

    assert result.tx_hash_matches is True


@pytest.mark.p1
@pytest.mark.skip("local/special boundary: max uint64 since must define expected rejection semantics")
def test_ckb_tx_026_max_uint64_since(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-026", fixture_name="max-uint64-since")

    assert result.tx_hash_matches is True


@pytest.mark.p1
@pytest.mark.skip("local/special boundary: very large capacity/fee is not practical for default Testnet fixture generation")
def test_ckb_tx_027_large_capacity_and_fee(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-027", fixture_name="large-capacity-and-fee")

    assert result.tx_hash_matches is True


@pytest.mark.p2
@pytest.mark.skip("large transaction fixture is kept for manual boundary testing; skip in full regression")
def test_ckb_tx_028_100_inputs_100_outputs(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-028", fixture_name="100-inputs-100-outputs")

    assert result.tx_hash_matches is True


@pytest.mark.p2
@pytest.mark.skip("requires a dedicated near node-size-limit fixture and is excluded from default regression")
def test_ckb_tx_029_near_host_node_size_limit(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-029", fixture_name="near-host-node-size-limit")
    assert result.tx_hash_matches is True
