"""Read explicitly AP-attributed 2026 race calls from public, source-linked pages.

A vote lead, campaign concession, or another desk's projection is not an AP call.
"""
from __future__ import annotations
import html
import re
from html.parser import HTMLParser

VOTECLOCK = "https://voteclock.org/2026-election-results"
ROLLCALL = "https://rollcall.com/2026/11/03/key-midterm-election-results/"

def clean(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())

def matching_candidate(race, value):
    val = clean(value)
    for c in race["candidates"]:
        name = c["name"]
        parts = re.findall(r"[a-z]+", name.lower())
        if val == clean(name):
            return name
        if len(parts) >= 2:
            first, last = parts[0], parts[-1]
            if re.fullmatch(re.escape(first) + r"[a-z]{0,20}" + re.escape(last), val):
                return name
    return None

def call_record(winner, source, url):
    return {
        "winner": winner,
        "calledBy": "AP",
        "calledAt": None,
        "sourceUrl": url,
        "sourceFeed": source,
    }

class ElectionCallHTML(HTMLParser):
    """Capture h2 section labels and the li entries under them."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.section = ""
        self.h2 = None
        self.li = None
        self.items = []
        self.link_href = None
        self.link_text = None
        self.link_list = []

    def handle_starttag(self, tag, attrs):
        if tag == "h2":
            self.h2 = []
        elif tag == "li" and self.li is None:
            self.li = []
            self.link_list = []
        elif tag == "a" and self.li is not None:
            self.link_href = dict(attrs).get("href")
            self.link_text = []

    def handle_data(self, data):
        if self.h2 is not None:
            self.h2.append(data)
        if self.li is not None:
            self.li.append(data)
        if self.link_text is not None:
            self.link_text.append(data)

    def handle_endtag(self, tag):
        if tag == "h2" and self.h2 is not None:
            self.section = " ".join("".join(self.h2).split()).lower()
            self.h2 = None
        elif tag == "a" and self.link_text is not None:
            self.link_list.append(("".join(self.link_text), self.link_href))
            self.link_href = None
            self.link_text = None
        elif tag == "li" and self.li is not None:
            self.items.append((self.section, " ".join("".join(self.li).split()), list(self.link_list)))
            self.li = None
            self.link_list = []

def from_voteclock(page, races):
    parser = ElectionCallHTML()
    parser.feed(page)
    full_text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    if "Races called by the Associated Press" not in full_text:
        raise ValueError("VoteClock AP attribution missing")
    if not any("senate races called" in sec for sec, _, _ in parser.items):
        raise ValueError("VoteClock Senate calls section missing")
    updates = {}
    for section, text, links in parser.items:
        if "senate races called" in section:
            office = "Senate"
        elif "governor races called" in section:
            office = "Governor"
        else:
            continue
        match = re.match(r"^(.+?):\s*(.+?)\s*\(([DRI])\)\.\s*AP call\b", text, re.I)
        if not match:
            continue
        state, reported, party = match.group(1).strip(), match.group(2).strip(), match.group(3).upper()
        for race in races:
            if race["office"] != office or race["state"].casefold() != state.casefold():
                continue
            winner = matching_candidate(race, reported)
            if not winner:
                continue
            person = next(c for c in race["candidates"] if c["name"] == winner)
            if person["party"] != party:
                continue
            origin = next((href for title, href in links if "AP call" in title and href and href.startswith("https://")), VOTECLOCK)
            updates[race["id"]] = call_record(winner, "Vote Clock — AP-attributed report", origin)
    return updates

def from_rollcall(page, races):
    page = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", page, flags=re.I | re.S)
    page = re.sub(r"</(?:p|li|h[1-6]|div|article|section|br)>", "\n", page, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    lines = [" ".join(s.split()) for s in text.splitlines() if s.strip()]
    heading = next((i for i, line in enumerate(lines) if "Roll Call is tracking the results" in line and "Associated Press" in line), None)
    if heading is None:
        raise ValueError("Roll Call AP attribution missing")
    updates = {}
    for line in lines[heading+1:]:
        if "Recent Stories" in line:
            break
        if not re.search(r"\bdefeats\b", line, re.I):
            continue
        before, after = re.split(r"\bdefeats\b", line, maxsplit=1, flags=re.I)
        for race in races:
            if race["office"] != "House":
                continue
            state = re.escape(race["state"])
            number = int(race["district"])
            suffix = "th" if number % 100 in (11, 12, 13) else {1:"st", 2:"nd", 3:"rd"}.get(number % 10, "th")
            if not re.search(rf"\b{state}['’]?s?\s+{number}{suffix}\s+District\b", before, flags=re.I):
                continue
            candidate = [c["name"] for c in race["candidates"] if re.search(r"\b" + re.escape(c["name"].split()[0]) + r"\b.*\b" + re.escape(c["name"].split()[-1]) + r"\b", before, flags=re.I)]
            loser = [c["name"] for c in race["candidates"] if c["name"] not in candidate and re.search(r"\b" + re.escape(c["name"].split()[0]) + r"\b.*\b" + re.escape(c["name"].split()[-1]) + r"\b", after, flags=re.I)]
            if len(candidate) != 1 or len(loser) != 1:
                continue
            updates[race["id"]] = call_record(candidate[0], "CQ Roll Call — calls attributed to the AP", ROLLCALL)
    return updates
