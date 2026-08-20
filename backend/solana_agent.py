import os
from decimal import Decimal

import httpx
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import create_associated_token_account, get_associated_token_address, transfer_checked
from spl.token.models import TransferCheckedParams

SOLANA_DEVNET_URL = "https://api.devnet.solana.com"

class LocalSolanaAgent:
    def __init__(self):
        self.rpc_url = os.getenv("SOLANA_RPC_URL", SOLANA_DEVNET_URL)
        self.client = AsyncClient(self.rpc_url)

        self.usdc_mint = os.getenv("USDC_MINT")
        self.x402_url = os.getenv("X402_PAYMENT_URL")
        self.payment_recipient = os.getenv("PAYMENT_RECIPIENT_WALLET")
        self.default_reward_usdc = Decimal(os.getenv("REWARD_USDC_AMOUNT", "50"))

        private_key_hex = os.getenv("SOLANA_PRIVATE_KEY_HEX") or os.getenv("SOLANA_PRIVATE_KEY")
        if private_key_hex:
            clean = private_key_hex.strip()
            if clean.startswith("0x"):
                clean = clean[2:]
            seed = bytes.fromhex(clean)
            self.agent_wallet = Keypair.from_seed(seed)
        else:
            self.agent_wallet = Keypair()

    def _safe_pubkey(self, value: str) -> Pubkey:
        if not value:
            raise ValueError("Wallet/PublicKey value is missing.")
        return Pubkey.from_string(value)

    async def _get_latest_blockhash(self):
        response = await self.client.get_latest_blockhash()
        return response.value.blockhash

    async def _send_transaction(self, instruction):
        recent_blockhash = await self._get_latest_blockhash()
        message = Message([instruction], self.agent_wallet.pubkey())
        transaction = Transaction([self.agent_wallet], message, recent_blockhash)
        result = await self.client.send_transaction(transaction)
        return result

    async def execute_reward_micropayment(
        self,
        recipient_address: str,
        amount_usdc: float | Decimal = None,
        payment_reference: str | None = None,
    ):
        """
        Real Solana payment flow: prefer USDC on the configured SPL mint if available,
        otherwise fall back to SOL lamports. This supports the x402 payment style
        described in the architecture brief.
        """
        if amount_usdc is None:
            amount_usdc = self.default_reward_usdc

        adjusted_amount = Decimal(str(amount_usdc)) if isinstance(amount_usdc, str) else Decimal(amount_usdc)

        if self.usdc_mint:
            try:
                return await self.execute_usdc_transfer(recipient_address, adjusted_amount, payment_reference)
            except Exception as exc:
                print(f"USDC transfer failed, falling back to SOL: {exc}")

        recipient = self._safe_pubkey(recipient_address)
        lamports = int(adjusted_amount * Decimal("1_000_000_000")) if adjusted_amount > 0 else 0

        ix = transfer(
            TransferParams(
                from_pubkey=self.agent_wallet.pubkey(),
                to_pubkey=recipient,
                lamports=lamports,
            )
        )

        result = await self._send_transaction(ix)
        return {
            "status": "processed",
            "network": self.rpc_url,
            "asset": "SOL",
            "amount": str(adjusted_amount),
            "signature": str(result.value),
            "reference": payment_reference,
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

        return {
            "status": "processed",
            "network": self.rpc_url,
            "asset": "USDC",
            "amount": str(amount_usdc),
            "signature": str(result.value),
            "reference": payment_reference,
            "mint": self.usdc_mint,
        }

    async def request_x402_payment(self, payment_url: str, amount_usdc: float | Decimal = None, recipient_address: str | None = None):
        """
        A real x402-style flow is: a protected HTTP API responds with HTTP 402,
        then the agent settles a payment and retries the request.
        """
        if not payment_url:
            raise ValueError("X402_PAYMENT_URL is not configured.")

        target_wallet = recipient_address or self.payment_recipient
        if not target_wallet:
            raise ValueError("No recipient wallet was supplied for the x402 payment.")

        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient() as client:
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

            retry = await client.get(payment_url, headers={**headers, "X-Payment-Status": "settled"}, follow_redirects=False)

            return {
                "status": "settled",
                "payment": settlement,
                "retry_status_code": retry.status_code,
                "retry_body": retry.text,
            }
