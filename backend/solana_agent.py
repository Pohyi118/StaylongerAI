import logging
import os
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx


logger = logging.getLogger(__name__)

SOLANA_DEVNET_URL = "https://api.devnet.solana.com"
USDC_DECIMALS = 6

# Solana support is optional for the local demo. Keep these imports isolated so
# a machine without the native solders/Solana packages can still start FastAPI.
SOLANA_IMPORT_ERROR: str | None = None
try:
    from solana.rpc.async_api import AsyncClient
    from solders.keypair import Keypair
    from solders.message import Message
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    from spl.token.constants import TOKEN_PROGRAM_ID
    from spl.token.instructions import (
        TransferCheckedParams,
        create_associated_token_account,
        get_associated_token_address,
        transfer_checked,
    )

    try:
        from spl.token.instructions import create_idempotent_associated_token_account
    except ImportError:  # Older compatible spl-token releases.
        create_idempotent_associated_token_account = None

    SOLANA_PACKAGES_AVAILABLE = True
except Exception as exc:  # ImportError plus native-extension load failures.
    SOLANA_PACKAGES_AVAILABLE = False
    SOLANA_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
    AsyncClient = None
    Keypair = None
    Message = None
    Pubkey = None
    Transaction = None
    TOKEN_PROGRAM_ID = None
    TransferCheckedParams = None
    create_associated_token_account = None
    create_idempotent_associated_token_account = None
    get_associated_token_address = None
    transfer_checked = None


def _env_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


class LocalSolanaAgent:
    """USDC reward agent with an explicit, non-transactional demo mode."""

    def __init__(self):
        self.rpc_url = (os.getenv("SOLANA_RPC_URL") or SOLANA_DEVNET_URL).strip()
        self.usdc_mint = (os.getenv("USDC_MINT") or "").strip() or None
        self.x402_url = (os.getenv("X402_PAYMENT_URL") or "").strip() or None
        self.payment_recipient = (
            (os.getenv("PAYMENT_RECIPIENT_WALLET") or "").strip() or None
        )
        self.live_requested = _env_flag("SOLANA_LIVE_MODE")
        self._configuration_errors: list[str] = []
        self.agent_wallet = None
        self.client = None

        self.default_reward_usdc = self._load_default_amount()

        if not SOLANA_PACKAGES_AVAILABLE:
            self._configuration_errors.append(
                "Optional Solana packages are unavailable."
            )
        else:
            self.agent_wallet = self._load_wallet()
            self._validate_configured_pubkey(self.usdc_mint, "USDC_MINT")
            self._validate_configured_pubkey(
                self.payment_recipient,
                "PAYMENT_RECIPIENT_WALLET",
            )

        self.configured = not self._configuration_errors
        self.live_enabled = self.live_requested and self.configured

        if self.live_enabled:
            try:
                self.client = AsyncClient(self.rpc_url)
            except Exception:
                # Invalid RPC configuration must not make backend import fail.
                self._configuration_errors.append(
                    "SOLANA_RPC_URL could not initialize a Solana client."
                )
                self.configured = False
                self.live_enabled = False

    def _load_default_amount(self) -> Decimal:
        raw_amount = os.getenv("REWARD_USDC_AMOUNT", "50")
        try:
            amount = Decimal(raw_amount)
            if not amount.is_finite() or amount <= 0:
                raise InvalidOperation
            return amount
        except (InvalidOperation, TypeError, ValueError):
            self._configuration_errors.append(
                "REWARD_USDC_AMOUNT must be a positive number."
            )
            return Decimal("50")

    def _load_wallet(self):
        private_key_hex = os.getenv("SOLANA_PRIVATE_KEY_HEX") or os.getenv(
            "SOLANA_PRIVATE_KEY"
        )
        if not private_key_hex:
            self._configuration_errors.append("Solana private key is missing.")
            return None

        try:
            clean = private_key_hex.strip()
            if clean.lower().startswith("0x"):
                clean = clean[2:]
            key_bytes = bytes.fromhex(clean)

            if len(key_bytes) == 32:
                return Keypair.from_seed(key_bytes)
            if len(key_bytes) == 64:
                return Keypair.from_bytes(key_bytes)

            raise ValueError("expected a 32-byte seed or 64-byte key")
        except Exception:
            # Never include key material in the error or logs.
            self._configuration_errors.append(
                "Solana private key is invalid; expected 32-byte or 64-byte hex."
            )
            return None

    def _validate_configured_pubkey(self, value: str | None, field_name: str) -> None:
        if not value:
            self._configuration_errors.append(f"{field_name} is missing.")
            return
        try:
            Pubkey.from_string(value)
        except Exception:
            self._configuration_errors.append(f"{field_name} is invalid.")

    def _status_reason(self) -> str:
        if self._configuration_errors:
            return " ".join(self._configuration_errors)
        if not self.live_requested:
            return "SOLANA_LIVE_MODE is disabled; payments are simulated."
        return "Live USDC payments are enabled."

    def get_status(self) -> dict[str, Any]:
        """Return the stable payment configuration contract used by the UI/API."""
        return {
            "mode": "live" if self.live_enabled else "demo",
            "configured": self.configured,
            "network": self.rpc_url,
            "asset": "USDC",
            "defaultAmount": float(self.default_reward_usdc),
            "reason": self._status_reason(),
        }

    def configuration_status(self) -> dict[str, Any]:
        """Compatibility alias for callers that prefer a descriptive method name."""
        return self.get_status()

    @staticmethod
    def _parse_amount(amount_usdc: float | Decimal | str) -> Decimal:
        try:
            amount = Decimal(str(amount_usdc))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("Reward amount must be a valid number.") from exc

        if not amount.is_finite() or amount <= 0:
            raise ValueError("Reward amount must be greater than zero.")
        return amount

    def _demo_payment_result(
        self,
        amount_usdc: Decimal,
        payment_reference: str | None,
    ) -> dict[str, Any]:
        return {
            "status": "demo",
            "mode": "demo",
            "configured": self.configured,
            "network": self.rpc_url,
            "asset": "USDC",
            "amount": str(amount_usdc),
            "signature": None,
            "reference": payment_reference,
            "simulated": True,
            "reason": self._status_reason(),
        }

    def _safe_pubkey(self, value: str | None):
        if not value:
            raise ValueError("Wallet/PublicKey value is missing.")
        if not SOLANA_PACKAGES_AVAILABLE:
            raise RuntimeError("Optional Solana packages are unavailable.")
        try:
            return Pubkey.from_string(value)
        except Exception as exc:
            raise ValueError("Wallet/PublicKey value is invalid.") from exc

    async def _get_latest_blockhash(self):
        if self.client is None:
            raise RuntimeError("Live Solana client is not available.")
        response = await self.client.get_latest_blockhash()
        return response.value.blockhash

    async def execute_reward_micropayment(
        self,
        recipient_address: str,
        amount_usdc: float | Decimal | str | None = None,
        payment_reference: str | None = None,
    ) -> dict[str, Any]:
        """
        Submit a USDC reward only when live mode is explicitly and fully enabled.

        Missing packages/configuration or a disabled live flag returns a truthful
        demo result. A failed live USDC transfer never falls back to SOL.
        """
        adjusted_amount = self._parse_amount(
            self.default_reward_usdc if amount_usdc is None else amount_usdc
        )

        if not self.live_enabled:
            return self._demo_payment_result(adjusted_amount, payment_reference)

        try:
            return await self.execute_usdc_transfer(
                recipient_address,
                adjusted_amount,
                payment_reference,
            )
        except Exception as exc:
            logger.error(
                "Live USDC reward transfer failed; no SOL fallback was attempted (%s).",
                type(exc).__name__,
            )
            raise RuntimeError(
                "Live USDC reward transfer failed; no fallback transaction was attempted."
            ) from exc

    async def execute_usdc_transfer(
        self,
        recipient_address: str,
        amount_usdc: Decimal | float | str,
        payment_reference: str | None = None,
    ) -> dict[str, Any]:
        adjusted_amount = self._parse_amount(amount_usdc)
        if not self.live_enabled:
            return self._demo_payment_result(adjusted_amount, payment_reference)
        if not self.usdc_mint or self.agent_wallet is None or self.client is None:
            return self._demo_payment_result(adjusted_amount, payment_reference)

        mint = self._safe_pubkey(self.usdc_mint)
        recipient = self._safe_pubkey(recipient_address)
        owner = self.agent_wallet.pubkey()

        source_ata = get_associated_token_address(owner, mint)
        dest_ata = get_associated_token_address(recipient, mint)

        transfer_units = adjusted_amount * (Decimal(10) ** USDC_DECIMALS)
        if transfer_units != transfer_units.to_integral_value():
            raise ValueError(
                f"USDC amount supports at most {USDC_DECIMALS} decimal places."
            )

        instructions = []
        if create_idempotent_associated_token_account is not None:
            instructions.append(
                create_idempotent_associated_token_account(
                    owner,
                    recipient,
                    mint,
                )
            )
        else:
            # Compatibility path for older spl-token packages: create only when
            # the destination associated token account does not already exist.
            destination_account = await self.client.get_account_info(dest_ata)
            if destination_account.value is None:
                instructions.append(
                    create_associated_token_account(
                        owner,
                        recipient,
                        mint,
                    )
                )

        instructions.append(
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=source_ata,
                    mint=mint,
                    dest=dest_ata,
                    owner=owner,
                    amount=int(transfer_units),
                    decimals=USDC_DECIMALS,
                    signers=[],
                )
            )
        )

        recent_blockhash = await self._get_latest_blockhash()
        message = Message(instructions, owner)
        transaction = Transaction([self.agent_wallet], message, recent_blockhash)
        result = await self.client.send_transaction(transaction)

        return {
            "status": "processed",
            "mode": "live",
            "configured": True,
            "network": self.rpc_url,
            "asset": "USDC",
            "amount": str(adjusted_amount),
            "signature": str(result.value),
            "reference": payment_reference,
            "mint": self.usdc_mint,
            "simulated": False,
        }

    async def request_x402_payment(
        self,
        payment_url: str,
        amount_usdc: float | Decimal | str | None = None,
        recipient_address: str | None = None,
    ) -> dict[str, Any]:
        """
        Request an x402-style resource, use the safe reward payment path on 402,
        and retry with an honest settled/simulated payment status.
        """
        if not payment_url:
            raise ValueError("X402_PAYMENT_URL is not configured.")

        target_wallet = recipient_address or self.payment_recipient
        if not target_wallet:
            raise ValueError("No recipient wallet was supplied for the x402 payment.")

        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            first = await client.get(
                payment_url,
                headers=headers,
                follow_redirects=False,
            )

            if first.status_code != 402:
                return {
                    "status": "not_required",
                    "status_code": first.status_code,
                    "body": first.text,
                }

            settlement = await self.execute_reward_micropayment(
                recipient_address=target_wallet,
                amount_usdc=(
                    amount_usdc
                    if amount_usdc is not None
                    else self.default_reward_usdc
                ),
                payment_reference=f"x402:{payment_url}",
            )
            payment_status = (
                "settled" if settlement.get("status") == "processed" else "simulated"
            )

            retry = await client.get(
                payment_url,
                headers={**headers, "X-Payment-Status": payment_status},
                follow_redirects=False,
            )

            return {
                "status": "settled" if payment_status == "settled" else "demo",
                "payment": settlement,
                "retry_status_code": retry.status_code,
                "retry_body": retry.text,
            }

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()
