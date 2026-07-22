import asyncio
import json
import os

from dotenv import load_dotenv
from eth_account import Account
from x402 import x402Client
from x402.http import x402HTTPClient
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


async def main() -> None:
    load_dotenv()
    endpoint = _required_env("X402_PAID_ENDPOINT_URL")
    private_key = _required_env("EVM_PRIVATE_KEY")

    account = Account.from_key(private_key)
    signer = EthAccountSigner(account)

    client = x402Client()
    register_exact_evm_client(client, signer)
    http_helper = x402HTTPClient(client)

    request_body = {
        "prompt": "Create a paid login flow chart",
        "diagram_type": "mermaid",
        "format": "svg",
    }

    async with x402HttpxClient(client, timeout=90.0) as http:
        response = await http.post(endpoint, json=request_body)
        await response.aread()

        print("status", response.status_code)
        print("body", response.text[:600])

        if response.is_success:
            settle_response = http_helper.get_payment_settle_response(
                lambda name: response.headers.get(name)
            )
            print("payment_settled", json.dumps(settle_response, default=str))
        else:
            print("payment_not_settled")


if __name__ == "__main__":
    asyncio.run(main())
