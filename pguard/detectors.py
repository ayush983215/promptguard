"""Deterministic detectors. No AI in this file.

Each detector returns Finding objects with the character span of the match.
The raw matched text is kept in Finding.value ONLY so the engine can redact
it; it is hidden from repr() and must never be logged or stored.
"""
from __future__ import annotations

import base64
import binascii
import ipaddress
import math
import re
from collections import Counter
from dataclasses import dataclass, field

DEFAULT_INTERNAL_SUFFIXES = ("internal", "corp", "local", "lan", "intranet")

# Lower number = higher priority when two findings overlap the same text.
PRIORITY = {
    "private_key": 0, "aws_access_key": 1, "github_token": 1, "slack_token": 1,
    "jwt": 1, "aws_secret_key": 2, "encoded_secret": 3, "credit_card": 4,
    "email": 5, "internal_ip": 6, "internal_hostname": 6, "phone": 7,
    "high_entropy": 8, "possible_phone": 9,
}
ALL_TYPES = frozenset(PRIORITY)


@dataclass(frozen=True)
class Finding:
    type: str
    start: int
    end: int
    value: str = field(repr=False)          # raw text: never log or store
    confidence: str = "high"                # "high" or "low"
    detail: str = ""                        # e.g. what a base64 blob decoded to


# ---------------------------------------------------------------- helpers
def luhn_ok(digits: str) -> bool:
    """Luhn checksum: separates real card numbers from random digit runs."""
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def shannon_entropy(s: str) -> float:
    """Bits per character. Random keys score high, English/identifiers low."""
    counts = Counter(s)
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


# ---------------------------------------------------------------- patterns
_SIMPLE = [
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{22,255})\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("jwt", re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
]
# The 40-char secret only counts when an "aws ... secret" label is nearby;
# 40 random chars on their own are left to the entropy detector.
_AWS_SECRET = re.compile(
    r"(?i)aws[\w .-]{0,30}?(?:secret|sk)[\w .-]{0,20}?['\"\s:=]+([A-Za-z0-9/+=]{40})(?![A-Za-z0-9/+=])")
_PK_BEGIN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")
_PK_END = re.compile(r"-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")
_CARD = re.compile(r"(?<![\d-])\d(?:[ -]?\d){12,18}(?![\d-])")
_PHONE = re.compile(r"(?<![\w.])\+?\(?\d[\d\s().-]{7,18}\d(?![\w:])")
_BARE_PHONE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_TOKEN = re.compile(r"[A-Za-z0-9+/=_-]{24,}")
_B64 = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/=])")
_HEXBLOB = re.compile(r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}){12,}(?![0-9A-Fa-f])")
_DATEISH = re.compile(r"\d{4}-\d{2}-\d{2}")
_HEX_HASH = re.compile(r"(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_RFC1918 = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]


# ---------------------------------------------------------------- detectors
def _scan_secrets(text: str) -> list[Finding]:
    """High-confidence credential patterns. Reused to inspect decoded base64."""
    out: list[Finding] = []
    for name, rx in _SIMPLE:
        if name == "email":
            continue
        out += [Finding(name, m.start(), m.end(), m.group()) for m in rx.finditer(text)]
    for m in _AWS_SECRET.finditer(text):
        out.append(Finding("aws_secret_key", m.start(1), m.end(1), m.group(1)))
    for m in _PK_BEGIN.finditer(text):
        end = _PK_END.search(text, m.end())
        stop = end.end() if end else len(text)   # unterminated key: take the rest
        out.append(Finding("private_key", m.start(), stop, text[m.start():stop]))
    return out


def _printable(decoded: str) -> bool:
    return decoded.isprintable() or "\n" in decoded


def _decoded_candidates(text: str):
    """Yield (match, decoded_text) for every base64 or hex blob that decodes to plain ASCII."""
    for m in _B64.finditer(text):
        blob = m.group()
        try:
            decoded = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=True).decode("ascii")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if _printable(decoded):
            yield m, decoded
    for m in _HEXBLOB.finditer(text):
        try:
            decoded = bytes.fromhex(m.group()).decode("ascii")
        except (ValueError, UnicodeDecodeError):
            continue
        if _printable(decoded):
            yield m, decoded


def _encoded_kinds(text: str, depth: int) -> set[str]:
    """Credential types hidden inside nested encodings. Depth-limited so input can't make us loop."""
    kinds: set[str] = set()
    if depth > 2:
        return kinds
    for _, decoded in _decoded_candidates(text):
        kinds |= {f.type for f in _scan_secrets(decoded)}
        kinds |= _encoded_kinds(decoded, depth + 1)
    return kinds


def _scan_all(text: str, suffixes) -> list[Finding]:
    out = _scan_secrets(text)
    out += [Finding("email", m.start(), m.end(), m.group()) for m in _SIMPLE[-1][1].finditer(text)]

    for m in _CARD.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            out.append(Finding("credit_card", m.start(), m.end(), m.group()))

    for m in _IPV4.finditer(text):
        try:
            ip = ipaddress.IPv4Address(m.group())
        except ValueError:
            continue
        if any(ip in net for net in _RFC1918):
            out.append(Finding("internal_ip", m.start(), m.end(), m.group()))

    host_rx = re.compile(
        r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:%s)\b" % "|".join(map(re.escape, suffixes)),
        re.IGNORECASE)
    out += [Finding("internal_hostname", m.start(), m.end(), m.group()) for m in host_rx.finditer(text)]

    for m in _PHONE.finditer(text):
        cand = m.group()
        digits = re.sub(r"\D", "", cand)
        has_format = any(c in cand for c in "+()- .")
        if (10 <= len(digits) <= 13 and has_format and not _DATEISH.search(cand)
                and not _IPV4.fullmatch(cand.strip())):
            out.append(Finding("phone", m.start(), m.end(), cand))
    out += [Finding("possible_phone", m.start(), m.end(), m.group(), "low")
            for m in _BARE_PHONE.finditer(text)]

    for m in _TOKEN.finditer(text):
        tok = m.group()
        if _HEX_HASH.fullmatch(tok) or _UUID.fullmatch(tok):
            continue                              # git SHAs / md5 / UUIDs are benign
        has_digit = any(c.isdigit() for c in tok)
        has_alpha = any(c.isalpha() for c in tok)
        if has_digit and has_alpha and shannon_entropy(tok) >= 4.0:
            out.append(Finding("high_entropy", m.start(), m.end(), tok, "low"))

    # blobs (base64 or hex, up to 2 layers deep) that decode to a known credential
    for m, decoded in _decoded_candidates(text):
        kinds = {f.type for f in _scan_secrets(decoded)} | _encoded_kinds(decoded, 1)
        if kinds:
            out.append(Finding("encoded_secret", m.start(), m.end(), m.group(), detail=",".join(sorted(kinds))))
    return out


def detect(text: str, internal_suffixes=DEFAULT_INTERNAL_SUFFIXES) -> list[Finding]:
    """Run every detector, then drop findings that overlap a higher-priority one."""
    candidates = sorted(_scan_all(text, internal_suffixes), key=lambda f: (PRIORITY[f.type], f.start))
    kept: list[Finding] = []
    for f in candidates:
        if all(f.end <= k.start or f.start >= k.end for k in kept):
            kept.append(f)
    return sorted(kept, key=lambda f: f.start)
