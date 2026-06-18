from __future__ import annotations


DEFAULT_PATH = "m/44'/309'/0'/0/0"
DEFAULT_TESTNET_ADDRESS = (
    "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xws"
    "qwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed"
)
DEFAULT_RPC_URLS = {
    "Testnet": "https://testnet.ckb.dev",
    "Mainnet": "https://mainnet.ckb.dev",
}

HASH_TYPE_TO_INT = {"data": 0, "type": 1, "data1": 2, "data2": 4}
INT_TO_HASH_TYPE = {value: key for key, value in HASH_TYPE_TO_INT.items()}
DEP_TYPE_TO_INT = {"code": 0, "dep_group": 1}
INT_TO_DEP_TYPE = {value: key for key, value in DEP_TYPE_TO_INT.items()}

