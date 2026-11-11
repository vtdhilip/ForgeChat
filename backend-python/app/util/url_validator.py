import ipaddress
import logging
import socket
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "host.docker.internal",
    "gateway.docker.internal",
    "metadata.google.internal",
    "instance-data",
}

def is_safe_external_url(url: Optional[str], allow_http: bool = False) -> bool:
    """
    Validate that a URL is a valid, publicly reachable external HTTP(S) URL
    and not targeting private, loopback, link-local, or cloud metadata endpoints.
    Default allow_http=False enforces HTTPS only.
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
        allowed_schemes = ("https", "http") if allow_http else ("https",)
        if parsed.scheme.lower() not in allowed_schemes:
            logger.warning(f"[url_validator] Rejected non-allowed scheme in URL: {parsed.scheme}")
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        hostname_lower = hostname.lower()
        if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
            logger.warning(f"[url_validator] Blocked internal hostname: {hostname}")
            return False

        # Check if hostname is an IP literal
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                logger.warning(f"[url_validator] Blocked private IP literal: {ip}")
                return False
            return True
        except ValueError:
            pass  # Not an IP literal, proceed to resolve DNS

        # Resolve DNS to check if domain points to private IP (DNS rebinding prevention)
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                resolved_ip = ipaddress.ip_address(ip_str)
                if resolved_ip.is_private or resolved_ip.is_loopback or resolved_ip.is_link_local or resolved_ip.is_reserved or resolved_ip.is_multicast:
                    logger.warning(f"[url_validator] Domain {hostname} resolved to private/reserved IP: {ip_str}")
                    return False
        except socket.gaierror:
            logger.warning(f"[url_validator] Unable to resolve hostname: {hostname}")
            return False

        return True
    except Exception as e:
        logger.warning(f"[url_validator] Error validating URL {url}: {e}")
        return False
