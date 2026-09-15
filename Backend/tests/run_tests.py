#!/usr/bin/env python3
"""
Test Runner for Project Template Backend API

Usage:
    python tests/run_tests.py                   # Run all tests
    python tests/run_tests.py chatbot           # Run chatbot tests only
    python tests/run_tests.py auth              # Run auth tests only
    python tests/run_tests.py --refresh-tokens  # Refresh managed test JWTs
    python tests/run_tests.py --verbose         # Verbose output
    python tests/run_tests.py --fail-fast       # Stop on first failure
    python tests/run_tests.py --markers         # List all markers
    python tests/run_tests.py --token "eyJ..."  # Set JWT token for all users
"""

import sys
import os
import argparse
from pathlib import Path
import pytest
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.config.test_config import config as test_config
from tests.helpers.auth_helper import PERSISTENT_USERS_FILE, refresh_configured_test_tokens


RUNTIME_LOG_ANCHOR_LINES = 20


def print_banner():
    print("""
========================================================================
           Project Template Backend — API Test Suite
                    Powered by pytest
========================================================================
""")


def use_provided_token(config_file: Path, token: str, user_type: str = 'all') -> bool:
    if not token or len(token) < 20:
        print("  Invalid token format")
        return False

    if not config_file.exists():
        print(f"  Config file not found: {config_file}")
        return False

    with open(config_file, 'r') as f:
        config = json.load(f)

    backup_file = config_file.with_suffix('.json.backup')
    with open(backup_file, 'w') as f:
        json.dump(config, f, indent=2)

    if user_type == 'all':
        for user_key in config['users'].keys():
            config['users'][user_key]['token'] = token
            print(f"  Updated {user_key} user token")
    elif user_type in config['users']:
        config['users'][user_type]['token'] = token
        print(f"  Updated {user_type} user token")
    else:
        print(f"  Unknown user type: {user_type}")
        return False

    config['lastUpdated'] = datetime.now(timezone.utc).isoformat()
    config['setupComplete'] = True
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"  Token set successfully (backup: {backup_file.name})")
    return True


def list_markers():
    print("\nAvailable Test Markers:")
    markers = {
        "health": "Root / health-check endpoint tests",
        "auth": "Authentication and token verification tests",
        "chatbot": "Chatbot response and chat history tests",
        "ticket": "Support ticket CRUD tests",
        "stats": "Conversation statistics tests",
        "ingestion": "Data scraping, embedding and search tests",
        "web_extract": "Local HTML, Amazon catalog, and Playwright page extraction tests",
        "slow": "Slow-running tests (>5 seconds)",
        "smoke": "Quick smoke tests for CI/CD",
        "integration": "Full integration tests",
        "external": "Tests requiring external services (Gemini, Pinecone, etc.)",
    }
    for marker, description in markers.items():
        print(f"  {marker:15} - {description}")

    print("\nUsage:")
    print('  pytest -m chatbot              # Run only chatbot tests')
    print('  pytest -m auth                 # Run only auth tests')
    print('  pytest -m "not external"       # Skip external service tests')
    print('  pytest -m "not slow"           # Skip slow tests')


def refresh_tokens_for_tests(user_type: str = 'all') -> None:
    target_users = None if user_type == 'all' else [user_type]
    refreshed = refresh_configured_test_tokens(target_users)
    for refreshed_user, token in refreshed.items():
        print(f"  Refreshed token for {refreshed_user} ({len(token)} chars)")


@dataclass(frozen=True)
class RuntimeLogSnapshot:
    path: Path
    line_count: int
    tail: tuple[str, ...]


def _resolve_runtime_log_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    return Path(raw_path).expanduser()


def _snapshot_runtime_log(path: Path | None) -> RuntimeLogSnapshot | None:
    if path is None:
        return None
    if not path.exists():
        print(f"  Runtime log file not found: {path}")
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        print(f"  Could not read runtime log file {path}: {exc}")
        return None
    return RuntimeLogSnapshot(
        path=path,
        line_count=len(lines),
        tail=tuple(lines[-RUNTIME_LOG_ANCHOR_LINES:]),
    )


def _find_new_runtime_lines(lines: list[str], snapshot: RuntimeLogSnapshot) -> list[str]:
    if snapshot.tail:
        anchor_len = len(snapshot.tail)
        for index in range(len(lines) - anchor_len, -1, -1):
            if tuple(lines[index : index + anchor_len]) == snapshot.tail:
                return lines[index + anchor_len :]
    if len(lines) >= snapshot.line_count:
        return lines[snapshot.line_count :]
    return lines


def _parse_allowed_statuses(raw_values: list[str] | None) -> set[str]:
    allowed: set[str] = set()
    for raw in raw_values or []:
        for item in raw.split(","):
            value = item.strip()
            if re.fullmatch(r"\d{3}", value):
                allowed.add(value)
    return allowed


def _print_runtime_log_delta(
    snapshot: RuntimeLogSnapshot | None,
    route_filter: str | None,
    allowed_statuses: set[str] | None = None,
    unexpected_only: bool = False,
    max_lines: int = 12,
) -> bool:
    if snapshot is None:
        return False

    try:
        lines = snapshot.path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        print(f"\n  Could not read runtime log delta from {snapshot.path}: {exc}")
        return False

    new_lines = _find_new_runtime_lines(lines, snapshot)
    if route_filter:
        new_lines = [line for line in new_lines if route_filter in line]

    if not new_lines:
        print("\n  Runtime log delta: no matching new lines")
        return False

    status_counts: Counter[str] = Counter()
    allowed_counts: Counter[str] = Counter()
    unexpected_counts: Counter[str] = Counter()
    allowed = allowed_statuses or set()
    unexpected_lines: list[str] = []

    for line in new_lines:
        match = re.search(r'HTTP/1\.1"\s+(\d{3})\b', line)
        if match:
            status = match.group(1)
            status_counts[status] += 1
            if allowed and status in allowed:
                allowed_counts[status] += 1
            elif allowed:
                unexpected_counts[status] += 1
                unexpected_lines.append(line)

    print("\n  Runtime log delta:")
    print(f"    file: {snapshot.path}")
    if route_filter:
        print(f"    filter: {route_filter}")
    if status_counts:
        counts = ", ".join(f"{code} x{count}" for code, count in sorted(status_counts.items()))
        print(f"    statuses: {counts}")
    if allowed:
        expected_counts = ", ".join(f"{code} x{count}" for code, count in sorted(allowed_counts.items())) or "none"
        unexpected_counts_text = (
            ", ".join(f"{code} x{count}" for code, count in sorted(unexpected_counts.items())) or "none"
        )
        print(f"    expected statuses: {expected_counts}")
        print(f"    unexpected statuses: {unexpected_counts_text}")

    lines_to_print = unexpected_lines if (unexpected_only and unexpected_lines) else new_lines
    for line in lines_to_print[-max_lines:]:
        print(f"    {line}")
    return bool(unexpected_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Project Template Backend API Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_tests.py                     # Run all tests
  python tests/run_tests.py --token "eyJ..."    # Set token, then run
  python tests/run_tests.py chatbot             # Run chatbot tests only
  python tests/run_tests.py auth --verbose      # Verbose auth tests
  python tests/run_tests.py --fail-fast         # Stop on first failure
        """
    )
    parser.add_argument('pattern', nargs='?', default=None,
                        help='Test pattern or marker (e.g., chatbot, auth, ticket)')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-x', '--fail-fast', action='store_true')
    parser.add_argument('-s', '--capture', action='store_true', help='Show print statements')
    parser.add_argument('-m', '--markers', action='store_true', help='List markers')
    parser.add_argument('--token', type=str, help='JWT token to use for all test users')
    parser.add_argument('--token-user', choices=['primary', 'secondary', 'all'],
                        default='all', help='Which user to update with token (default: all)')
    parser.add_argument('--refresh-tokens', action='store_true',
                        help='Fetch fresh test JWTs via the internal shared-secret endpoint')
    parser.add_argument('--server-log', type=str,
                        help='Path to a backend runtime log file to mirror after tests')
    parser.add_argument('--log-filter', type=str,
                        help='Only show new runtime log lines containing this text')
    parser.add_argument('--allow-status', action='append',
                        help='HTTP status code to treat as expected in mirrored runtime logs (repeatable or comma-separated)')
    parser.add_argument('--unexpected-only', action='store_true',
                        help='When mirrored logs exist, print only unexpected status lines if any are found')
    parser.add_argument('--fail-on-unexpected-log-status', action='store_true',
                        help='Fail the run if mirrored runtime logs contain a status outside --allow-status')

    args = parser.parse_args()
    print_banner()

    if args.markers:
        list_markers()
        return 0

    config_file = PERSISTENT_USERS_FILE

    if args.token:
        success = use_provided_token(config_file, args.token, args.token_user)
        if not success:
            print("\n  Failed to set provided token\n")
            return 1
    elif args.refresh_tokens or test_config.can_auto_refresh_tokens():
        try:
            refresh_tokens_for_tests(args.token_user)
        except Exception as exc:
            if args.refresh_tokens:
                print(f"\n  Failed to refresh tokens: {exc}\n")
                return 1
            print(f"  Token auto-refresh unavailable: {exc}")

    pytest_args = ['tests/usecases']

    if args.verbose:
        pytest_args.append('-v')
    else:
        pytest_args.append('-q')

    if args.fail_fast:
        pytest_args.append('-x')

    if args.capture:
        pytest_args.append('-s')

    if args.pattern:
        pytest_args.extend(['-k', args.pattern])
        print(f"  Running tests matching: {args.pattern}")
    else:
        print("  Running all tests")

    print(f"  pytest command: pytest {' '.join(pytest_args)}\n")

    runtime_log_path = _resolve_runtime_log_path(
        args.server_log or os.getenv("TEST_RUNTIME_LOG_PATH")
    )
    runtime_log_filter = args.log_filter or os.getenv("TEST_RUNTIME_LOG_FILTER")
    if runtime_log_filter is None and args.pattern == "web_extract":
        runtime_log_filter = "/web-extract/extract-page"
    allowed_statuses = _parse_allowed_statuses(
        args.allow_status or ([os.getenv("TEST_RUNTIME_LOG_ALLOWED_STATUSES")] if os.getenv("TEST_RUNTIME_LOG_ALLOWED_STATUSES") else None)
    )
    if not allowed_statuses and args.pattern == "web_extract" and runtime_log_filter == "/web-extract/extract-page":
        allowed_statuses = {"422"}
    runtime_log_snapshot = _snapshot_runtime_log(runtime_log_path)

    exit_code = pytest.main(pytest_args)

    unexpected_log_status = _print_runtime_log_delta(
        runtime_log_snapshot,
        runtime_log_filter,
        allowed_statuses=allowed_statuses,
        unexpected_only=args.unexpected_only,
    )
    if exit_code == 0 and unexpected_log_status and args.fail_on_unexpected_log_status:
        print("\n  Unexpected runtime log statuses detected")
        exit_code = 1

    if exit_code == 0:
        print("\n  All tests passed!")
    else:
        print("\n  Some tests failed")

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Test execution interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n  Fatal error: {e}")
        sys.exit(1)
