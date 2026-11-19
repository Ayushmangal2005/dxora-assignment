"""URL validation and SSRF (Server-Side Request Forgery) protection."""

import ipaddress
import socket
from urllib.parse import urlparse


def is_private_or_restricted_ip(ip_str: str) -> bool:
    """Check if an IP address belongs to private, loopback, or reserved ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return True


def validate_url(url: str, check_dns: bool = True) -> str:
    """
    Validate a website URL for accessibility and SSRF protection.
    
    Ensures:
    1. Scheme is http or https.
    2. Hostname is present and well-formed.
    3. Hostname does not resolve to private, loopback, or reserved internal IPs.
    
    Returns the normalized URL string or raises ValueError.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string.")

    cleaned_url = url.strip()

    # Parse initial URL
    parsed = urlparse(cleaned_url)

    # If scheme was provided and it's not http/https, reject immediately
    if parsed.scheme:
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.")
    else:
        # Bare domain/path like example.com -> prepend https:// and re-parse
        cleaned_url = "https://" + cleaned_url
        parsed = urlparse(cleaned_url)

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: Hostname is missing.")

    # Block common local/internal aliases
    blocked_hosts = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "metadata.google.internal",
        "169.254.169.254",
    }
    if hostname.lower() in blocked_hosts or hostname.lower().endswith(".local"):
        raise ValueError(f"Access to internal/private host '{hostname}' is blocked for SSRF protection.")

    # Check if hostname itself is directly an IP literal
    is_ip = False
    try:
        ip_obj = ipaddress.ip_address(hostname)
        is_ip = True
    except ValueError:
        is_ip = False

    if is_ip:
        if is_private_or_restricted_ip(str(ip_obj)):
            raise ValueError(f"Access to private IP address '{hostname}' is blocked for SSRF protection.")
    elif check_dns:
        # Hostname is a domain name, resolve DNS to verify all resolved IPs
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            resolved_ips = {item[4][0] for item in addr_info}
            if not resolved_ips:
                raise ValueError(f"Could not resolve domain name '{hostname}'.")
            for ip in resolved_ips:
                if is_private_or_restricted_ip(ip):
                    raise ValueError(
                        f"Domain '{hostname}' resolves to restricted internal IP '{ip}' (SSRF Protection)."
                    )
        except socket.gaierror as e:
            raise ValueError(f"Failed to resolve domain '{hostname}': {e}")

    return cleaned_url
