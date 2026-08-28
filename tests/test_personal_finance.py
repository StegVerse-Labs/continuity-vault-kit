import unittest

from runtime.personal_finance import (
    PersonalFinanceError,
    assert_read_only_finance_contract,
    deterministic_id,
    normalize_snapshot,
)


class PersonalFinanceTests(unittest.TestCase):
    def test_empty_snapshot_normalizes(self):
        snapshot = normalize_snapshot({})
        self.assertEqual(snapshot["schema_version"], "stegverse.kv.personal-finance/v1")
        self.assertFalse(snapshot["execution_authority"])
        self.assertEqual(len(snapshot["snapshot_hash"]), 64)

    def test_account_id_is_deterministic(self):
        payload = {
            "accounts": [{
                "display_name": "Synthetic Checking",
                "type": "depository",
                "mask": "1234",
                "balances": {
                    "current": 1000.0,
                    "available": 900.0,
                    "limit": None,
                    "currency": "USD",
                    "as_of": "2026-08-28T12:00:00Z"
                },
                "source": {
                    "kind": "provider_import",
                    "provider_name": "Example Bank",
                    "external_reference": "synthetic-account-ref",
                    "connection_state": "CONNECTED_READ_ONLY"
                }
            }]
        }
        a = normalize_snapshot(payload)
        b = normalize_snapshot(payload)
        self.assertEqual(a["accounts"][0]["account_id"], b["accounts"][0]["account_id"])
        self.assertTrue(a["accounts"][0]["account_id"].startswith("kvfin_acct_"))

    def test_secret_fields_fail_closed(self):
        with self.assertRaises(PersonalFinanceError):
            normalize_snapshot({
                "accounts": [],
                "provider_access_token": "must-not-enter-kv"
            })

    def test_full_account_numbers_fail_closed(self):
        with self.assertRaises(PersonalFinanceError):
            normalize_snapshot({
                "accounts": [{
                    "display_name": "Synthetic",
                    "type": "depository",
                    "account_number": "1234567890"
                }]
            })

    def test_execution_authority_cannot_be_granted(self):
        with self.assertRaises(PersonalFinanceError):
            normalize_snapshot({"execution_authority": True})

    def test_reward_and_collateral_shapes_remain_read_only(self):
        collateral_account = deterministic_id("acct", "Example Crypto", "usdc")
        secured_account = deterministic_id("acct", "Example Card", "secured")
        snapshot = normalize_snapshot({
            "accounts": [],
            "rewards": [{
                "reward_id": deterministic_id("reward", "usdc-apy"),
                "kind": "apy",
                "source_account_id": collateral_account,
                "asset": "USDC",
                "rate_percent": 6.5,
                "earning_balance": {"amount": 1000.0, "currency": "USD"},
                "earned_value": None,
                "as_of": "2026-08-28T12:00:00Z",
                "notes": "synthetic fixture"
            }],
            "collateral_relationships": [{
                "relationship_id": deterministic_id("collateral", "usdc", "secured-card"),
                "collateral_account_id": collateral_account,
                "secured_account_id": secured_account,
                "asset": "USDC",
                "locked_amount": {"amount": 1000.0, "currency": "USD"},
                "purpose": "synthetic secured-card collateral",
                "as_of": "2026-08-28T12:00:00Z"
            }]
        })
        assert_read_only_finance_contract(snapshot)
        self.assertFalse(snapshot["execution_authority"])


if __name__ == "__main__":
    unittest.main()
