# app/services/siwf.py
from __future__ import annotations

import re
from typing import Any

from siwe import SiweMessage, DomainMismatch, NonceMismatch, ExpiredMessage
from web3 import Web3
from app.core.config import settings

# Farcaster ID Registry lives on Optimism (chainId 10)
EXPECTED_CHAIN_ID = 10

w3 = Web3(Web3.HTTPProvider(settings.OPTIMISM_RPC_URL, request_kwargs={"timeout": 15}))
ID_REGISTRY = w3.eth.contract(
    address=Web3.to_checksum_address(settings.ID_REGISTRY_ADDRESS),
    abi=[
        {
            "inputs": [{"internalType": "uint256", "name": "fid", "type": "uint256"}],
            "name": "custodyOf",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        }
    ],
)

def expected_domain() -> str:
    # MUST match the first line of SIWE exactly: "{domain} wants you to sign in…"
    # e.g. "www.glaria.xyz"
    return settings.expected_domain()

def parse_fid_from_resources(resources: list[str] | None) -> int | None:
    """Accept common SIWF resource forms."""
    if not resources:
        return None
    patterns = [
        r"^farcaster://fids?/(\d+)$",       # farcaster://fid/123 | farcaster://fids/123
        r"^fc://fid/(\d+)$",                # fc://fid/123
        r"^farcaster://user\?id=(\d+)$",    # farcaster://user?id=123
    ]
    for raw in resources:
        s = raw.strip()
        for pat in patterns:
            m = re.match(pat, s)
            if m:
                return int(m.group(1))
    return None

def _load_siwe_model(raw: str) -> SiweMessage:
    """
    Cope with different `siwe` versions:
    - First try keyword constructor (pydantic style)
    - Then try known classmethods
    - Finally try positional constructor
    """
    # 1) keyword constructor
    try:
        return SiweMessage(message=raw)  # many releases support this
    except TypeError:
        pass
    except Exception:
        pass

    # 2) classmethods some releases expose
    for name in ("from_message", "from_str", "from_string", "parse", "loads"):
        m = getattr(SiweMessage, name, None)
        if callable(m):
            try:
                return m(raw)  # type: ignore[misc]
            except Exception:
                continue

    # 3) positional constructor (rare)
    try:
        return SiweMessage(raw)  # type: ignore[call-arg]
    except Exception as e:
        raise ValueError(f"Failed to parse SIWE text: {e}")

def verify_message_and_get(
    fid_expected: int | None,
    message: str,
    signature: str,
    expected_nonce: str | None,
):
    # 1) Parse raw SIWE / SIWF
    siwe = _load_siwe_model(message)

    # 2) Domain (exact) & optional server-nonce
    exp_dom = expected_domain()
    if getattr(siwe, "domain", None) != exp_dom:
        raise ValueError(f"Domain mismatch: got {getattr(siwe, 'domain', None)} expected {exp_dom}")

    if expected_nonce and getattr(siwe, "nonce", None) != expected_nonce:
        raise ValueError("Nonce mismatch")

    # 2b) Must be Optimism mainnet (10)
    try:
        chain_id = int(getattr(siwe, "chain_id"))
    except Exception:
        chain_id = None
    if chain_id != EXPECTED_CHAIN_ID:
        raise ValueError(f"Unexpected chain id: {chain_id} (expected {EXPECTED_CHAIN_ID})")

    # 3) Signature verify (EIP-191)
    try:
        siwe.verify(signature, domain=siwe.domain, nonce=siwe.nonce)
    except (DomainMismatch, NonceMismatch, ExpiredMessage) as e:
        raise ValueError(f"Signature verify failed: {e.__class__.__name__}")

    signer = Web3.to_checksum_address(getattr(siwe, "address"))

    # 4) Extract FID from resources
    fid = parse_fid_from_resources(getattr(siwe, "resources", None))
    if fid is None:
        raise ValueError("Missing fid in SIWE resources")
    if fid_expected and fid != fid_expected:
        raise ValueError("FID mismatch")

    # 5) Check current custody on-chain matches signer
    custody = ID_REGISTRY.functions.custodyOf(fid).call()
    custody = None if int(custody, 16) == 0 else Web3.to_checksum_address(custody)
    if custody is None or custody != signer:
        raise ValueError("Signer is not current custody for FID")

    return {
        "fid": fid,
        "signer": signer,
        "nonce": getattr(siwe, "nonce"),
        "domain": getattr(siwe, "domain"),
    }
