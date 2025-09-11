# app/services/siwf.py
import re
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
    return settings.expected_domain()

def parse_fid_from_resources(resources: list[str] | None) -> int | None:
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
        r"^farcaster://fids?/(\d+)$",         # fid or fids
        r"^fc://fid/(\d+)$",                  # some clients use fc://
        r"^farcaster://user\?id=(\d+)$",      # older/alt style
    ]

    for raw in resources:
        s = raw.strip()
        for pat in patterns:
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
    # 1) Parse SIWE / SIWF
    siwe = SiweMessage(message=message)

    # 2) Enforce domain + (optional) nonce
    exp_dom = expected_domain()
    if siwe.domain != exp_dom:
        raise ValueError(f"Domain mismatch: got {siwe.domain} expected {exp_dom}")
    if expected_nonce and siwe.nonce != expected_nonce:
        raise ValueError("Nonce mismatch")

    # 2b) Enforce chain id (Farcaster custody is on Optimism mainnet = 10)
    # MiniKit is already showing "Chain ID: 10" in your logs; keep this guard:
    try:
        chain_id = int(getattr(siwe, "chain_id"))
    except Exception:
        chain_id = None
    if chain_id != EXPECTED_CHAIN_ID:
        raise ValueError(f"Unexpected chain id: {chain_id} (expected {EXPECTED_CHAIN_ID})")

    # 3) Cryptographic verification (EIP-191)
    try:
        siwe.verify(signature, domain=siwe.domain, nonce=siwe.nonce)
    except (DomainMismatch, NonceMismatch, ExpiredMessage) as e:
        raise ValueError(f"Signature verify failed: {e.__class__.__name__}")

    signer = Web3.to_checksum_address(siwe.address)

    # 4) Extract fid from resources
    fid = parse_fid_from_resources(getattr(siwe, "resources", None))
    if fid is None:
        raise ValueError("Missing fid in SIWE resources")
    if fid_expected and fid != fid_expected:
        raise ValueError("FID mismatch")

    # 5) Check current custody on-chain
    custody = ID_REGISTRY.functions.custodyOf(fid).call()
    # if zero address, int('0x0...', 16) == 0
    custody = None if int(custody, 16) == 0 else Web3.to_checksum_address(custody)
    if custody is None or custody != signer:
        raise ValueError("Signer is not current custody for FID")

    return {
        "fid": fid,
        "signer": signer,
        "nonce": siwe.nonce,
        "domain": siwe.domain,
    }