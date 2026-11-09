# APISEAL

**A GenLayer Intelligent Contract for backward-compatible API upgrade authorization.**

APISEAL binds an API baseline to its owner and a canonical SHA-256 fingerprint, freezes proposed API revisions, and classifies breaking changes before an owner can authorize an upgrade.

## Why it is more than schema validation

Many breaking API changes are structural: removing an operation, changing a route, removing a required response field, changing a field type, or introducing a new required request argument. APISEAL checks these **deterministically**; an LLM cannot override a hard incompatibility.

Other breaks are semantic: an unchanged numeric field may change units from USD cents to USD. When no structural break is found, GenLayer leader and validators independently analyze the **two frozen API contracts** and compare the substance of the COMPATIBLE / BREAKING / REVIEW_REQUIRED classification. The validator reruns the full task; it does not merely validate the response format.

## State machine

1. register_baseline(specification_json): owner locks canonical API contract, version and SHA-256.
2. propose_revision(baseline_id, specification_json): owner freezes a candidate; duplicate candidate digests are refused.
3. evaluate_revision(revision_id): deterministic structural checks or independently validated GenLayer semantic consensus.
4. authorize_upgrade(revision_id): owner-only and only if COMPATIBLE.
5. revoke_upgrade(revision_id): owner-only, once.
6. get_baseline, get_revision and stats: read-only inspection.

Decision scopes: COMPATIBLE can be authorized; BREAKING and REVIEW_REQUIRED cannot. Evaluation and authorization are one-shot. Revisions remain anchored to their original immutable baseline rather than silently replacing its history.

## Input specification

One JSON object with exactly these keys: api, version, operations. Each operation must define id, method, path, success_status, request and response. Fields in request/response must define name, type, required (boolean), meaning (6–180 chars).

See [versioned contract fixtures](examples/api_contracts.json) for complete objects. This deliberately constrained declarative format makes compatibility rules inspectable and limits unbounded AI interpretation.

## Expected cases

| Change | Expected outcome | Decision path |
| --- | --- | --- |
| Optional response memo field added | COMPATIBLE, if consensus agrees | Semantic consensus |
| Required response field removed | BREAKING | Deterministic |
| New required request field | BREAKING | Deterministic |
| Units change from USD cents to whole USD | BREAKING, if consensus agrees | Semantic consensus |
| Insufficiently documented semantic change | REVIEW_REQUIRED, if consensus agrees | Semantic consensus |

The semantic outputs above are illustrative expectations, not observed on-chain results.

## Code and tests

- [Standalone Intelligent Contract](contracts/apiseal.py)
- [12 mocked-VM contract tests](tests/test_apiseal.py), including validator disagreement, roles, duplicates, changes in units, structural breaks, replay and revocation
- [CI](https://github.com/bearbaba/APISEAL/actions/workflows/tests.yml)

Local unit tests: python -m unittest discover -s tests -v

Official lint / schema checks: pip install genvm-linter ; genvm-lint check contracts/apiseal.py

## Limits

APISEAL reviews **caller-supplied specifications**. It does not attest a deployed HTTP API, runtime response data, API provider identity, third-party consumer requirements or external source authenticity. A passed verdict cannot prove that the running system conforms to its specification. Adversarial contract descriptions and semantic ambiguity remain AI-consensus risks.

## Status

Code and offline tests are committed. **No live GenLayer Studio deployment, on-chain verdict or steward acceptance is claimed.** Real wallet transactions and LATEST_FINAL readbacks are required before submitting.

[GenLayer Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)
