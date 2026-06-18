from __future__ import annotations


def has_explicit_test_nodeid(args: tuple[str, ...] | list[str]) -> bool:
    return any("::" in arg for arg in args)


def has_explicit_test_file(args: tuple[str, ...] | list[str]) -> bool:
    return any("/tests/test_" in arg or arg.startswith("tests/test_") for arg in args)


def has_explicit_tests_directory(args: tuple[str, ...] | list[str]) -> bool:
    return any(arg.endswith("/tests") or arg == "tests" for arg in args)


def has_explicit_test_selection(args: tuple[str, ...] | list[str]) -> bool:
    return (
        has_explicit_test_nodeid(args)
        or has_explicit_test_file(args)
        or has_explicit_tests_directory(args)
    )


def has_explicit_slow_selection(args: tuple[str, ...] | list[str]) -> bool:
    return has_explicit_test_nodeid(args) or has_explicit_test_file(args)


def should_auto_run_device(args: tuple[str, ...] | list[str]) -> bool:
    return has_explicit_test_selection(args)


def should_auto_run_manual_ui(args: tuple[str, ...] | list[str]) -> bool:
    return has_explicit_test_selection(args)


def should_auto_run_onchain(args: tuple[str, ...] | list[str]) -> bool:
    return has_explicit_test_selection(args)


def should_auto_run_slow(args: tuple[str, ...] | list[str]) -> bool:
    return has_explicit_slow_selection(args)


def should_auto_debug_trezorctl(args: tuple[str, ...] | list[str]) -> bool:
    return has_explicit_test_selection(args)
