# app/services/siwf.py
from __future__ import annotations

import re
from typing import Any

from siwe import SiweMessage, DomainMismatch, NonceMismatch, ExpiredMessage
from web3 import Web3

from app.core.config import settings

EXPECTED_CHAIN_ID = 10  # Farcaster ID Registry on Optimism

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

def _load_siwe_model(raw: str) -> SiweMessage:
    # 1) keyword constructor
    try:
        return SiweMessage(message=raw)
    except TypeError:
        pass
    except Exception:
        pass

    # 2) common classmethods across releases
    for name in ("from_message", "from_str", "from_string", "parse", "loads"):
        m = getattr(SiweMessage, name, None)
        if callable(m):
            try:
                return m(raw)  # type: ignore[misc]
            except Exception:
                continue

    # 3) positional constructor
    try:
        return SiweMessage(raw)  # type: ignore[call-arg]
    except Exception as e:
        raise ValueError(f"Failed to parse SIWE text: {e}")

def parse_fid_from_resources(resources: list[str] | None) -> int | None:
    if not resources:
        return None
    pats = [
        r"^farcaster://fids?/(\d+)$",
        r"^fc://fid/(\d+)$",
        r"^farcaster://user\?id=(\d+)$",
    ]
    for raw in resources:
        s = raw.strip()
        for pat in pats:
            m = re.match(pat, s)
            if m:
                return int(m.group(1))
    return None

def verify_message_and_get(
    fid_expected: int | None,
    message: str,
    signature: str,
    expected_nonce: str | None,
):
    # 1) Parse
    siwe = _load_siwe_model(message)

    # 2) Domain allow-list (exact match to one allowed authority)
    dom = getattr(siwe, "domain", None)
    allowed = set(settings.ALLOWED_SIWE_DOMAINS or settings.allowed_siwe_domains())
    if dom not in allowed:
        raise ValueError(f"Domain mismatch: got {dom} allowed {sorted(list(allowed))}")

    # 3) ChainId (Optimism mainnet)
    try:
        chain_id = int(getattr(siwe, "chain_id"))
    except Exception:
        chain_id = None
    if chain_id != EXPECTED_CHAIN_ID:
        raise ValueError(f"Unexpected chain id: {chain_id} (expected {EXPECTED_CHAIN_ID})")

    # 4) Optional server nonce (disabled in this flow)
    if expected_nonce and getattr(siwe, "nonce", None) != expected_nonce:
        raise ValueError("Nonce mismatch")

    # 5) Signature verification
    try:
        siwe.verify(signature, domain=siwe.domain, nonce=siwe.nonce)
    except (DomainMismatch, NonceMismatch, ExpiredMessage) as e:
        raise ValueError(f"Signature verify failed: {e.__class__.__name__}")

    signer = Web3.to_checksum_address(getattr(siwe, "address"))

    # 6) FID in resources
    fid = parse_fid_from_resources(getattr(siwe, "resources", None))
    if fid is None:
        raise ValueError("Missing fid in SIWE resources")
    if fid_expected and fid != fid_expected:
        raise ValueError("FID mismatch")

    # 7) Check current custody on-chain
    custody = ID_REGISTRY.functions.custodyOf(fid).call()
    custody = None if int(custody, 16) == 0 else Web3.to_checksum_address(custody)
    if custody is None or custody != signer:
        raise ValueError("Signer is not current custody for FID")

    return {
        "fid": fid,
        "signer": signer,
        "nonce": getattr(siwe, "nonce"),
        "domain": dom,
    }
