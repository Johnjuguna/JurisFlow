"""Pure name and identifier matching for conflict searches. No database access."""

import re
import unicodedata
from difflib import SequenceMatcher

MIN_ID_LENGTH = 5
DEFAULT_THRESHOLD = 0.85

# Words that do not identify a party: company forms and honorifics.
_NOISE = {
    "ltd", "limited", "plc", "inc", "incorporated", "llp", "llc", "co", "company", "corp", "corporation",
    "mr", "mrs", "ms", "miss", "dr", "prof", "hon", "eng", "rev", "sir",
}


def normalize_name(name):
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.casefold().replace("&", " and ")
    s = re.sub(r"[\W_]+", " ", s)
    return " ".join(t for t in s.split() if t not in _NOISE)


def normalize_id(value):
    if not value:
        return ""
    return re.sub(r"[\W_]+", "", str(value)).upper()


def name_similarity(a, b):
    """0.0 to 1.0. Word order and company suffixes are ignored; typos and extra names still score high."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    ta, tb = set(na.split()), set(nb.split())
    if na == nb or ta == tb:
        return 1.0
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len(small) >= 2 and small <= big:
        return 0.9
    jaccard = len(ta & tb) / len(ta | tb)
    ratio = SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()
    return round(max(jaccard, ratio), 4)


def find_matches(name, id_number, candidates, threshold=DEFAULT_THRESHOLD):
    """candidates: dicts with source, record, name, id_number, role, matter. Returns hits, best first."""
    qid = normalize_id(id_number)
    hits = []
    for c in candidates:
        cid = normalize_id(c.get("id_number"))
        if len(qid) >= MIN_ID_LENGTH and qid == cid:
            score, reason = 1.0, "ID / PIN match"
        else:
            score = name_similarity(name, c.get("name"))
            if score < threshold:
                continue
            reason = "Exact name match" if score == 1.0 else "Similar name"
        hits.append({
            "source": c.get("source"), "record": c.get("record"), "name": c.get("name"),
            "role": c.get("role"), "matter": c.get("matter"), "score": score, "reason": reason,
        })
    hits.sort(key=lambda h: (-h["score"], str(h["name"])))
    return hits
