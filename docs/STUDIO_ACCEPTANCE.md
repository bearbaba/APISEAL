# APISEAL — GenLayer Studio acceptance

## Preparation

1. Open https://studio.genlayer.com/ using GenLayer Studionet (chain ID 61999).
2. Deploy contracts/apiseal.py as ApiSeal. Record the actual contract address and deployment transaction.
3. Use examples/api_contracts.json to copy **the contents of the baseline or candidate JSON object serialized as a STRING** into the appropriate specification_json form field. Do not use the outer examples wrapper.
4. Wait for FINALIZED / GenVM SUCCESS, not FINALIZED alone. Independently read get_baseline(id) and get_revision(id) at LATEST_FINAL; record the actual transaction hashes, consensus and stage.

## Scenario 1 — optional field (COMPATIBLE candidate)

Signer A:
- register_baseline(serialized baseline object). Record returned baseline ID.
- propose_revision(baseline_id, serialized compatible_revision object). Record returned revision ID.
- evaluate_revision(revision_id). Expected COMPATIBLE if GenLayer validators agree that the optional field preserves the baseline contract.
- If and only if the observed verdict is COMPATIBLE, authorize_upgrade(revision_id); read back AUTHORIZED and true.
- Try duplicate authorize_upgrade: expected revert.
- revoke_upgrade(revision_id); read back REVOKED and false.

## Scenario 2 — semantic unit shift (BREAKING candidate)

Signer A:
- propose_revision(baseline_id, serialized unit_shift_revision).
- evaluate_revision(id). Expected BREAKING from independent semantic consensus because amount changes from USD cents to whole USD while remaining a number.
- If consensus returns REVIEW_REQUIRED instead, record actual verdict and investigate. Never assert an expected verdict as observed fact.
- authorize_upgrade(id) must reject non-COMPATIBLE decisions.

## Scenario 3 — hard schema incompatibility

Signer A:
- propose_revision(baseline_id, serialized removed_required_field_revision).
- evaluate_revision(id). Expected BREAKING from DETERMINISTIC_STRUCTURAL (no AI override).
- Read stored structural_breaks; authorization must fail.

## Scenario 4 — permissions, invalid inputs, replays

- Wallet B attempts propose_revision against A's baseline: must reject.
- Propose the exact same candidate JSON a second time: must reject duplicate digest.
- Attempt second evaluate_revision on an evaluated record: must reject.
- Submit duplicated operation IDs or fields: must reject at registration/proposal.
- A REVIEW_REQUIRED decision must never authorize.

## Recording results

| Case | Baseline/revision ID | TX hash | GenVM result | Consensus | Readback |
| --- | --- | --- | --- | --- | --- |
| Register baseline | | | | | |
| Optional field evaluation | | | | | |
| Compatible authorization | | | | | |
| Unit shift evaluation | | | | | |
| Structural breaking | | | | | |
| Unauthorized write | | | | | |
| Duplicate / replay | | | | | |

Clearly separate deterministic results from GenLayer consensus. Unit tests are simulated-VM checks, not on-chain evidence. APISEAL reviews frozen input specifications and cannot confirm actual HTTP endpoint behavior.
