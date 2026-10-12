"""Validated product context for reusable ASCM GTM workflows.

Configuration is loaded from .ascm_product.json in the project root. Missing fields
stay explicitly generic rather than silently assuming a particular product or ICP.
"""
import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import List


@dataclass
class ProductContext:
    product_name: str = "Unconfigured product"
    product_thesis: str = "Product thesis not configured; ask the founder to define the problem and value proposition."
    icp_description: str = "Ideal customer profile not configured; validate the target user before outreach."
    milestone_name: str = "Unspecified milestone"
    domain_keywords: List[str] = field(default_factory=list)
    sender_name: str = "Founder"
    tone: str = "Clear, candid, evidence-based"
    goals: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, project_path: Path) -> "ProductContext":
        """Load a project-local JSON config, optionally overridden by a config path env var."""
        config_path = Path(os.getenv("ASCM_PRODUCT_CONFIG", str(project_path / ".ascm_product.json")))
        if not config_path.is_absolute():
            config_path = project_path / config_path
        if not config_path.exists():
            return cls()
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read product config {config_path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Product config must be a JSON object")
        allowed = {item.name for item in fields(cls)}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"Unknown product config fields: {', '.join(sorted(unknown))}")
        for key in ("product_name", "product_thesis", "icp_description", "milestone_name", "sender_name", "tone"):
            if key in payload and (not isinstance(payload[key], str) or not payload[key].strip()):
                raise ValueError(f"{key} must be a non-empty string")
        for key in ("domain_keywords", "channels", "goals"):
            if key in payload and (not isinstance(payload[key], list) or any(not isinstance(v, str) or not v.strip() for v in payload[key])):
                raise ValueError(f"{key} must be a list of non-empty strings")
        return cls(**payload)
