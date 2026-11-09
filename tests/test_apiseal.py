"""Offline APISEAL contract logic tests. GenLayer Studio evidence is separate."""
import copy
import importlib.util
import json
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OWNER = "0x" + "11" * 20
INTRUDER = "0x" + "22" * 20


class VM:
    class UserError(Exception):
        pass

    class Return:
        def __init__(self, calldata):
            self.calldata = calldata

    def run_nondet_unsafe(self, leader, validator):
        result = leader()
        if not validator(self.Return(result)):
            raise self.UserError("independent validator rejected leader decision")
        return result


class TreeMap(dict):
    @classmethod
    def __class_getitem__(cls, _):
        return cls


class Public:
    @staticmethod
    def write(fn):
        return fn

    @staticmethod
    def view(fn):
        return fn


class Harness:
    def __init__(self):
        self.answers = []
        self.gl = types.SimpleNamespace(
            Contract=object, public=Public(), vm=VM(),
            message=types.SimpleNamespace(
                sender_address=types.SimpleNamespace(as_hex=OWNER)),
            nondet=types.SimpleNamespace(exec_prompt=self.prompt))
        fake = types.ModuleType("genlayer")
        fake.gl = self.gl
        fake.TreeMap = TreeMap
        fake.u256 = int
        sys.modules["genlayer"] = fake
        spec = importlib.util.spec_from_file_location("apiseal_under_test",
                    ROOT / "contracts" / "apiseal.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.mod = mod
        self.seal = mod.ApiSeal()
        self.seal.baselines = TreeMap()
        self.seal.revisions = TreeMap()
        self.seal.revision_keys = TreeMap()
        self.before = {
            "api": "Payments", "version": "1.0",
            "operations": [{
                "id": "get_balance", "method": "GET", "path": "/balance",
                "success_status": 200,
                "request": [],
                "response": [{
                    "name": "amount", "type": "number", "required": True,
                    "meaning": "Account balance expressed in USD cents"
                }]
            }]
        }
        self.baseline_id = self.seal.register_baseline(json.dumps(self.before))

    def prompt(self, _):
        return self.answers.pop(0)

    def actor(self, address):
        self.gl.message.sender_address.as_hex = address

    def candidate(self):
        out = copy.deepcopy(self.before)
        out["version"] = "2.0"
        return out

    def propose(self, candidate):
        return self.seal.propose_revision(self.baseline_id, json.dumps(candidate))


class ApiSealTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def test_optional_response_extension_can_pass_consensus(self):
        newer = self.h.candidate()
        newer["operations"][0]["response"].append({
            "name": "memo", "type": "string", "required": False,
            "meaning": "Optional balance display memo"
        })
        self.h.answers = ["COMPATIBLE", "COMPATIBLE"]
        rid = self.h.propose(newer)
        self.assertEqual(self.h.seal.evaluate_revision(rid), "COMPATIBLE")
        self.h.seal.authorize_upgrade(rid)
        self.assertTrue(json.loads(self.h.seal.get_revision(rid))["authorized"])

    def test_semantic_unit_change_is_decided_by_consensus(self):
        newer = self.h.candidate()
        newer["operations"][0]["response"][0]["meaning"] = (
            "Account balance expressed in whole USD, not cents"
        )
        self.h.answers = ["BREAKING", "BREAKING"]
        rid = self.h.propose(newer)
        self.assertEqual(self.h.seal.evaluate_revision(rid), "BREAKING")
        record = json.loads(self.h.seal.get_revision(rid))
        self.assertEqual(record["method"], "GENLAYER_SEMANTIC_CONSENSUS")
        with self.assertRaises(VM.UserError):
            self.h.seal.authorize_upgrade(rid)

    def test_semantic_validator_must_independently_agree(self):
        newer = self.h.candidate()
        newer["operations"][0]["response"][0]["meaning"] = (
            "Balance amount in an undocumented numeric unit"
        )
        self.h.answers = ["COMPATIBLE", "BREAKING"]
        rid = self.h.propose(newer)
        with self.assertRaises(VM.UserError):
            self.h.seal.evaluate_revision(rid)
        self.assertEqual(json.loads(self.h.seal.get_revision(rid))["stage"],
                         "PROPOSED")

    def test_required_response_removal_is_mechanically_breaking(self):
        newer = self.h.candidate()
        newer["operations"][0]["response"] = []
        rid = self.h.propose(newer)
        self.assertEqual(self.h.seal.evaluate_revision(rid), "BREAKING")
        record = json.loads(self.h.seal.get_revision(rid))
        self.assertEqual(record["method"], "DETERMINISTIC_STRUCTURAL")
        self.assertIn("get_balance:required_response_removed:amount",
                      record["structural_breaks"])

    def test_new_required_request_is_breaking(self):
        newer = self.h.candidate()
        newer["operations"][0]["request"] = [{
            "name": "token", "type": "string", "required": True,
            "meaning": "Mandatory new access token"
        }]
        rid = self.h.propose(newer)
        self.assertEqual(self.h.seal.evaluate_revision(rid), "BREAKING")

    def test_route_change_is_breaking(self):
        newer = self.h.candidate()
        newer["operations"][0]["path"] = "/balance/v2"
        rid = self.h.propose(newer)
        self.assertEqual(self.h.seal.evaluate_revision(rid), "BREAKING")

    def test_unknown_semantics_requires_review_not_authorization(self):
        newer = self.h.candidate()
        newer["operations"][0]["response"][0]["meaning"] = (
            "Numeric balance without declared unit or rounding policy"
        )
        self.h.answers = ["REVIEW_REQUIRED", "REVIEW_REQUIRED"]
        rid = self.h.propose(newer)
        self.assertEqual(self.h.seal.evaluate_revision(rid), "REVIEW_REQUIRED")
        with self.assertRaises(VM.UserError):
            self.h.seal.authorize_upgrade(rid)

    def test_only_owner_may_propose_or_authorize(self):
        newer = self.h.candidate()
        self.h.actor(INTRUDER)
        with self.assertRaises(VM.UserError):
            self.h.propose(newer)
        self.h.actor(OWNER)
        rid = self.h.propose(newer)
        self.h.answers = ["COMPATIBLE", "COMPATIBLE"]
        self.h.seal.evaluate_revision(rid)
        self.h.actor(INTRUDER)
        with self.assertRaises(VM.UserError):
            self.h.seal.authorize_upgrade(rid)

    def test_duplicate_revision_is_blocked(self):
        newer = self.h.candidate()
        self.h.propose(newer)
        with self.assertRaises(VM.UserError):
            self.h.propose(newer)

    def test_duplicate_operation_is_invalid(self):
        newer = self.h.candidate()
        newer["operations"].append(copy.deepcopy(newer["operations"][0]))
        with self.assertRaises(VM.UserError):
            self.h.propose(newer)

    def test_authorized_revision_can_be_revoked_once(self):
        newer = self.h.candidate()
        rid = self.h.propose(newer)
        self.h.answers = ["COMPATIBLE", "COMPATIBLE"]
        self.h.seal.evaluate_revision(rid)
        self.h.seal.authorize_upgrade(rid)
        self.h.seal.revoke_upgrade(rid)
        record = json.loads(self.h.seal.get_revision(rid))
        self.assertFalse(record["authorized"])
        self.assertEqual(record["stage"], "REVOKED")
        with self.assertRaises(VM.UserError):
            self.h.seal.revoke_upgrade(rid)

    def test_no_re_evaluation(self):
        newer = self.h.candidate()
        rid = self.h.propose(newer)
        self.h.answers = ["COMPATIBLE", "COMPATIBLE"]
        self.h.seal.evaluate_revision(rid)
        with self.assertRaises(VM.UserError):
            self.h.seal.evaluate_revision(rid)


if __name__ == "__main__":
    unittest.main()
