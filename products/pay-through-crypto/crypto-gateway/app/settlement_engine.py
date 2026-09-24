"""
Crypto Settlement Engine & Multi-Currency Invoice Manager.
"""

import time
import uuid
from typing import Any, Dict, Optional


EXCHANGE_RATES_USD = {
    "USDT": 1.00,
    "USDC": 1.00,
    "ETH": 3200.00,
    "BTC": 65000.00,
}


class CryptoSettlementEngine:
    def __init__(self, merchant_deposit_address: str = "0x89205A3A3b2A69De6Dbf7f01ED13B2108B2c43e7"):
        self.merchant_deposit_address = merchant_deposit_address
        self._invoices: Dict[str, Dict[str, Any]] = {}

    def create_invoice(self, amount_usd: float, currency: str = "USDT", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        curr = currency.upper()
        if curr not in EXCHANGE_RATES_USD:
            raise ValueError(f"Unsupported cryptocurrency '{currency}'. Supported: {list(EXCHANGE_RATES_USD.keys())}")

        rate = EXCHANGE_RATES_USD[curr]
        crypto_amount = round(amount_usd / rate, 6 if curr in ("ETH", "BTC") else 2)
        invoice_id = f"inv_{uuid.uuid4().hex[:10]}"
        now = int(time.time())

        invoice = {
            "invoice_id": invoice_id,
            "amount_usd": amount_usd,
            "currency": curr,
            "crypto_amount": crypto_amount,
            "deposit_address": self.merchant_deposit_address,
            "status": "PENDING",
            "created_at": now,
            "expires_at": now + 900,  # 15 minutes window
            "metadata": metadata or {},
            "tx_hash": None,
            "confirmations": 0,
        }
        self._invoices[invoice_id] = invoice
        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        return self._invoices.get(invoice_id)

    def mark_settled(self, invoice_id: str, tx_hash: str) -> Dict[str, Any]:
        inv = self._invoices.get(invoice_id)
        if not inv:
            raise KeyError(f"Invoice '{invoice_id}' not found.")
        inv["status"] = "SETTLED"
        inv["tx_hash"] = tx_hash
        inv["confirmations"] = 1
        inv["settled_at"] = int(time.time())
        return inv
