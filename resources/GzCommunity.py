"""GzCommunity -- land a JWT-authenticated user INSIDE an Experience Cloud site.

Robot Framework library. Proven live 2026-09-21 against SDO - Partner Central
(co1735825376471), user Paul Partner, Partner Community licence: member nav
rendered, no password, no login form, no passkey.

WHY THIS EXISTS
  QForce's JWTLogin derives its host from the token response, which returns the
  INTERNAL instance -- so it lands a portal user on lightning.force.com, where a
  Partner Community licence answers "edition or user license isn't supported yet".
  The session has to be opened on the SITE domain instead.

WHAT DOES NOT WORK (measured, do not retry)
  * <site>/secur/frontdoor.jsp?sid=<access_token>   -> lands GUEST.
    Only the singleaccess `otp` frontdoor authenticates.
  * Reusing a frontdoor_uri -> it is SINGLE-USE. The second visit lands GUEST.
    Mint it immediately before you navigate.

PREREQUISITES IN THE ORG (each cost a real failure to find)
  1. The site must be PUBLISHED. "Active" is not "Published". An unpublished site
     refuses every authenticated session while login history records SUCCESS.
  2. The user's PROFILE must be a member of the site (Administration > Members).
  3. The connected app must pre-authorise the user (permission set or profile),
     else the token request answers invalid_app_access.
  4. If the org enforces login IP ranges, trust BOTH address families -- and for
     IPv6 trust the /64, because privacy addresses rotate within minutes.
"""
import json, time, socket, urllib.request, urllib.parse
import jwt as _jwt

__version__ = "1.0.0"


def _ipv4_only():
    """Force IPv4. An org enforcing trusted IP ranges sees the IPv6 address
    otherwise, and a whitelisted IPv4 is never consulted (measured 2026-09-21)."""
    orig = socket.getaddrinfo
    socket.getaddrinfo = lambda h, p, f=0, t=0, pr=0, fl=0: orig(h, p, socket.AF_INET, t, pr, fl)


def _post(url, data=b"", headers=None, timeout=45):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def jwt_community_frontdoor(client_id, username, private_key, site_url,
                            landing="/s/", login_url="https://login.salesforce.com",
                            force_ipv4=True):
    """Return a ONE-TIME frontdoor URL that signs `username` into `site_url`.

    Navigate to it IMMEDIATELY -- it cannot be reused.

    | ${fd}= | Jwt Community Frontdoor | ${client_id} | ${username} | ${private_key} | ${site} |
    | GoTo   | ${fd} |
    """
    if force_ipv4:
        _ipv4_only()
    site = site_url.rstrip("/")
    claims = {"iss": client_id, "sub": username, "aud": login_url,
              "exp": int(time.time()) + 180}
    assertion = _jwt.encode(claims, private_key, algorithm="RS256")
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion}).encode()
    tok = _post(login_url.rstrip("/") + "/services/oauth2/token", body,
                {"Content-Type": "application/x-www-form-urlencoded"})
    fd = _post(site + "/services/oauth2/singleaccess", b"",
               {"Authorization": "Bearer " + tok["access_token"]})
    uri = fd["frontdoor_uri"]
    if landing:
        # urlparse, NOT a split on ".com" -- that worked for one org and breaks on
        # any other TLD or a host with ".com" earlier in the string.
        path = urllib.parse.urlparse(site_url).path.rstrip("/")
        uri += ("&" if "?" in uri else "?") + urllib.parse.urlencode(
            {"retURL": path + landing})
    return uri
