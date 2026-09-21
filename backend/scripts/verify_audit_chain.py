#!/usr/bin/env python3
"""
SIH26100 — Independent Audit Hash-Chain Verifier CLI
Allows an independent auditor or reviewer to verify the cryptographic
integrity of the AuthBid audit trail without trusting the application UI.

Usage:
    python backend/scripts/verify_audit_chain.py [--file path/to/audit_trail.json] [--url http://127.0.0.1:8000/api/verification/audit-trail]
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from typing import List, Dict, Any


def verify_audit_trail(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Independently verify cryptographic SHA-256 hash-chain commitments.
    """
    if not entries:
        return {
            "valid": True,
            "total_blocks": 0,
            "root_hash": "GENESIS",
            "message": "Audit trail is empty.",
        }

    for i, entry in enumerate(entries):
        expected_prev = entries[i - 1]["current_hash"] if i > 0 else "GENESIS"
        actual_prev = entry.get("prev_hash")

        # 1. Verify link to previous block
        if actual_prev != expected_prev:
            return {
                "valid": False,
                "broken_at_index": i,
                "broken_block_id": entry.get("step_id", f"INDEX_{i}"),
                "reason": f"Previous hash mismatch: expected '{expected_prev}', got '{actual_prev}'",
                "total_blocks_checked": i + 1,
            }

        # 2. Recompute current hash
        agent_id = entry.get("agent_id", "")
        action = entry.get("action", "")
        input_hash = entry.get("input_hash", "")
        output_hash = entry.get("output_hash", "")

        content = f"{actual_prev}|{agent_id}|{action}|{input_hash}|{output_hash}"
        recomputed_hash = hashlib.sha256(content.encode()).hexdigest()

        if recomputed_hash != entry.get("current_hash"):
            return {
                "valid": False,
                "broken_at_index": i,
                "broken_block_id": entry.get("step_id", f"INDEX_{i}"),
                "reason": f"Block content tampered: computed '{recomputed_hash}', recorded '{entry.get('current_hash')}'",
                "total_blocks_checked": i + 1,
            }

    return {
        "valid": True,
        "total_blocks": len(entries),
        "genesis_block": entries[0].get("step_id"),
        "root_hash": entries[-1].get("current_hash"),
        "message": "Cryptographic audit trail is fully verified and unbroken.",
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="AuthBid Independent Audit Hash-Chain Verifier")
    parser.add_argument("--file", help="Path to exported audit trail JSON file")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/verification/audit-trail", help="API URL to fetch audit trail from")
    args = parser.parse_args()

    print("=" * 70)
    print(" AuthBid SIH26100 — Independent Audit Trail Verifier")
    print("=" * 70)

    entries = []
    if args.file:
        print(f"[*] Reading audit trail from file: {args.file}")
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
            entries = data.get("data", {}).get("entries", data if isinstance(data, list) else [])
    else:
        print(f"[*] Fetching audit trail from endpoint: {args.url}")
        try:
            req = urllib.request.Request(args.url, headers={"User-Agent": "AuthBid-Auditor-CLI/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                entries = payload.get("data", {}).get("entries", [])
        except Exception as e:
            print(f"[ERROR] Failed to fetch audit trail from {args.url}: {e}")
            sys.exit(1)

    print(f"[*] Loaded {len(entries)} audit blocks. Verifying cryptographic chain...")
    result = verify_audit_trail(entries)

    print("-" * 70)
    if result["valid"]:
        print("[PASSED] AUDIT TRAIL VERIFICATION: PASSED")
        print(f"   Total Blocks Verified : {result['total_blocks']}")
        print(f"   Latest Root Hash      : {result['root_hash']}")
        print(f"   Status                : {result['message']}")
        print("=" * 70)
        sys.exit(0)
    else:
        print("[FAILED] AUDIT TRAIL VERIFICATION: FAILED (TAMPERING DETECTED)")
        print(f"   Broken Block ID       : {result.get('broken_block_id')}")
        print(f"   Broken at Index       : {result.get('broken_at_index')}")
        print(f"   Reason                : {result.get('reason')}")
        print("=" * 70)
        sys.exit(2)


if __name__ == "__main__":
    main()
