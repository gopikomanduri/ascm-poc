import time
from typing import Dict, Any


class TokenEscrowManager:
    """
    Manages tenant API token balance, credit escrow, and sliding-window rate limits.
    """

    def __init__(self, default_credit_balance: int = 50000):
        self.default_balance = default_credit_balance
        self.balances: Dict[str, int] = {}
        self.request_timestamps: Dict[str, list] = {}

    def get_balance(self, tenant_id: str) -> int:
        return self.balances.setdefault(tenant_id, self.default_balance)

    def credit_tokens(self, tenant_id: str, amount: int) -> int:
        cur = self.get_balance(tenant_id)
        new_bal = cur + amount
        self.balances[tenant_id] = new_bal
        return new_bal

    def check_and_consume_tokens(self, tenant_id: str, tokens_needed: int, max_rpm: int = 60) -> Dict[str, Any]:
        now = time.time()
        # Rate limit sliding window (1 minute)
        reqs = self.request_timestamps.setdefault(tenant_id, [])
        reqs = [t for t in reqs if now - t < 60]
        self.request_timestamps[tenant_id] = reqs

        if len(reqs) >= max_rpm:
            return {
                "allowed": False,
                "reason": "RATE_LIMIT_EXCEEDED",
                "message": f"Tenant exceeded {max_rpm} requests per minute limit.",
                "remaining_balance": self.get_balance(tenant_id),
            }

        cur_bal = self.get_balance(tenant_id)
        if cur_bal < tokens_needed:
            return {
                "allowed": False,
                "reason": "INSUFFICIENT_CREDITS",
                "message": f"Required {tokens_needed} tokens, but balance is only {cur_bal}.",
                "remaining_balance": cur_bal,
            }

        new_bal = cur_bal - tokens_needed
        self.balances[tenant_id] = new_bal
        reqs.append(now)

        return {
            "allowed": True,
            "consumed": tokens_needed,
            "remaining_balance": new_bal,
            "timestamp": now,
        }
