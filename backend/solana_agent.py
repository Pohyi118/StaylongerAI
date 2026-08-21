import asyncio
import os
from decimal import Decimal, InvalidOperation

import httpx
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    TransferCheckedParams,
    create_associated_token_account,
    get_associated_token_address,
    transfer_checked,
)

SOLANA_DEVNET_URL = "https://api.devnet.solana.com"


def _load_agent_wallet() -> Keypair:
    private_key_hex = os.getenv("SOLANA_PRIVATE_KEY_HEX") or os.getenv("SOLANA_PRIVATE_KEY")
    if not private_key_hex:
        # Dev only: no key configured, generate ephemeral key. Has no funds,
        # so any real transfer will fail loudly rather than silently paying.
        return Keypair()

    clean = private_key_hex.strip()
    if clean.startswith("0x"):
        clean = clean[2:]
    try:
        seed = bytes.fromhex(clean)
    except ValueError as exc:
        raise ValueError(
            "SOLANA_PRIVATE_KEY_HEX is not valid hex. Provide the 64-byte private key "
            "or a 32-byte seed, not the base58 public/private format."
        ) from exc

    if len(seed) == 64:
        # Full private key bytes as exported by the Solana CLI.
        return Keypair.from_bytes(seed)
    if len(seed) == 32:
        return Keypair.from_seed(seed)
    raise ValueError(
        f"SOLANA_PRIVATE_KEY_HEX must be 32 (seed) or 64 (private key) bytes, got {len(seed)}."
    )


class LocalSolanaAgent:
    def __init__(self):
        self.rpc_url = os.getenv("SOLANA_RPC_URL", SOLANA_DEVNET_URL)
        self.client = AsyncClient(self.rpc_url, timeout=30)
        self.usdc_mint = os.getenv("USDC_MINT")
        self.x402_url = os.getenv("X402_PAYMENT_URL")
        self.payment_recipient = os.getenv("PAYMENT_RECIPIENT_WALLET")

        raw_reward = os.getenv("REWARD_USDC_AMOUNT", "50")
        try:
            self.default_reward_usdc = Decimal(raw_reward)
        except InvalidOperation as exc:
            raise ValueError(f"REWARD_USDC_AMOUNT is not a valid decimal: {raw_reward!r}") from exc

        self.agent_wallet = _load_agent_wallet()

    async def close(self):
        await self.client.close()

    def _safe_pubkey(self, value: str) -> Pubkey:
        if not value:
            raise ValueError("Wallet/PublicKey value is missing.")
        return Pubkey.from_string(value)

    async def _get_latest_blockhash(self):
        response = await self.client.get_latest_blockhash()
        return response.value.blockhash

    async def _confirm_sent(self, signature):
        # Wait for confirmed finality; raises if the transaction is dropped,
        # so callers never report "processed" for a failed broadcast.
        await self.client.confirm_transaction(signature, commitment="confirmed")

    async def _send_transaction(self, instruction):
        recent_blockhash = await self._get_latest_blockhash()
        message = Message([instruction], self.agent_wallet.pubkey())
        transaction = Transaction([self.agent_wallet], message, recent_blockhash)
        last_error = None
        for attempt in range(3):
            try:
                result = await self.client.send_transaction(transaction)
                signature = result.value
                await self._confirm_sent(signature)
                return signature
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"Solana RPC transaction failed after retries: {last_error}")

    async def execute_reward_micropayment(
        self,
        recipient_address: str,
        amount_usdc: float | Decimal = None,
        payment_reference: str | None = None,
    ):
        """Pay a reward. USDC preferred; SOL fallback is devnet-only and gated."""
        if amount_usdc is None:
            amount_usdc = self.default_reward_usdc

        try:
            adjusted_amount = Decimal(str(amount_usdc))
        except InvalidOperation as exc:
            raise ValueError(f"Invalid payment amount: {amount_usdc!r}") from exc

        if adjusted_amount <= 0:
            raise ValueError("Invalid payment amount: must be positive")

        if self.usdc_mint:
            return await self.execute_usdc_transfer(
                recipient_address, adjusted_amount, payment_reference
            )

        # SOL fallback is unsafe on mainnet: it pays SOL 1:1 as USD (no price
        # conversion). Hard-gate to devnet unless explicitly enabled for a demo.
        is_devnet = "devnet" in self.rpc_url
        allow_fallback = os.getenv("ALLOW_SOL_FALLBACK", "0") == "1"
        if not (is_devnet and allow_fallback):
            raise RuntimeError(
                "USDC_MINT is not configured and SOL fallback is disabled "
                "(set USDC_MINT, or ALLOW_SOL_FALLBACK=1 while pointing at devnet)."
            )

        return await self.pay_sol(recipient_address, adjusted_amount, payment_reference)

    async def pay_sol(self, recipient_address: str, amount_unconverted: Decimal, payment_reference: str | None = None):
        recipient = self._safe_pubkey(recipient_address)
        # MilliSOL for devnet demo; not a USD price conversion.
        lamports = int((amount_unconverted * Decimal("1_000_000")).to_integral_value())
        if lamports <= 0:
            raise ValueError("Invalid payment amount")

        ix = transfer(
            TransferParams(
                from_pubkey=self.agent_wallet.pubkey(),
                to_pubkey=recipient,
                lamports=lamports,
            )
        )
        signature = await self._send_transaction(ix)
        return {
            "status": "processed",
            "network": self.rpc_url,
            "asset": "SOL",
            "amount_usd_label": str(amount_unconverted),
            "amount_sol_millis": str(amount_unconverted),
            "signature": str(signature),
            "reference": payment_reference,
            "warning": "DEVNET_ONLY_NO_PRICE_CONVERSION",
        }

    async def execute_usdc_transfer(self, recipient_address: str, amount_usdc: Decimal, payment_reference: str | None = None):
        if not self.usdc_mint:
            raise ValueError("USDC_MINT is not configured.")

        mint = Pubkey.from_string(self.usdc_mint)
        recipient = self._safe_pubkey(recipient_address)
        owner = self.agent_wallet.pubkey()

        source_ata = get_associated_token_address(owner, mint, TOKEN_PROGRAM_ID)
        dest_ata = get_associated_token_address(recipient, mint, TOKEN_PROGRAM_ID)

        create_ata_ix = create_associated_token_account(owner, recipient, mint, TOKEN_PROGRAM_ID)
        transfer_amount = int((amount_usdc * Decimal("1_000_000")).to_integral_value())

        transfer_ix = transfer_checked(
            TransferCheckedParams(
                program_id=TOKEN_PROGRAM_ID,
                source=source_ata,
                mint=mint,
                dest=dest_ata,
                owner=owner,
                amount=transfer_amount,
                decimals=6,
                signers=[],
            )
        )

        recent_blockhash = await self._get_latest_blockhash()
        message = Message([create_ata_ix, transfer_ix], owner)
        tx = Transaction([self.agent_wallet], message, recent_blockhash)
        result = await self.client.send_transaction(tx)
        signature = result.value
        await self._confirm_sent(signature)

        return {
            "status": "processed",
            "network": self.rpc_url,
            "asset": "USDC",
            "amount": str(amount_usdc),
            "signature": str(signature),
            "reference": payment_reference,
            "mint": self.usdc_mint,
        }

    async def request_x402_payment(self, payment_url: str, amount_usdc: float | Decimal = None, recipient_address: str | None = None):
        """x402 flow: hit API, settle on HTTP 402, then retry."""
        if not payment_url:
            raise ValueError("X402_PAYMENT_URL is not configured.")

        target_wallet = recipient_address or self.payment_recipient
        if not target_wallet:
            raise ValueError("No recipient wallet was supplied for the x402 payment.")

        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            first = await client.get(payment_url, headers=headers, follow_redirects=False)

            if first.status_code != 402:
                return {
                    "status": "not_required",
                    "status_code": first.status_code,
                    "body": first.text,
                }

            settlement = await self.execute_reward_micropayment(
                recipient_address=target_wallet,
                amount_usdc=amount_usdc if amount_usdc is not None else self.default_reward_usdc,
                payment_reference=f"x402:{payment_url}",
            )

            retry = await client.get(
                payment_url,
                headers={**headers, "X-Payment-Status": "settled"},
                follow_redirects=False,
            )

            return {
                "status": "settled",
                "payment": settlement,
                "retry_status_code": retry.status_code,
                "retry_body": retry.text,
            }