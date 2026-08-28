import unittest

from runtime.coinbase_finance_ingress import (
    CoinbaseFinanceIngressError,
    normalize_coinbase_finance_result,
)
from runtime.personal_finance import reject_secret_fields


class CoinbaseFinanceIngressTests(unittest.TestCase):
    def synthetic_result(self):
        return {
            "provider": "coinbase",
            "direct_source_verified": True,
            "session_verified": True,
            "access": "READ_ONLY",
            "provider_operation_authorized": False,
            "retrieved_at": "2026-08-28T16:00:00Z",
            "coverage_start": "2026-08-01T00:00:00Z",
            "coverage_end": "2026-08-28T16:00:00Z",
            "adapter_version": "synthetic-v1",
            "session_evidence_ref": "receipt:synthetic-session",
            "accounts": [
                {
                    "source_ref": "coinbase-usdc-wallet",
                    "display_name": "USDC",
                    "account_type": "crypto",
                    "asset": "USDC",
                    "currency": "USD",
                    "current_balance": 1000.0,
                    "available_balance": 0.0,
                    "as_of": "2026-08-28T16:00:00Z",
                },
                {
                    "source_ref": "coinbase-secured-card",
                    "display_name": "Coinbase Secured Card",
                    "account_type": "credit",
                    "subtype": "secured_card",
                    "mask": "1234",
                    "current_balance": 75.0,
                    "credit_limit": 1000.0,
                    "currency": "USD",
                },
            ],
            "transactions": [
                {
                    "source_ref": "txn-1",
                    "posted_at": "2026-08-27T12:00:00Z",
                    "description": "Synthetic purchase",
                    "amount": -25.0,
                    "currency": "USD",
                    "category": "purchase",
                    "pending": False,
                }
            ],
            "rewards": [
                {
                    "source_ref": "usdc-reward-program",
                    "reward_type": "apy",
                    "asset": "USDC",
                    "rate": 6.5,
                    "rate_unit": "PERCENT_APY",
                    "earned_amount": 10.0,
                    "earned_asset": "USDC",
                },
                {
                    "source_ref": "btc-card-reward",
                    "reward_type": "crypto_back",
                    "asset": "BTC",
                    "rate": 1.0,
                    "rate_unit": "PERCENT",
                },
            ],
            "collateral": [
                {
                    "source_ref": "secured-card-usdc-collateral",
                    "asset": "USDC",
                    "locked_amount": 1000.0,
                    "purpose": "SECURED_CARD_COLLATERAL",
                }
            ],
        }

    def test_synthetic_result_normalizes(self):
        snapshot = normalize_coinbase_finance_result(self.synthetic_result())
        self.assertEqual(snapshot["schema_version"], "stegverse.kv.personal-finance/v1")
        self.assertFalse(snapshot["execution_authority"])
        self.assertEqual(len(snapshot["accounts"]), 2)
        self.assertEqual(len(snapshot["rewards"]), 2)
        self.assertEqual(snapshot["collateral_relationships"][0]["locked_amount"], 1000.0)
        self.assertTrue(snapshot["snapshot_hash"])

    def test_direct_source_required(self):
        result = self.synthetic_result()
        result["direct_source_verified"] = False
        with self.assertRaises(CoinbaseFinanceIngressError):
            normalize_coinbase_finance_result(result)

    def test_session_required(self):
        result = self.synthetic_result()
        result["session_verified"] = False
        with self.assertRaises(CoinbaseFinanceIngressError):
            normalize_coinbase_finance_result(result)

    def test_provider_operation_authority_rejected(self):
        result = self.synthetic_result()
        result["provider_operation_authorized"] = True
        with self.assertRaises(CoinbaseFinanceIngressError):
            normalize_coinbase_finance_result(result)

    def test_secret_field_rejected(self):
        result = self.synthetic_result()
        result["access_token"] = "synthetic-secret"
        with self.assertRaises(Exception):
            normalize_coinbase_finance_result(result)

    def test_spending_field_name_does_not_trip_pin_fragment(self):
        reject_secret_fields({"spending_category": "food"})

    def test_actual_pin_field_remains_rejected(self):
        with self.assertRaises(Exception):
            reject_secret_fields({"pin": "0000"})


if __name__ == "__main__":
    unittest.main()
