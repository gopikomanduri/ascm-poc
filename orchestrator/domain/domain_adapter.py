"""
Universal Domain Adaptation Engine for ASCM.

Dynamically adapts the entire multi-agent squad (Product, Architect, Coder,
Reviewers, Business Strategy) to ANY industry domain (CAD/CAM, MedTech,
Robotics, FinTech, DevTools, AI/ML, E-Commerce, Gaming, etc.).

Also provides domain-aware model routing to select the best frontier or local
LLM for each domain's computational characteristics.
"""

import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class DomainProfile(BaseModel):
    domain_id: str
    display_name: str
    category_summary: str
    primary_language: str = "python"
    core_primitives: List[str] = Field(default_factory=list)
    grilling_dimensions: List[str] = Field(default_factory=list)
    architectural_patterns: List[str] = Field(default_factory=list)
    standard_libraries: Dict[str, List[str]] = Field(default_factory=dict)
    safety_and_nfr_focus: List[str] = Field(default_factory=list)
    competitor_archetypes: List[Dict[str, str]] = Field(default_factory=list)
    preferred_models: Dict[str, str] = Field(default_factory=dict)
    unit_test_frameworks: Dict[str, str] = Field(default_factory=dict)
    role_titles: Dict[str, str] = Field(default_factory=dict)


# Catalog of pre-configured vertical domains
VERTICAL_DOMAINS: Dict[str, DomainProfile] = {
    "LEGALTECH_COMPLIANCE": DomainProfile(
        domain_id="LEGALTECH_COMPLIANCE",
        display_name="LegalTech, Regulatory Engineering & Compliance Automation",
        category_summary="Contract lifecycle automation, clause extraction, redlining, regulatory compliance (GDPR/HIPAA/SEC), attorney-client privilege protection, and immutable audit trails.",
        primary_language="python",
        core_primitives=[
            "Contract AST & Clause Extraction", "Statutory Jurisdictions & Rule Parsing",
            "Redlining & Semantic Diffing", "Data Residency & Attorney-Client Privilege",
            "Audit Trails & Immutable Chain-of-Custody", "Dual-Key Authorization & Signoff Workflow",
            "Privilege Tagging & Redaction", "Regulatory Citation Indexing"
        ],
        grilling_dimensions=[
            "1. Jurisdiction & Statutory Scope: US Federal/State, EU GDPR / EU AI Act, Indian BNS/IT Act, or cross-border multi-jurisdiction?",
            "2. Contract Ingestion & Parsing: Unstructured PDF/Word (DocX) with OCR vs structured JSON schema vs smart legal contract markup?",
            "3. Confidentiality & Privilege: Strict zero-retention API policies, field-level encryption at rest, data sovereignty, and attorney-client privilege safeguards?",
            "4. Legal Reasoning & Clause Verification: Deterministic rule engines vs LLM clause classification with human-in-the-loop counsel sign-off?",
            "5. Liability & UPL Disclaimers: Enforcing Unauthorized Practice of Law (UPL) guardrails, liability caps, and jurisdiction-specific audit logs?"
        ],
        architectural_patterns=[
            "Clause-Level AST Transformer & Classifier",
            "Zero-Retention Cryptographic Vault",
            "Immutable Append-Only Audit Ledger",
            "Dual-Key Authorization & Signoff Workflow"
        ],
        standard_libraries={
            "python": ["spacy", "pydantic", "python-docx", "pypdf", "cryptography", "fastapi"],
            "node": ["pdf-parse", "mammoth", "crypto", "@types/node"],
            "go": ["github.com/ledongthuc/pdf", "crypto/aes", "crypto/sha256"]
        },
        safety_and_nfr_focus=[
            "Zero retention of privileged legal documents in public model logs",
            "Field-level AES-256-GCM encryption for client confidential clauses",
            "Audit logging of all contract modifications with cryptographic hash signatures",
            "Deterministic clause validation to prevent hallucinated citations"
        ],
        competitor_archetypes=[
            {"competitor": "Harvey AI", "limitations": "Closed invite-only enterprise pricing, opaque proprietary models, high lock-in.", "ascm_advantage": "Self-hosted, transparent Git-native pipelines with inspectable open-source code and BYOK privacy."},
            {"competitor": "Ironclad / Robin AI", "limitations": "Rigid CLM workflow walls, difficult to customize with custom code or internal microservices.", "ascm_advantage": "Autonomous generation of dedicated, deployable legal microservices directly into engineering repos."}
        ],
        preferred_models={
            "coder": "gpt-4o",
            "reviewer": "claude-3-5-sonnet",
            "architect": "gemini-2.5-pro",
            "product": "gemini-2.5-flash",
            "business": "gemini-2.5-flash"
        },
        unit_test_frameworks={"python": "unittest", "node": "jest", "go": "testing"},
        role_titles={
            "product": "Specialized LegalTech & Regulatory Compliance Expert",
            "architect": "Lead Legal Systems Architect & Regulatory Framework Lead",
            "thinking": "Senior Legal Systems Architecture Critic & Compliance Invariant Auditor",
            "code_review": "Adversarial Senior LegalTech Code Reviewer & Privilege Security Specialist",
            "orchestrator": "Lead Legal & Technical Workflow Orchestrator",
            "planner": "LegalTech Execution Planner & Task Coordinator",
            "coder": "Principal LegalTech Software Engineer & TDD Specialist",
            "business": "Chief Commercial Officer & LegalTech GTM Strategist",
            "security": "LegalTech Data Privacy & Regulatory Security Auditor"
        }
    ),

    "CAD_CAM": DomainProfile(
        domain_id="CAD_CAM",
        display_name="Computer-Aided Design (CAD) & Manufacturing (CAM)",
        category_summary="Parametric 3D modeling, geometric kernels, CNC toolpath generation, G-code synthesis, and physical tolerance engineering.",
        primary_language="python",
        core_primitives=[
            "Boundary Representation (B-Rep)", "NURBS curves & surfaces", "Polygon Meshes (STL/OBJ)",
            "STEP/IGES exchange formats", "G-code post-processing", "3-axis/5-axis toolpaths",
            "Spindle feed rates & cutting physics", "Geometric tolerances & kerf compensation"
        ],
        grilling_dimensions=[
            "1. Geometry Kernel & Representation: Parametric B-Rep/NURBS (STEP/IGES) vs Polygonal Mesh (STL/OBJ)? What precision/dimensional tolerance (e.g. ±0.001mm)?",
            "2. Machining & Toolpath Strategy: 3-axis vs 5-axis CNC milling, adaptive clearing, contour pocketing, feed rate and spindle speed calculation?",
            "3. Controller Dialect & Post-Processing: What machine syntax (Fanuc, Haas, LinuxCNC, GRBL, Siemens Sinumerik)?",
            "4. Collision Avoidance & Rapid Moves: How are toolholder gouge protection, retract heights, and rapid traverse clearances enforced?",
            "5. Viewport & Visualization: WebGL/Three.js interactive 3D viewport, toolpath animation, material removal simulation?"
        ],
        architectural_patterns=[
            "Scene Graph & Spatial Partitioning (BVH/Octree)",
            "Pipelined Geometry Evaluation Kernel",
            "G-code Emitter with State Machine & Feed Interpolator",
            "Toolpath Mesh Slicer & Contour Offset Engine"
        ],
        standard_libraries={
            "python": ["numpy", "scipy", "trimesh", "shapely", "numpy-stl", "open3d"],
            "go": ["github.com/fogleman/fauxgl", "github.com/qmuntal/gltf", "gonum.org/v1/gonum/mat"],
            "node": ["three", "@types/three", "earcut", "manifold-3d"]
        },
        safety_and_nfr_focus=[
            "Tool collision detection with stock/clamps",
            "Spindle overload / chatter vibration limits",
            "Float precision rounding errors in linear/arc interpolation (G01/G02/G03)",
            "Memory efficiency when slicing multi-million triangle meshes"
        ],
        competitor_archetypes=[
            {"competitor": "Autodesk Fusion 360", "limitations": "Expensive proprietary cloud lock-in; closed geometry kernel.", "ascm_advantage": "Open-core, fully inspectable parametric pipeline integrated into Git repos."},
            {"competitor": "SolidWorks / Mastercam", "limitations": "Legacy desktop monoliths, Windows-only, zero programmable Git automation.", "ascm_advantage": "Modern cross-platform headless API, automated code generation, and CI/CD testing."},
            {"competitor": "FreeCAD", "limitations": "Complex steep UI, unstable Python macro scripts, lack of automated web-first pipelines.", "ascm_advantage": "Clean headless microservices with verified web viewports and automatic tests."}
        ],
        preferred_models={
            "coder": "qwen2.5-coder:32b",     # Excels at math, coordinate geometry, matrices, G-code
            "reviewer": "claude-3-5-sonnet",   # Top-tier code verification & precision auditing
            "architect": "gemini-2.5-pro",     # Deep context reasoning over 3D topology
            "product": "gemini-2.5-flash",     # Low-latency interactive stakeholder grilling
        },
        unit_test_frameworks={"python": "unittest", "go": "testing", "node": "jest"},
        role_titles={
            "product": "Specialized CAD/CAM & Geometric Manufacturing Expert",
            "architect": "Lead CAD/CAM Geometry Systems Architect",
            "thinking": "Senior CAD/CAM Architecture Critic & Physical Kinematics Auditor",
            "code_review": "Adversarial Senior CNC & Toolpath Code Reviewer",
            "orchestrator": "Lead CAD/CAM Manufacturing Orchestrator",
            "planner": "CNC Toolpath Planning & Task Coordinator",
            "coder": "Principal CAD/CAM Algorithms Engineer & Geometric TDD Specialist",
            "business": "Chief Commercial Officer & Industrial CAD/CAM GTM Strategist",
            "security": "Machining Safety & CNC Collision Auditor"
        }
    ),

    "FINTECH_CRYPTO": DomainProfile(
        domain_id="FINTECH_CRYPTO",
        display_name="Crypto & Web3 Payment Infrastructure",
        category_summary="Non-custodial cryptocurrency checkout, blockchain settlement, double-spend prevention, and timing-safe signature verification.",
        primary_language="python",
        core_primitives=[
            "EVM & Solana address validation", "HMAC-SHA256 signature verification", "Replay protection",
            "Mempool watcher & block finality", "Crypto-to-fiat conversion rate locks", "Non-custodial treasuries"
        ],
        grilling_dimensions=[
            "1. Chains & Tokens: EVM (Ethereum, Polygon, Arbitrum) vs Solana vs Bitcoin; USDT/USDC vs native ETH/BTC?",
            "2. Settlement Flow: Direct on-chain Crypto-to-Crypto (self-custody) vs Crypto-to-Fiat (auto-offramp to INR/USD bank account)?",
            "3. Transfer Mechanics & UX: Injected Web3 wallet (MetaMask/WalletConnect) vs dynamic QR invoice address?",
            "4. Volatility & Gas Economics: Who covers network gas? What is the exchange rate lock window (e.g. 15-min freeze)?",
            "5. Regulatory & Tax: Handling KYC/AML, Indian FIU-IND compliance, and 1% TDS on Virtual Digital Assets (VDA)?"
        ],
        architectural_patterns=[
            "Idempotent Event-Driven Webhook Gateway",
            "State Machine (PENDING -> CONFIRMING -> SETTLED / EXPIRED)",
            "Timing-Safe Cryptographic Verifier",
            "Sliding-Window Replay Cache"
        ],
        standard_libraries={
            "python": ["cryptography", "web3", "eth-account", "fastapi"],
            "go": ["github.com/ethereum/go-ethereum", "crypto/hmac", "crypto/sha256"],
            "node": ["ethers", "viem", "@solana/web3.js", "crypto"]
        },
        safety_and_nfr_focus=[
            "Constant-time digest comparison (hmac.compare_digest)",
            "Double-spend transaction hash rejection",
            "Replay window expiry",
            "Sub-50ms cryptographic signature check"
        ],
        competitor_archetypes=[
            {"competitor": "BitPay / Coinbase Commerce", "limitations": "Custodial holdbacks, 1% withdrawal fees, account freeze risks.", "ascm_advantage": "100% self-sovereign code directly in merchant repo with zero third-party escrow."},
            {"competitor": "Stripe Crypto", "limitations": "US/EU only, high fees, no INR offramps.", "ascm_advantage": "Global accessibility, extensible local fiat connectors."}
        ],
        preferred_models={
            "coder": "gpt-4o",
            "reviewer": "claude-3-5-sonnet",
            "architect": "gemini-2.5-pro",
            "product": "gemini-2.5-flash",
        },
        unit_test_frameworks={"python": "unittest", "go": "testing", "node": "jest"},
        role_titles={
            "product": "Specialized Crypto, Web3 & FinTech Payments Expert",
            "architect": "Lead Crypto Protocol & Settlement Systems Architect",
            "thinking": "Senior Web3 Architecture Critic & Smart Contract Auditor",
            "code_review": "Adversarial Senior Blockchain & Cryptographic Code Reviewer",
            "orchestrator": "Lead Web3 Financial Orchestrator",
            "planner": "Crypto Gateway Execution Planner",
            "coder": "Principal Blockchain & FinTech Software Engineer & TDD Specialist",
            "business": "Chief Commercial Officer & Web3 Payments GTM Strategist",
            "security": "Cryptographic Protocol & Smart Contract Security Auditor"
        }
    ),

    "HEALTHCARE_MEDTECH": DomainProfile(
        domain_id="HEALTHCARE_MEDTECH",
        display_name="Healthcare & MedTech Systems",
        category_summary="Clinical data interoperability, HL7/FHIR protocols, DICOM medical imaging, HIPAA privacy, and SaMD validation.",
        primary_language="python",
        core_primitives=[
            "HL7 v2 & FHIR R4 resources", "DICOM medical image parsing", "HIPAA/HITECH audit logging",
            "EHR integration (Epic/Cerner)", "De-identification / PHI redaction", "FDA 510(k) SaMD design controls"
        ],
        grilling_dimensions=[
            "1. Interoperability Standards: FHIR R4 JSON REST API vs legacy HL7 v2 MLLP pipe-delimited feeds?",
            "2. Clinical Data Scope: Patient demographics, observations/vitals, diagnostic reports, or DICOM imaging metadata?",
            "3. Privacy & Compliance: HIPAA Business Associate Agreement (BAA) constraints, field-level encryption at rest, and audit trail retention?",
            "4. Identity & Authorization: SMART-on-FHIR OAuth2 / OpenID Connect with clinical role-based access control (RBAC)?",
            "5. EHR Target: Direct integration with Epic App Orchard, Cerner SMART, or standalone clinical microservice?"
        ],
        architectural_patterns=[
            "SMART-on-FHIR Identity Gateway",
            "HL7 Message Parser & Event Transformer",
            "Immutable Clinical Audit Log Pipeline",
            "Field-Level AES-256-GCM Encrypted Storage"
        ],
        standard_libraries={
            "python": ["fhir.resources", "pydicom", "cryptography", "sqlalchemy"],
            "go": ["github.com/samply/golang-fhir-models", "crypto/aes"],
            "node": ["@types/fhir", "dicom-parser", "jsonwebtoken"]
        },
        safety_and_nfr_focus=[
            "Zero unprotected Protected Health Information (PHI) in application logs",
            "Strict patient consent validation before data disclosure",
            "Sub-100ms FHIR resource lookup for emergency clinical workflows"
        ],
        competitor_archetypes=[
            {"competitor": "Redox Engine", "limitations": "Expensive per-connection SaaS fee, vendor lock-in.", "ascm_advantage": "Self-hosted FHIR microservice with native repo ownership and zero per-patient tolls."}
        ],
        preferred_models={
            "coder": "gpt-4o",
            "reviewer": "claude-3-5-sonnet",
            "architect": "gemini-2.5-pro",
            "product": "gemini-2.5-flash",
        },
        unit_test_frameworks={"python": "unittest", "go": "testing", "node": "jest"},
        role_titles={
            "product": "Specialized Healthcare & MedTech Interoperability Expert",
            "architect": "Lead Health Informatics Architect & HIPAA Compliance Lead",
            "thinking": "Senior Clinical Systems Architecture Critic & SaMD Auditor",
            "code_review": "Adversarial Senior Clinical Software Reviewer & PHI Security Auditor",
            "orchestrator": "Lead Healthcare & Clinical Workflow Orchestrator",
            "planner": "Clinical Integration Planner & Task Coordinator",
            "coder": "Principal Health Informatics Software Engineer & TDD Specialist",
            "business": "Chief Commercial Officer & MedTech GTM Strategist",
            "security": "HIPAA & Patient Health Information (PHI) Security Auditor"
        }
    ),

    "ROBOTICS_EMBEDDED": DomainProfile(
        domain_id="ROBOTICS_EMBEDDED",
        display_name="Robotics, IoT & Embedded Systems",
        category_summary="Real-time control loops, sensor fusion, microcontrollers, ROS2 nodes, CAN/UART bus protocols, and actuator telemetry.",
        primary_language="python",
        core_primitives=[
            "Real-Time Operating System (RTOS)", "ROS2 (Robot Operating System)", "CAN / UART / I2C / SPI buses",
            "Sensor Fusion (IMU, LiDAR, Encoders)", "PID / State-space control loops", "Low-power sleep states"
        ],
        grilling_dimensions=[
            "1. Compute Hardware & OS: Bare-metal microcontroller (STM32/ESP32) with FreeRTOS vs Embedded Linux with ROS2?",
            "2. Control Loop Frequency: What loop deadline (e.g. 1kHz motor PID vs 50Hz sensor polling)? Is execution hard real-time?",
            "3. Bus Protocol & Interconnect: CAN-bus (CANopen/J1939), RS-485, SPI, or Ethernet/MQTT?",
            "4. Safety & Watchdogs: Hardware watchdog timer (WDT), emergency stop (E-Stop) circuitry, brownout protection?",
            "5. Power Budget: Battery-powered low-power modes (microamps) vs line-powered continuous high-torque duty cycle?"
        ],
        architectural_patterns=[
            "Zero-Allocation State Machine",
            "Ring-Buffer Interrupt Service Routine (ISR) Queue",
            "ROS2 Publisher/Subscriber Node Topology",
            "Watchdog Supervisor & Fail-Safe Interlock"
        ],
        standard_libraries={
            "python": ["pyserial", "can", "numpy"],
            "go": ["periph.io/x/conn/v3", "tinygo.org/x/drivers"],
            "node": ["serialport", "onoff"]
        },
        safety_and_nfr_focus=[
            "Deterministic loop execution jitter (< 50 microseconds)",
            "Dynamic memory allocation (malloc/free) forbidden in interrupt contexts",
            "Actuator hardware interlocks on communication loss"
        ],
        competitor_archetypes=[
            {"competitor": "Keil / IAR Embedded", "limitations": "Expensive proprietary toolchains, poor Git collaboration.", "ascm_advantage": "Modern open toolchains (PlatformIO, TinyGo, CMake) with automated unit test harnesses."}
        ],
        preferred_models={
            "coder": "qwen2.5-coder:32b",
            "reviewer": "claude-3-5-sonnet",
            "architect": "gpt-4o",
            "product": "gemini-2.5-flash",
        },
        unit_test_frameworks={"python": "unittest", "go": "testing", "node": "jest"},
        role_titles={
            "product": "Specialized Robotics, IoT & Embedded Systems Expert",
            "architect": "Lead Robotics Systems & Real-Time Control Architect",
            "thinking": "Senior Real-Time Architecture Critic & Hardware Safety Auditor",
            "code_review": "Adversarial Senior Embedded Systems & Firmware Reviewer",
            "orchestrator": "Lead Robotics & Embedded Systems Orchestrator",
            "planner": "Robotics Control Loop Planner & Task Coordinator",
            "coder": "Principal Embedded Systems Engineer & Low-Level TDD Specialist",
            "business": "Chief Commercial Officer & Industrial Automation GTM Strategist",
            "security": "Hardware Interlock & Embedded Firmware Security Auditor"
        }
    ),

    "DEVTOOLS_COMPILER": DomainProfile(
        domain_id="DEVTOOLS_COMPILER",
        display_name="Developer Tools, Compilers & Systems Infrastructure",
        category_summary="Abstract Syntax Tree (AST) parsing, intermediate representations, type checkers, CLI tools, and high-throughput runtimes.",
        primary_language="python",
        core_primitives=[
            "Lexer & Parser (CFG / PEG)", "AST / Concrete Syntax Tree", "Intermediate Representation (IR)",
            "Static Analysis & Linting", "CLI Argument & Subcommand routing", "Hot reloading & file watchers"
        ],
        grilling_dimensions=[
            "1. Grammars & Parsing: Hand-written recursive descent vs parser generator (ANTLR/Tree-sitter)?",
            "2. Target Output: Source-to-source transpilation, bytecode VM interpretation, or native binary emission?",
            "3. Type Checking & Safety: Dynamic duck typing vs static Hindley-Milner type inference?",
            "4. Performance & Memory: In-memory AST footprint, streaming incremental parsing, multi-threaded parallel compilation?",
            "5. Developer Ergonomics: Diagnostic error reporting with precise source code line, column, and ASCII caret highlighting?"
        ],
        architectural_patterns=[
            "Visitor / Walker Pattern over Immutable AST Nodes",
            "Pipelined Compiler Passes (Lex -> Parse -> TypeCheck -> Optimize -> Emit)",
            "Incremental File Hash Cache for Build Acceleration"
        ],
        standard_libraries={
            "python": ["ast", "tree_sitter", "click", "rich"],
            "go": ["go/parser", "go/ast", "github.com/spf13/cobra"],
            "node": ["acorn", "typescript", "commander"]
        },
        safety_and_nfr_focus=[
            "Zero stack overflow crashes on deeply nested syntax trees",
            "Graceful recovery on syntax errors without aborting file parsing",
            "Sub-50ms latency for real-time IDE diagnostics"
        ],
        competitor_archetypes=[
            {"competitor": "Babel / SWC / esbuild", "limitations": "Complex monolithic plugin ecosystems with fragile custom transforms.", "ascm_advantage": "Self-documenting, clean modular AST pipelines customized directly for project requirements."}
        ],
        preferred_models={
            "coder": "qwen2.5-coder:32b",
            "reviewer": "claude-3-5-sonnet",
            "architect": "gpt-4o",
            "product": "gemini-2.5-flash",
        },
        unit_test_frameworks={"python": "unittest", "go": "testing", "node": "jest"},
        role_titles={
            "product": "Specialized Developer Tools, Compilers & Systems Infrastructure Expert",
            "architect": "Lead Language Runtimes & Compiler Architect",
            "thinking": "Senior Compilers & AST Architecture Critic",
            "code_review": "Adversarial Senior Compiler & Systems Code Reviewer",
            "orchestrator": "Lead Developer Tooling Orchestrator",
            "planner": "Compiler Pipeline Planner & Pass Coordinator",
            "coder": "Principal Compilers & Developer Tools Software Engineer & TDD Specialist",
            "business": "Chief Commercial Officer & DevTools GTM Strategist",
            "security": "AST Sanitization & Memory Safety Auditor"
        }
    ),

    "AI_ML_SYSTEMS": DomainProfile(
        domain_id="AI_ML_SYSTEMS",
        display_name="AI, Machine Learning & Agentic Infrastructure",
        category_summary="Autonomous agent orchestration, prompt caching, RAG retrieval, vector embeddings, streaming inference, and token budgeting.",
        primary_language="python",
        core_primitives=[
            "Model cascading & fallbacks", "RAG vector retrieval", "Prompt caching & token accounting",
            "Streaming Server-Sent Events (SSE)", "Tool calling / Function calling", "Evaluation benchmarks"
        ],
        grilling_dimensions=[
            "1. Model Routing & Fallback: Multi-provider tiering (fast vs primary) with automated 429/503 circuit breakers?",
            "2. Retrieval & Context: In-memory semantic search vs vector DB (Chroma, Qdrant, Pinecone) with chunking?",
            "3. Streaming & Latency: Chunked Server-Sent Events (SSE) streaming vs synchronous JSON responses?",
            "4. Token Budget & Guardrails: Pre-flight token forecasting, rate limiting, and output moderation?",
            "5. Evaluation: Automated ground-truth eval datasets, LLM-as-a-judge scoring, latency telemetry?"
        ],
        architectural_patterns=[
            "Provider Abstraction with Retry & Circuit Breakers",
            "Asynchronous Event-Driven Agent State Machine",
            "Context Window Sliding-Window Buffer"
        ],
        standard_libraries={
            "python": ["google-genai", "openai", "anthropic", "chromadb", "pydantic"],
            "go": ["github.com/sashabaranov/go-openai", "github.com/google/generative-ai-go"],
            "node": ["@google/genai", "openai", "@anthropic-ai/sdk"]
        },
        safety_and_nfr_focus=[
            "PII redaction prior to outbound API calls",
            "Zero unhandled rate-limit crashes",
            "Token spend ceiling enforcement"
        ],
        competitor_archetypes=[
            {"competitor": "LangChain / CrewAI", "limitations": "Heavy abstraction sprawl, high latency, complex debugging.", "ascm_advantage": "Lean, typed, contract-verified microservices with built-in P90 cost radar."}
        ],
        preferred_models={
            "coder": "gpt-4o",
            "reviewer": "claude-3-5-sonnet",
            "architect": "gemini-2.5-pro",
            "product": "gemini-2.5-flash",
        },
        unit_test_frameworks={"python": "unittest", "go": "testing", "node": "jest"},
        role_titles={
            "product": "Specialized AI, Machine Learning & Agentic Systems Expert",
            "architect": "Lead AI Systems Architect & Multi-Agent Designer",
            "thinking": "Senior AI Systems Architecture Critic & Guardrails Auditor",
            "code_review": "Adversarial Senior AI Code Reviewer & Model Safety Specialist",
            "orchestrator": "Lead Autonomous Agent Orchestrator",
            "planner": "Agentic Execution Planner & Token Budget Coordinator",
            "coder": "Principal AI Infrastructure Software Engineer & TDD Specialist",
            "business": "Chief Commercial Officer & Enterprise AI GTM Strategist",
            "security": "Prompt Injection & Model Privacy Security Auditor"
        }
    ),

    "GENERIC_MICROSERVICE": DomainProfile(
        domain_id="GENERIC_MICROSERVICE",
        display_name="Enterprise Web Application & Microservice",
        category_summary="REST/GraphQL APIs, multi-tenant databases, authentication, background workers, and horizontal scalability.",
        primary_language="go",
        core_primitives=[
            "REST / gRPC / GraphQL endpoints", "Relational & NoSQL persistence", "JWT / OAuth2 authentication",
            "Background job queues", "Health checks & metrics (/healthz, /metrics)", "Horizontal auto-scaling"
        ],
        grilling_dimensions=[
            "1. API Protocol & Contracts: RESTful OpenAPI vs gRPC protobuf vs GraphQL schema?",
            "2. Data Persistence & Multi-Tenancy: PostgreSQL, MySQL, or MongoDB? Tenant isolation via schema vs tenant_id column?",
            "3. Auth & Authorization: JWT bearer tokens, session cookies, or OAuth2 / OpenID Connect?",
            "4. Asynchronous Workflows: Synchronous request/response vs message queue (Redis Celery, RabbitMQ, Kafka)?",
            "5. Observability: Structured JSON logging, Prometheus metrics endpoints, and health check probes?"
        ],
        architectural_patterns=[
            "Clean Architecture / Hexagonal Ports & Adapters",
            "Repository Pattern for Persistence Abstraction",
            "Middleware Pipeline for Auth, CORS, and Telemetry"
        ],
        standard_libraries={
            "python": ["fastapi", "sqlalchemy", "pydantic", "uvicorn"],
            "go": ["github.com/gin-gonic/gin", "gorm.io/gorm", "github.com/stretchr/testify"],
            "node": ["express", "prisma", "zod", "jest"]
        },
        safety_and_nfr_focus=[
            "OWASP Top 10 mitigation (SQL injection, XSS, CSRF)",
            "Constant-time password hashing (argon2 / bcrypt)",
            "Database connection pooling and query timeout bounds"
        ],
        competitor_archetypes=[
            {"competitor": "Standard Boilerplates", "limitations": "Static generic scaffolding without business or architectural review.", "ascm_advantage": "Full-stack multi-agent verification with autonomous unit testing."}
        ],
        preferred_models={
            "coder": "gpt-4o",
            "reviewer": "claude-3-5-sonnet",
            "architect": "gemini-2.5-pro",
            "product": "gemini-2.5-flash",
        },
        unit_test_frameworks={"python": "unittest", "go": "testing", "node": "jest"},
        role_titles={
            "product": "Specialized Enterprise Software & Systems Product Expert",
            "architect": "Lead Cloud Systems Architect & Distributed Systems Principal",
            "thinking": "Senior Architecture Critic & NFR Systems Auditor",
            "code_review": "Adversarial Senior Principal Code Reviewer",
            "orchestrator": "Lead Enterprise Software Orchestrator",
            "planner": "Microservices Execution Planner & Task Coordinator",
            "coder": "Principal Software Engineer & TDD Specialist",
            "business": "Chief Commercial Officer & Enterprise SaaS GTM Strategist",
            "security": "Application Security & OWASP Top 10 Auditor"
        }
    )
}


class DomainAdapter:
    """
    Intelligent engine that detects the domain of any user request and injects
    domain-expert intelligence, dynamic role titles, coding languages, and optimal model routing across the squad.
    """

    @classmethod
    def detect_domain(cls, user_goal: str, context: Optional[str] = None) -> DomainProfile:
        combined = f"{user_goal} {context or ''}".lower()

        # LegalTech / Regulatory Compliance / Contracts / Law
        legal_keywords = [
            "legal", "law", "laws", "lawyer", "lawyers", "attorney", "attorneys", "contract", "contracts",
            "clause", "clauses", "nda", "ndas", "gdpr", "regulatory", "compliance", "ediscovery",
            "litigation", "redline", "redlining", "terms of service", "tos", "privacy policy",
            "court", "statute", "statutes", "statutory", "trademark", "patent", "bar association", "paralegal"
        ]
        if any(re.search(rf"\b{re.escape(k)}\b", combined) for k in legal_keywords):
            return VERTICAL_DOMAINS["LEGALTECH_COMPLIANCE"]

        # CAD / CAM / 3D Graphics / CNC
        if any(k in combined for k in [
            "cad", "cam", "cnc", "toolpath", "g-code", "gcode", "g code", "mesh", "stl", "step",
            "iges", "b-rep", "nurbs", "spindle", "milling", "lathe", "slicer", "3d print",
            "open3d", "trimesh", "parametric", "3d model", "three.js", "viewport"
        ]):
            return VERTICAL_DOMAINS["CAD_CAM"]

        # Crypto / Web3 / Blockchain Payments
        if any(k in combined for k in [
            "crypto", "bitcoin", "ethereum", "web3", "token", "usdt", "usdc", "solana",
            "blockchain", "mempool", "wallet", "metamask", "escrow", "onchain", "smart contract"
        ]):
            return VERTICAL_DOMAINS["FINTECH_CRYPTO"]

        # Healthcare / MedTech
        if any(k in combined for k in [
            "health", "medical", "patient", "ehr", "emr", "fhir", "hl7", "dicom", "hipaa",
            "clinic", "hospital", "pharma", "radiology", "doctor"
        ]):
            return VERTICAL_DOMAINS["HEALTHCARE_MEDTECH"]

        # Robotics / Embedded / IoT
        if any(k in combined for k in [
            "robot", "embedded", "firmware", "iot", "rtos", "ros2", "microcontroller",
            "stm32", "esp32", "can bus", "sensor fusion", "motor control", "actuator"
        ]):
            return VERTICAL_DOMAINS["ROBOTICS_EMBEDDED"]

        # DevTools / Compilers / CLI
        if any(k in combined for k in [
            "compiler", "parser", "ast", "lexer", "transpiler", "linter", "syntax tree",
            "cli tool", "language server", "lsp", "bytecode"
        ]):
            return VERTICAL_DOMAINS["DEVTOOLS_COMPILER"]

        # AI / Machine Learning / Agent Systems
        if any(k in combined for k in [
            "llm", "agent", "rag", "vector", "embedding", "prompt", "inference",
            "langchain", "fine-tuning", "diffusion", "neural", "transformers"
        ]):
            return VERTICAL_DOMAINS["AI_ML_SYSTEMS"]

        # Default fallback: Enterprise Microservice
        return VERTICAL_DOMAINS["GENERIC_MICROSERVICE"]

    @classmethod
    def detect_language(cls, user_goal: str, profile: DomainProfile) -> str:
        """
        Detects requested programming language from user input, or falls back to profile's primary language.
        """
        goal_lower = user_goal.lower()
        if any(k in goal_lower for k in ["in python", "using python", "python3", "python code", "lang:python"]):
            return "python"
        if any(k in goal_lower for k in ["in go", "using go", "golang", "in golang", "lang:go"]):
            return "go"
        if any(k in goal_lower for k in ["in typescript", "using typescript", "in ts", "in javascript", "in js", "in node"]):
            return "typescript"
        if any(k in goal_lower for k in ["in rust", "using rust", "rustlang"]):
            return "rust"
        if any(k in goal_lower for k in ["in c++", "using c++", "cpp", "in c "]):
            return "cpp"
        return profile.primary_language

    @classmethod
    def get_agent_domain_prompt(cls, agent_role: str, profile: DomainProfile, language: Optional[str] = None) -> str:
        """
        Dynamically formats a specialized system prompt preamble for any agent in any domain,
        explicitly injecting the domain expert persona (e.g. Legal Expert, CAD Expert, etc.)
        and configuring the target programming language.
        """
        lang = language or profile.primary_language
        role_key = agent_role.lower().replace("agent", "").strip()
        role_title = profile.role_titles.get(role_key) or profile.role_titles.get(agent_role.lower()) or f"Specialized {profile.display_name} Principal"
        primitives_str = ", ".join(profile.core_primitives)
        grilling_str = "\n".join(f"  * {q}" for q in profile.grilling_dimensions)
        nfr_str = ", ".join(profile.safety_and_nfr_focus)

        return (
            f"You are operating as the [{role_title.upper()}] in the domain of [{profile.display_name.upper()}].\n"
            f"Domain Focus: {profile.category_summary}\n"
            f"Target Implementation Language: {lang.upper()}\n\n"
            f"CORE DOMAIN PRIMITIVES & CONCEPTS:\n{primitives_str}\n\n"
            f"CRITICAL DOMAIN GRILLING & ARCHITECTURAL DIMENSIONS:\n{grilling_str}\n\n"
            f"NON-NEGOTIABLE SAFETY & NFR STANDARDS:\n{nfr_str}\n"
        )

    @classmethod
    def recommend_models_for_domain(cls, profile: DomainProfile, available_providers: Optional[Dict[str, bool]] = None) -> Dict[str, str]:
        """
        Determines the optimal model for each squad role based on the domain's characteristics.
        """
        # Default recommendations
        return profile.preferred_models.copy()

