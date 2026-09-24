/**
 * Pay Through Crypto Client SDK
 * Autonomous cross-repo SDK built by ASCM.
 */

class CryptoPaymentSDK {
  constructor(baseUrl = "http://127.0.0.1:8001") {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  async createInvoice(amountUsd, currency = "USDT", metadata = {}) {
    const res = await fetch(`${this.baseUrl}/api/v1/crypto/invoice/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount_usd: amountUsd, currency, metadata })
    });
    return res.json();
  }

  async verifyPayment(payload) {
    const res = await fetch(`${this.baseUrl}/api/v1/crypto/payment/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  }

  async getMetrics() {
    const res = await fetch(`${this.baseUrl}/api/v1/crypto/metrics`);
    return res.json();
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CryptoPaymentSDK };
}
