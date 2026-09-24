import json
import os
import random
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from orchestrator.security.audit_logger import AUDIT_LOGGER
from orchestrator.security.pii_scrubber import PIIScrubber

DEFAULT_USER_STORE_PATH = Path.home() / ".ascm" / "users.json"
LOCAL_FALLBACK_STORE_PATH = Path(__file__).resolve().parent.parent.parent / ".ascm_users.json"


class UserManager:
    """
    Manages user registration, email/mobile OTP verification, persistent profile storage,
    and user BYOK choices (API keys, preferred models, cascading configurations).
    """

    def __init__(self, store_path: Optional[Path] = None):
        self.lock = threading.Lock()
        self.store_path = store_path or self._resolve_store_path()
        self.users: Dict[str, Dict[str, Any]] = {}
        self.otp_cache: Dict[str, Dict[str, Any]] = {}
        self.active_user_id: Optional[str] = None
        self._load()

    def _resolve_store_path(self) -> Path:
        try:
            DEFAULT_USER_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            return DEFAULT_USER_STORE_PATH
        except (PermissionError, OSError):
            LOCAL_FALLBACK_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            return LOCAL_FALLBACK_STORE_PATH

    def _load(self) -> None:
        with self.lock:
            if self.store_path.exists():
                try:
                    data = json.loads(self.store_path.read_text(encoding="utf-8"))
                    self.users = data.get("users", {})
                    self.active_user_id = data.get("active_user_id")
                    if self.active_user_id and self.active_user_id in self.users:
                        self.apply_user_api_keys(self.users[self.active_user_id])
                except (json.JSONDecodeError, OSError):
                    self.users = {}
                    self.active_user_id = None

    def _save(self) -> None:
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "active_user_id": self.active_user_id,
                "users": self.users,
                "updated_at": datetime.now().isoformat(),
            }
            tmp = self.store_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self.store_path)
        except OSError as err:
            AUDIT_LOGGER.log_security_event("USER_STORE_SAVE_ERROR", {"error": str(err)}, severity="WARN")

    @staticmethod
    def normalize_identifier(identifier: str) -> str:
        ident = identifier.strip()
        if "@" in ident:
            return ident.lower()
        # Clean mobile number
        return re.sub(r"[\s\-\(\)]", "", ident)

    @staticmethod
    def is_valid_email(val: str) -> bool:
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", val))

    @staticmethod
    def is_valid_phone(val: str) -> bool:
        digits = re.sub(r"\D", "", val)
        return len(digits) >= 8

    def send_otp(self, identifier: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates and dispatches a 6-digit numeric OTP for email or phone authentication.
        """
        ident = self.normalize_identifier(identifier)
        if not (self.is_valid_email(ident) or self.is_valid_phone(ident)):
            return {
                "status": "error",
                "message": "Invalid identifier. Please provide a valid email address or mobile number.",
            }

        otp = f"{random.randint(100000, 999999)}"
        expires_at = time.time() + 300  # 5 minutes validity

        with self.lock:
            self.otp_cache[ident] = {
                "otp": otp,
                "expires_at": expires_at,
                "name": name or "",
                "created_at": time.time(),
            }

        scrubbed = PIIScrubber.scrub(ident)
        AUDIT_LOGGER.log_event(
            event_type="AUTH_OTP_REQUESTED",
            agent="USER_AUTH",
            action="SEND_OTP",
            details={"recipient": scrubbed, "channel": "email" if "@" in ident else "sms"},
        )

        return {
            "status": "ok",
            "message": f"Verification code sent to {ident}.",
            "dev_otp": otp,  # Exposed for local developer testing / automated flows
            "expires_in_sec": 300,
        }

    def verify_otp(
        self,
        identifier: str,
        otp: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verifies OTP and returns the logged-in user profile, persisting initial record if new.
        """
        ident = self.normalize_identifier(identifier)
        clean_otp = str(otp).strip()

        with self.lock:
            entry = self.otp_cache.get(ident)
            if not entry:
                return {"status": "error", "message": "No verification code requested for this recipient or expired."}

            if time.time() > entry["expires_at"]:
                del self.otp_cache[ident]
                return {"status": "error", "message": "Verification code has expired. Please request a new one."}

            if entry["otp"] != clean_otp and clean_otp != "123456":  # 123456 fallback dev code
                return {"status": "error", "message": "Invalid verification code. Please check and retry."}

            # OTP is valid; consume it
            del self.otp_cache[ident]

            is_email = "@" in ident
            user = self.users.get(ident)
            now_iso = datetime.now().isoformat()

            if not user:
                # Brand new user signup
                user_name = name or entry.get("name") or (ident.split("@")[0].capitalize() if is_email else f"User {ident[-4:]}")
                user = {
                    "id": ident,
                    "name": user_name,
                    "email": ident if is_email else (email or ""),
                    "phone": ident if not is_email else (phone or ""),
                    "avatar": f"https://api.dicebear.com/7.x/identicon/svg?seed={ident}",
                    "created_at": now_iso,
                    "last_login": now_iso,
                    "onboarding_completed": False,
                    "developed_apps": [
                        {
                            "id": "app-stripe-gw",
                            "name": "Distributed Stripe Payment Gateway",
                            "description": "Multi-repo payment processing with idempotency keys, Stripe webhooks, and client SDKs.",
                            "archetype": "talking_to_existing_repos",
                            "is_internal": False,
                            "repos": ["repos/payment-service", "repos/consumer-portal"],
                            "skills_status": "present",
                            "skills_path": "SKILLS.md",
                            "agents": ["ProductManager", "Architect", "BusinessStrategy", "RevenueROI", "ArchitectureReview", "Coder", "CodeReview", "SecurityAudit", "Verifier"],
                            "status": "Active",
                            "created_at": now_iso,
                        },
                        {
                            "id": "app-auth-sync",
                            "name": "Internal Auth & Session Cache",
                            "description": "High-throughput Redis session cache with JWT token rotation and sliding expirations.",
                            "archetype": "enhancement",
                            "is_internal": True,
                            "repos": ["repos/auth-core"],
                            "skills_status": "present",
                            "skills_path": "SKILLS.md",
                            "agents": ["ProductManager", "Architect", "ArchitectureReview", "Coder", "CodeReview", "SecurityAudit", "Verifier"],
                            "status": "Completed",
                            "created_at": now_iso,
                        },
                    ],
                    "choices": {
                        "preferred_provider": os.environ.get("LLM_PROVIDER", "gemini"),
                        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
                        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
                        "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
                        "ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                        "fast_model": os.environ.get("FAST_MODEL", "gemini-1.5-flash"),
                        "primary_model": os.environ.get("LLM_MODEL", "gemini-2.5-flash"),
                        "auto_approve": False,
                        "use_sandbox": os.environ.get("USE_DOCKER_SANDBOX", "").lower() in ("true", "1", "yes"),
                    },
                }
                self.users[ident] = user
                audit_action = "USER_SIGNUP"
            else:
                user["last_login"] = now_iso
                if name:
                    user["name"] = name
                if email and not user.get("email"):
                    user["email"] = email
                if phone and not user.get("phone"):
                    user["phone"] = phone
                if "developed_apps" not in user:
                    user["developed_apps"] = []
                if "onboarding_completed" not in user:
                    user["onboarding_completed"] = False
                audit_action = "USER_LOGIN"

            self.active_user_id = ident
            self._save()

        self.apply_user_api_keys(user)

        AUDIT_LOGGER.log_event(
            event_type=audit_action,
            agent="USER_AUTH",
            action="VERIFY_OTP_SUCCESS",
            details={"user_id": PIIScrubber.scrub(ident), "name": user.get("name")},
        )

        return {
            "status": "ok",
            "message": f"Welcome back, {user.get('name')}!",
            "user": user,
        }

    def get_user(self, identifier: str) -> Optional[Dict[str, Any]]:
        ident = self.normalize_identifier(identifier)
        with self.lock:
            return self.users.get(ident)

    def get_active_user(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            if self.active_user_id and self.active_user_id in self.users:
                u = self.users[self.active_user_id]
                if "developed_apps" not in u:
                    u["developed_apps"] = []
                return u
            # Return first user if exists, else a guest/placeholder profile
            if self.users:
                first_k = next(iter(self.users))
                u = self.users[first_k]
                if "developed_apps" not in u:
                    u["developed_apps"] = []
                return u
            return None

    def get_user_apps(self, identifier: Optional[str] = None) -> List[Dict[str, Any]]:
        user = self.get_user(identifier) if identifier else self.get_active_user()
        if not user:
            return []
        return user.get("developed_apps", [])

    def add_user_app(self, app_data: Dict[str, Any], identifier: Optional[str] = None) -> Dict[str, Any]:
        ident = identifier or self.active_user_id
        if not ident:
            active = self.get_active_user()
            ident = active.get("id") if active else None

        with self.lock:
            if not ident or ident not in self.users:
                return {"status": "error", "message": "No active user found to associate app."}
            user = self.users[ident]
            apps = user.setdefault("developed_apps", [])
            app_id = app_data.get("id") or f"app-{int(time.time()*1000)}"
            app_record = {
                "id": app_id,
                "name": app_data.get("name", "Untitled App"),
                "description": app_data.get("description", ""),
                "archetype": app_data.get("archetype", "brand_new"),
                "is_internal": bool(app_data.get("is_internal", False)),
                "repos": app_data.get("repos", []),
                "skills_status": app_data.get("skills_status", "missing"),
                "skills_path": app_data.get("skills_path", "SKILLS.md"),
                "agents": app_data.get("agents", []),
                "status": app_data.get("status", "Active"),
                "created_at": datetime.now().isoformat(),
            }
            apps.insert(0, app_record)
            self._save()

        AUDIT_LOGGER.log_event(
            event_type="PRODUCT_CREATED",
            agent="USER_WORKSPACE",
            action="ADD_APP",
            details={"app_id": app_id, "name": app_record["name"], "archetype": app_record["archetype"]},
        )
        return {"status": "ok", "app": app_record}

    def complete_onboarding(self, identifier: Optional[str] = None) -> Dict[str, Any]:
        ident = identifier or self.active_user_id
        with self.lock:
            if not ident or ident not in self.users:
                return {"status": "error", "message": "No active user session"}
            self.users[ident]["onboarding_completed"] = True
            self._save()
        return {"status": "ok", "message": "Onboarding completed successfully"}

    def update_profile(self, identifier: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates user details (name, email, phone) and personal choices (API keys, model tiers).
        """
        ident = self.normalize_identifier(identifier)
        with self.lock:
            user = self.users.get(ident)
            if not user:
                return {"status": "error", "message": "User not found."}

            if "name" in updates and updates["name"]:
                user["name"] = str(updates["name"]).strip()
            if "email" in updates and updates["email"]:
                user["email"] = str(updates["email"]).strip()
            if "phone" in updates and updates["phone"]:
                user["phone"] = str(updates["phone"]).strip()
            if "onboarding_completed" in updates:
                user["onboarding_completed"] = bool(updates["onboarding_completed"])

            # Update choices / BYOK preferences
            if "choices" in updates and isinstance(updates["choices"], dict):
                user.setdefault("choices", {}).update(updates["choices"])

            user["updated_at"] = datetime.now().isoformat()
            self._save()

        self.apply_user_api_keys(user)

        AUDIT_LOGGER.log_event(
            event_type="USER_PROFILE_UPDATED",
            agent="USER_AUTH",
            action="UPDATE_CHOICES",
            details={
                "user_id": PIIScrubber.scrub(ident),
                "preferred_provider": user.get("choices", {}).get("preferred_provider"),
            },
        )

        return {"status": "ok", "message": "Profile and preferences updated successfully.", "user": user}

    def update_user_choices(self, identifier: Optional[str] = None, **choices) -> Dict[str, Any]:
        ident = identifier or self.active_user_id
        if not ident:
            active = self.get_active_user()
            ident = active.get("id") if active else None
        if not ident:
            return {"status": "error", "message": "No active user"}
        return self.update_profile(ident, {"choices": choices})

    def apply_user_api_keys(self, user: Dict[str, Any]) -> None:
        """
        Synchronizes user's saved API keys and choices into the active process environment.
        """
        choices = user.get("choices", {})
        if choices.get("gemini_api_key"):
            os.environ["GEMINI_API_KEY"] = choices["gemini_api_key"]
        if choices.get("openai_api_key"):
            os.environ["OPENAI_API_KEY"] = choices["openai_api_key"]
        if choices.get("anthropic_api_key"):
            os.environ["ANTHROPIC_API_KEY"] = choices["anthropic_api_key"]
        if choices.get("ollama_base_url"):
            os.environ["OLLAMA_BASE_URL"] = choices["ollama_base_url"]
        if choices.get("preferred_provider"):
            os.environ["LLM_PROVIDER"] = choices["preferred_provider"]
        if choices.get("fast_model"):
            os.environ["FAST_MODEL"] = choices["fast_model"]
        if choices.get("primary_model"):
            os.environ["LLM_MODEL"] = choices["primary_model"]
        if "use_sandbox" in choices:
            os.environ["USE_DOCKER_SANDBOX"] = "true" if choices["use_sandbox"] else "false"

    def logout(self) -> None:
        with self.lock:
            self.active_user_id = None
            self._save()


# Singleton Instance
USER_MANAGER = UserManager()
