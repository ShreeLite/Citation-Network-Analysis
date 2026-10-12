"""Repair incomplete TLS chains without disabling verification.

Some institute servers (e.g. iiitd.ac.in) send a stale intermediate certificate, so clients
that do not do AIA fetching fail with "unable to get local issuer certificate". We read the
leaf certificate's Authority Information Access URL, download the issuing intermediate from
the CA, and verify against certifi's roots + those intermediates. The chain is still fully
verified up to a trusted root.
"""
from __future__ import annotations

import logging
import socket
import ssl

import certifi
import requests
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

from .config import EXTERNAL

log = logging.getLogger("tls")
BUNDLE = EXTERNAL / "ca_bundle_with_intermediates.pem"
EXTRA = EXTERNAL / "extra_intermediates.pem"


def _leaf_cert(host: str, port: int = 443) -> x509.Certificate:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # only to *read* the leaf; verification happens afterwards
    with socket.create_connection((host, port), timeout=30) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ss:
            der = ss.getpeercert(binary_form=True)
    return x509.load_der_x509_certificate(der)


def _aia_issuer_urls(cert: x509.Certificate) -> list[str]:
    try:
        aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS)
    except x509.ExtensionNotFound:
        return []
    return [
        d.access_location.value
        for d in aia.value
        if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS
    ]


def repair_chain(host: str) -> str:
    """Fetch missing intermediates for `host`; return a CA bundle path to verify against."""
    cert = _leaf_cert(host)
    pems = []
    for _ in range(3):  # walk up at most 3 intermediates
        urls = _aia_issuer_urls(cert)
        if not urls:
            break
        r = requests.get(urls[0], timeout=30)
        r.raise_for_status()
        try:
            cert = x509.load_der_x509_certificate(r.content)
        except ValueError:
            cert = x509.load_pem_x509_certificate(r.content)
        pems.append(cert.public_bytes(Encoding.PEM).decode())
        if cert.issuer == cert.subject:
            break
        log.info("TLS: fetched intermediate %s for %s", cert.subject.rfc4514_string(), host)
    existing = EXTRA.read_text() if EXTRA.exists() else ""
    new = existing + "".join(p for p in pems if p not in existing)
    EXTRA.write_text(new)
    BUNDLE.write_text(open(certifi.where()).read() + "\n" + new)
    return str(BUNDLE)


def bundle_path() -> str | bool:
    return str(BUNDLE) if BUNDLE.exists() else True
