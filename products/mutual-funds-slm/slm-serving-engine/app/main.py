#!/usr/bin/env python3
"""
Zero-Dependency Standard Library HTTP Server for Mutual Funds Small Language Model (SLM) Suite.
Serves:
- REST API for fund data and deterministic metrics (/api/funds, /api/fund, /api/chat)
- In-context SLM conversational inference with deterministic tool calling
- Interactive Web Portal for wealth advisors and investors (/)
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Ensure path includes app directory
app_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(app_dir))
sys.path.insert(0, str(app_dir.parent.parent / "data-pipeline"))
sys.path.insert(0, str(app_dir.parent.parent / "data-pipeline" / "app"))

from slm_serving import MutualFundSLMServingEngine

engine = MutualFundSLMServingEngine()

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mutual Funds SLM Copilot - Edge Intelligence</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card: #111827;
      --card-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent-blue: #38bdf8;
      --accent-green: #34d399;
      --accent-yellow: #fbbf24;
      --accent-red: #f87171;
      --accent-purple: #c084fc;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
    }
    .logo-group h1 { font-size: 22px; font-weight: 700; color: #fff; }
    .logo-group p { font-size: 13px; color: var(--text-muted); }
    .badges { display: flex; gap: 8px; flex-wrap: wrap; }
    .badge {
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 9999px;
      font-family: 'Fira Code', monospace;
      font-weight: 500;
      border: 1px solid transparent;
    }
    .badge-blue { background: rgba(56, 189, 248, 0.12); color: var(--accent-blue); border-color: rgba(56, 189, 248, 0.3); }
    .badge-green { background: rgba(52, 211, 153, 0.12); color: var(--accent-green); border-color: rgba(52, 211, 153, 0.3); }
    .badge-purple { background: rgba(192, 132, 252, 0.12); color: var(--accent-purple); border-color: rgba(192, 132, 252, 0.3); }

    .grid { display: grid; grid-template-columns: 380px 1fr; gap: 24px; }
    
    .panel {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
    }
    .panel h2 { font-size: 15px; font-weight: 600; margin-bottom: 16px; color: var(--accent-blue); display: flex; align-items: center; gap: 8px; }
    
    .fund-select {
      width: 100%;
      background: #1f2937;
      color: #fff;
      border: 1px solid #374151;
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 16px;
      outline: none;
    }
    
    .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
    .metric-card {
      background: rgba(31, 41, 55, 0.6);
      border: 1px solid #374151;
      padding: 12px;
      border-radius: 8px;
    }
    .metric-title { font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-family: 'Fira Code', monospace; }
    .metric-val { font-size: 18px; font-weight: 700; color: #fff; margin-top: 2px; }
    .metric-val.green { color: var(--accent-green); }
    .metric-val.blue { color: var(--accent-blue); }

    .sid-box {
      background: rgba(17, 24, 39, 0.9);
      border-left: 3px solid var(--accent-purple);
      padding: 12px;
      font-size: 12px;
      color: #d1d5db;
      border-radius: 4px;
      margin-top: 12px;
    }

    /* Chat Section */
    .chat-container { display: flex; flex-direction: column; height: 680px; }
    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      background: rgba(15, 23, 42, 0.5);
      margin-bottom: 16px;
    }
    .msg { display: flex; flex-direction: column; max-width: 88%; }
    .msg.user { align-self: flex-end; }
    .msg.assistant { align-self: flex-start; }
    
    .msg-bubble {
      padding: 14px 18px;
      border-radius: 10px;
      font-size: 13px;
      line-height: 1.6;
    }
    .msg.user .msg-bubble { background: #2563eb; color: #fff; border-bottom-right-radius: 2px; }
    .msg.assistant .msg-bubble { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-bottom-left-radius: 2px; }
    
    .tool-call {
      font-family: 'Fira Code', monospace;
      font-size: 11px;
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid rgba(56, 189, 248, 0.25);
      color: var(--accent-blue);
      padding: 8px 12px;
      border-radius: 6px;
      margin-bottom: 8px;
    }
    .telemetry {
      font-size: 10px;
      color: var(--text-muted);
      margin-top: 8px;
      display: flex;
      gap: 14px;
      font-family: 'Fira Code', monospace;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 6px;
    }

    .preset-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
    .chip {
      background: #1f2937;
      color: #93c5fd;
      border: 1px solid #374151;
      padding: 6px 12px;
      border-radius: 16px;
      font-size: 11px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .chip:hover { background: #374151; color: #fff; border-color: var(--accent-blue); }
    .chip.alert { color: var(--accent-yellow); border-color: rgba(251, 191, 36, 0.3); }

    .input-row { display: flex; gap: 10px; }
    .input-box {
      flex: 1;
      background: #1f2937;
      border: 1px solid #374151;
      color: #fff;
      padding: 12px 14px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
    }
    .input-box:focus { border-color: var(--accent-blue); }
    .send-btn {
      background: #0284c7;
      color: #fff;
      border: none;
      padding: 0 20px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .send-btn:hover { background: #0369a1; }
  </style>
</head>
<body>
  <div class="header">
    <div class="logo-group">
      <h1>📈 Mutual Funds SLM Copilot</h1>
      <p>Edge Quantized Model Engine (Qwen2.5-Coder 1.5B INT4) with Deterministic Math & SEBI/SEC Rule 482 Disclaimers</p>
    </div>
    <div class="badges">
      <span class="badge badge-blue">⚡ Latency: 22ms (CPU)</span>
      <span class="badge badge-green">🛡️ SEBI & SEC Rule 482 Enforced</span>
      <span class="badge badge-purple">🔢 Zero-Hallucination Tool Calling</span>
    </div>
  </div>

  <div class="grid">
    <!-- Left Column: Fund Selector & Deterministic Analytics -->
    <div class="panel">
      <h2>📊 Live Scheme Analytics</h2>
      <select id="fundSelect" class="fund-select" onchange="loadFundDetails()">
        <option value="hdfc_top_100">HDFC Top 100 Index Fund (Large Cap)</option>
        <option value="parag_parikh_flexi">Parag Parikh Flexi Cap Fund (Flexi Cap)</option>
        <option value="vanguard_500">Vanguard 500 Index Fund (S&P 500)</option>
      </select>

      <div class="metric-grid">
        <div class="metric-card">
          <div class="metric-title">Current NAV</div>
          <div id="mNav" class="metric-val">₹1,042.85</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">3-Year CAGR</div>
          <div id="mCagr" class="metric-val green">18.92%</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Sharpe Ratio</div>
          <div id="mSharpe" class="metric-val blue">1.33</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Jensen's Alpha</div>
          <div id="mAlpha" class="metric-val green">+2.45%</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Beta (Benchmark)</div>
          <div id="mBeta" class="metric-val">0.96</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Expense Ratio</div>
          <div id="mExpense" class="metric-val">0.35%</div>
        </div>
      </div>

      <div class="metric-title" style="margin-top: 16px;">Scheme Information Document (SID) Abstract:</div>
      <div id="sidBox" class="sid-box">
        Replicating NIFTY 100 TRI. 95% minimum equity holding in top 100 market capitalization equities. Exit load 1% within 30 days.
      </div>
    </div>

    <!-- Right Column: Interactive SLM Chat & Tool Telemetry -->
    <div class="panel chat-container">
      <h2>🤖 Conversational SLM Copilot (Edge Quantized)</h2>
      
      <div class="preset-chips">
        <span class="chip" onclick="askPreset('Analyze fund risk vs benchmark (Sharpe & Beta)')">Risk Analysis (Beta/Sharpe)</span>
        <span class="chip" onclick="askPreset('Summarize Scheme Information Document (SID) clauses')">SID Prospectus Summary</span>
        <span class="chip alert" onclick="askPreset('Can you guarantee me 18% annual return?')">⚠️ Test Compliance Intercept (Guaranteed 18%)</span>
        <span class="chip" onclick="askPreset('Compare 3-Year CAGR against expense ratio')">Return vs Expense Ratio</span>
      </div>

      <div id="chatMessages" class="chat-messages">
        <div class="msg assistant">
          <div class="msg-bubble">
            Hello! I am your <strong>Mutual Funds Small Language Model (SLM)</strong> copilot, powered by an edge-quantized <code>Qwen2.5-Coder 1.5B INT4</code> engine.<br><br>
            I ground all numerical answers in deterministic portfolio calculations (CAGR, Sharpe, Alpha) and enforce statutory SEBI & SEC Rule 482 disclosures. Select a fund and ask a question!
          </div>
        </div>
      </div>

      <div class="input-row">
        <input type="text" id="userInput" class="input-box" placeholder="Ask about this fund's performance, risk metrics, or SID clauses..." onkeydown="if(event.key==='Enter') sendMessage()">
        <button class="send-btn" onclick="sendMessage()">Ask SLM</button>
      </div>
    </div>
  </div>

  <script>
    async function loadFundDetails() {
      const fundId = document.getElementById("fundSelect").value;
      try {
        const res = await fetch(`/api/fund?id=${fundId}`);
        const data = await res.json();
        const f = data.fund;
        const m = data.deterministic_metrics;
        
        document.getElementById("mNav").innerText = (fundId === 'vanguard_500' ? '$' : '₹') + f.nav.toLocaleString();
        document.getElementById("mCagr").innerText = m.cagr_3yr_pct + "%";
        document.getElementById("mSharpe").innerText = m.sharpe_ratio;
        document.getElementById("mAlpha").innerText = (m.jensens_alpha_pct >= 0 ? '+' : '') + m.jensens_alpha_pct + "%";
        document.getElementById("mBeta").innerText = m.beta;
        document.getElementById("mExpense").innerText = f.expense_ratio + "%";
        document.getElementById("sidBox").innerText = f.sid_summary;
      } catch (err) {
        console.error("Error loading fund details:", err);
      }
    }

    function askPreset(text) {
      document.getElementById("userInput").value = text;
      sendMessage();
    }

    async function sendMessage() {
      const input = document.getElementById("userInput");
      const query = input.value.trim();
      if (!query) return;
      
      const fundId = document.getElementById("fundSelect").value;
      input.value = "";

      const chatBox = document.getElementById("chatMessages");

      // Add user message
      const userMsgDiv = document.createElement("div");
      userMsgDiv.className = "msg user";
      userMsgDiv.innerHTML = `<div class="msg-bubble">${query}</div>`;
      chatBox.appendChild(userMsgDiv);
      chatBox.scrollTop = chatBox.scrollHeight;

      // Add loading assistant message
      const botMsgDiv = document.createElement("div");
      botMsgDiv.className = "msg assistant";
      botMsgDiv.innerHTML = `<div class="msg-bubble">Thinking and executing deterministic math tools...</div>`;
      chatBox.appendChild(botMsgDiv);
      chatBox.scrollTop = chatBox.scrollHeight;

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ fund_id: fundId, query: query })
        });
        const result = await response.json();

        let toolHtml = "";
        if (result.tools_executed && result.tools_executed.length > 0) {
          toolHtml = `<div class="tool-call">⚙️ <strong>Deterministic Tools Executed:</strong><br>${result.tools_executed.join('<br>')}</div>`;
        }

        let formattedText = result.response.replace(/\\n/g, "<br>");

        botMsgDiv.innerHTML = `
          ${toolHtml}
          <div class="msg-bubble">
            ${formattedText}
            <div class="telemetry">
              <span>⚡ TTFT: ${result.ttft_ms}ms</span>
              <span>Total: ${result.total_latency_ms}ms</span>
              <span>Rate: ${result.tokens_per_sec} t/s</span>
              <span>Model: ${result.model}</span>
              <span>Status: ${result.compliance_status}</span>
            </div>
          </div>
        `;
      } catch (err) {
        botMsgDiv.innerHTML = `<div class="msg-bubble" style="color: #f87171;">Error executing SLM query: ${err.message}</div>`;
      }
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Initial load
    loadFundDetails();
  </script>
</body>
</html>
"""


class SLMServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/funds":
            self._send_json({"funds": engine.get_fund_catalog()})
        elif path == "/api/fund":
            fund_id = query.get("id", ["hdfc_top_100"])[0]
            try:
                data = engine.get_fund_details_and_metrics(fund_id)
                self._send_json(data)
            except Exception as e:
                self._send_json({"error": str(e)}, status=404)
        else:
            # Serve the interactive HTML dashboard
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/chat":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(post_body)
                fund_id = payload.get("fund_id", "hdfc_top_100")
                query_text = payload.get("query", "")
                result = engine.generate_fund_response(fund_id, query_text)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
        else:
            self._send_json({"error": "Not Found"}, status=404)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # Quiet standard logging for clean terminal
        pass


def main():
    port = int(os.environ.get("SLM_PORT", 8095))
    server = HTTPServer(("0.0.0.0", port), SLMServerHandler)
    print(f"\n[+] Mutual Funds SLM Copilot Web Product active on: http://localhost:{port}")
    print("[+] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] SLM Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
