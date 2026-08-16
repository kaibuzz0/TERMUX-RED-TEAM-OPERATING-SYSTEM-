"""Compatibility facade for the self-contained offline candidate gate."""

from __future__ import annotations

from release_engine import _candidate_gate_standalone as _gate

CandidateGateError = _gate.CandidateGateError
RC1_RELEASE_ID = _gate.RC1_RELEASE_ID
RC1_SECURITY_SEQUENCE = _gate.RC1_SECURITY_SEQUENCE
EXPECTED_VERSION = _gate.EXPECTED_VERSION
EXPECTED_SECURITY_SEQUENCE = _gate.EXPECTED_SECURITY_SEQUENCE
EXPECTED_PLATFORM = _gate.EXPECTED_PLATFORM
EXPECTED_ARCHITECTURE = _gate.EXPECTED_ARCHITECTURE

# Kept as a facade attribute so tests and callers can replace only the public
# signature verifier without changing the standalone implementation module.
verify_metadata = _gate.verify_metadata


def verify_candidate_hashes(candidate_dir):
    return _gate.verify_candidate_hashes(candidate_dir)


def validate_signed_metadata(candidate, unsigned_metadata, signed_metadata):
    _gate.verify_metadata = verify_metadata
    return _gate.validate_signed_metadata(candidate, unsigned_metadata, signed_metadata)


def seal_release_bundle(bundle_path, signed_metadata, output_path):
    return _gate.seal_release_bundle(bundle_path, signed_metadata, output_path)


def gate_candidate(candidate_dir, signed_metadata_path, output_dir):
    _gate.verify_metadata = verify_metadata
    return _gate.gate_candidate(candidate_dir, signed_metadata_path, output_dir)


def main(argv=None):
    return _gate.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
