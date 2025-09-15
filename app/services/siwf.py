# app/services/siwf.py
from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from siwe import SiweMessage, DomainMismatch, NonceMismatch, ExpiredMessage
from web3 import Web3
from app.core.config import settings

# Farcaster custody lives on Optimism mainnet
EXPECTED_CHAIN_ID = 10  # OP Mainnet

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
    # must exactly match the host the user sees in the SIWE text (e.g. "www.glaria.xyz")
    return settings.expected_domain()

def _coerce_raw_siwe_message(m: Any) -> str:
    """
    MiniKit / SIWE providers sometimes return:
      - a raw string, or
      - { message: "<raw-string>", signature: "0x..." }, or
      - { message: { message: "<raw-string>", ... }, signature: "0x..." }
    Normalize to the raw multi-line SIWE string.
    """
    if isinstance(m, str):
        return m
    if isinstance(m, dict):
        inner = m.get("message")
        if isinstance(inner, str):
            return inner
        if isinstance(inner, dict) and isinstance(inner.get("message"), str):
            return inner["message"]
    raise ValueError("Invalid SIWE message: expected raw string or object containing it at .message")

def parse_fid_from_resources(resources: Optional[Iterable[str]]) -> Optional[int]:
    """
    Accept common SIWF resource forms:
      - farcaster://fid/123
      - farcaster://fids/123
      - fc://fid/123
      - farcaster://user?id=123
    """
    if not resources:
        return None

    patterns = [
        r"^farcaster://fids?/(\d+)$",       # fid or fids
        r"^fc://fid/(\d+)$",                # fc://fid/123
        r"^farcaster://user\?id=(\d+)$",    # farcaster://user?id=123
    ]

    for raw in resources:
        s = (raw or "").strip()
        for pat in patterns:
            m = re.match(pat, s)
            if m:
                return int(m.group(1))
    return None

def verify_message_and_get(
    fid_expected: Optional[int],
    message: Any,          # tolerate object or string
    signature: str,
    expected_nonce: Optional[str],
):
    # 1) Normalize and parse SIWE
    raw = _coerce_raw_siwe_message(message)
    siwe = SiweMessage(message=raw)

    # 2) Enforce domain and optional server nonce (if you choose to use it)
    exp_dom = expected_domain()
    if siwe.domain != exp_dom:
        raise ValueError(f"Domain mismatch: got {siwe.domain} expected {exp_dom}")
    if expected_nonce and siwe.nonce != expected_nonce:
        raise ValueError("Nonce mismatch")

    # 3) Enforce Optimism chain id (Farcaster custody)
    try:
        chain_id = int(getattr(siwe, "chain_id"))
    except Exception:
        chain_id = None
    if chain_id != EXPECTED_CHAIN_ID:
        raise ValueError(f"Unexpected chain id: {chain_id} (expected {EXPECTED_CHAIN_ID})")

    # 4) EIP-191 signature verification
    try:
        siwe.verify(signature, domain=siwe.domain, nonce=siwe.nonce)
    except (DomainMismatch, NonceMismatch, ExpiredMessage) as e:
        raise ValueError(f"Signature verify failed: {e.__class__.__name__}")

    signer = Web3.to_checksum_address(siwe.address)

    # 5) Extract fid from resources
    fid = parse_fid_from_resources(getattr(siwe, "resources", None))
    if fid is None:
        raise ValueError("Missing fid in SIWE resources")
    if fid_expected and fid != fid_expected:
        raise ValueError("FID mismatch")

    # 6) Verify current custody on-chain
    custody = ID_REGISTRY.functions.custodyOf(fid).call()
    custody = None if int(custody, 16) == 0 else Web3.to_checksum_address(custody)
    if custody is None or custody != signer:
        raise ValueError("Signer is not current custody for FID")

    return {
        "fid": fid,
        "signer": signer,
        "nonce": siwe.nonce,
        "domain": siwe.domain,
    }
