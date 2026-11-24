"""Ownership verification.

Three ways for a promoter to prove they run an event:

1. website - publish a token on the event's own site or ticket page; we fetch it.
2. email   - click a link sent to an address on the event's official domain.
3. manual  - submit evidence; a staff member reviews it in the admin.
"""
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse

# Hosts anyone can publish on. A token here only counts if it is on the exact
# page the promoter listed, and an address here proves nothing about ownership.
SHARED_HOSTS = {
    "facebook.com", "instagram.com", "x.com", "twitter.com", "linkedin.com",
    "eventbrite.com", "meetup.com", "ticketmaster.com", "quicket.co.za",
    "linktr.ee", "wixsite.com", "wordpress.com", "blogspot.com", "google.com",
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me",
}
EMAIL_SALT = "event-email-verify"
EMAIL_MAX_AGE = 3 * 24 * 3600


class FetchError(Exception):
    pass


def _bare(host):
    host = (host or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _host_matches(host, allowed):
    host, allowed = _bare(host), _bare(allowed)
    return host == allowed or host.endswith("." + allowed)


def _is_shared(host):
    return any(_host_matches(host, s) for s in SHARED_HOSTS)


def _norm_url(url):
    p = urlparse(url)
    return (_bare(p.hostname), p.path.rstrip("/"))


def _public_host(host):
    """Reject hosts that resolve to private/loopback/link-local addresses (SSRF guard)."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    return all(ipaddress.ip_address(i[4][0]).is_global for i in infos)


def safe_fetch(url, max_redirects=3, max_bytes=500_000):
    """Fetch a page as text, validating every redirect hop."""
    for _ in range(max_redirects + 1):
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname or not _public_host(p.hostname):
            raise FetchError("That address can't be checked.")
        try:
            resp = requests.get(url, timeout=8, allow_redirects=False, stream=True,
                                headers={"User-Agent": "EventHubVerifier/1.0"})
        except requests.RequestException:
            raise FetchError("We couldn't reach that page.")
        try:
            if 300 <= resp.status_code < 400 and resp.headers.get("Location"):
                url = urljoin(url, resp.headers["Location"])
                continue
            if resp.status_code != 200:
                raise FetchError(f"That page returned status {resp.status_code}.")
            body = resp.raw.read(max_bytes, decode_content=True)
            return body.decode(resp.encoding or "utf-8", errors="ignore")
        finally:
            resp.close()
    raise FetchError("That page redirected too many times.")


def check_website_proof(event, proof_url):
    """Return (ok, message). The token must appear on a page the promoter controls."""
    reference = [u for u in (event.official_website, event.ticket_url) if u]
    if not reference:
        return False, "Add an official website or ticket link to your event first."
    host = urlparse(proof_url).hostname or ""
    matched = [u for u in reference if _host_matches(host, urlparse(u).hostname or "")]
    if not matched:
        return False, "The page must be on your event's official website or ticket link."
    if _is_shared(host) and _norm_url(proof_url) not in [_norm_url(u) for u in matched]:
        return False, "On shared platforms, use the exact page you listed for this event."
    try:
        html = safe_fetch(proof_url)
    except FetchError as e:
        return False, str(e)
    if event.token_snippet not in html:
        return False, "We couldn't find the code on that page. Publish it, then try again."
    return True, ""


def check_email_eligibility(event, address):
    """The address must sit on the event's official website domain."""
    if not event.official_website:
        return False, "Add an official website to your event first."
    site = urlparse(event.official_website).hostname or ""
    domain = address.rsplit("@", 1)[-1]
    if _is_shared(site):
        return False, "Your official website is on a shared platform, so email can't prove ownership. Use the website code or manual review."
    if not _host_matches(domain, site):
        return False, f"The address must end in @{_bare(site)}."
    return True, ""


def send_email_link(request, event, address):
    token = signing.dumps({"e": event.pk, "a": address}, salt=EMAIL_SALT)
    link = request.build_absolute_uri(reverse("events:verify_email", args=[token]))
    send_mail(
        f"Confirm you run “{event.title}”",
        f"Open this link while signed in to EventHub to verify your event:\n\n{link}\n\nIt expires in 3 days. "
        "If you didn't ask for this, ignore this email.",
        None, [address],
    )


def read_email_token(token):
    """Return (event_id, address) or None."""
    try:
        data = signing.loads(token, salt=EMAIL_SALT, max_age=EMAIL_MAX_AGE)
        return data["e"], data["a"]
    except (signing.BadSignature, KeyError):
        return None
