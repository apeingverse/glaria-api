# app/services/siwf.py
import re
from siwe import SiweMessage, DomainMismatch, NonceMismatch, ExpiredMessage
from web3 import Web3
from app.core.config import settings

EXPECTED_CHAIN_ID = 10  # Farcaster custody is on Optimism mainnet

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
    return settings.expected_domain()  # must be *exactly* e.g. "www.glaria.xyz"

def parse_fid_from_resources(resources: list[str] | None) -> int | None:
    """Accept common SIWF resource forms."""
    if not resources:
        return None
    patterns = [
        r"^farcaster://fids?/(\d+)$",       # farcaster://fid/123 or farcaster://fids/123
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

def verify_message_and_get(
    fid_expected: int | None,
    message: str,
    signature: str,
    expected_nonce: str | None,
):
    # 1) Parse the *raw* SIWE text (IMPORTANT: positional argument, not keyword!)
    try:
        siwe = SiweMessage(message)
    except Exception as e:
        raise ValueError(f"Failed to parse SIWE text: {e}")

    # 2) Domain & (optional) server-nonce
    exp_dom = expected_domain()
    if siwe.domain != exp_dom:
        raise ValueError(f"Domain mismatch: got {siwe.domain} expected {exp_dom}")
    if expected_nonce and siwe.nonce != expected_nonce:
        raise ValueError("Nonce mismatch")

    # 3) Chain id must be Optimism (10)
    try:
        chain_id = int(getattr(siwe, "chain_id"))
    except Exception:
        chain_id = None
    if chain_id != EXPECTED_CHAIN_ID:
        raise ValueError(f"Unexpected chain id: {chain_id} (expected {EXPECTED_CHAIN_ID})")

    # 4) Signature verify (EIP-191)
    try:
        siwe.verify(signature, domain=siwe.domain, nonce=siwe.nonce)
    except (DomainMismatch, NonceMismatch, ExpiredMessage) as e:
        raise ValueError(f"Signature verify failed: {e.__class__.__name__}")

    signer = Web3.to_checksum_address(siwe.address)

    # 5) Extract FID from resources
    fid = parse_fid_from_resources(getattr(siwe, "resources", None))
    if fid is None:
        raise ValueError("Missing fid in SIWE resources")
    if fid_expected and fid != fid_expected:
        raise ValueError("FID mismatch")

    # 6) Check current custody on-chain
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
