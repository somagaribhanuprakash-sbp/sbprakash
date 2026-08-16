"""
The detailed 4-phase / week-by-day Restart Plan (20 weeks).
This is the single source of truth — served to the frontend via /api/restart/plan
so it only lives in one place instead of being duplicated between index.html and plan.html.
Each day gets a stable key: <phase>-w<weekIndex>-d<dayIndex>
"""

RESTART_PLAN = [
    {
        "key": "p1", "name": "Phase 1 — Foundations", "range": "Weeks 1–3", "color": "cyan",
        "weeks": [
            {"name": "Week 1 — Subnetting Mastery", "days": [
                "Binary/decimal conversion + IP address structure",
                "CIDR notation — network bits vs host bits, what /24 /25 /26 actually mean",
                "Practice: network address, broadcast address, usable range for /24 /25 /26",
                "Practice: same for /27 /28 /29 /30",
                "Timed drill: 20 random CIDR problems, aim under 1 min each",
                "Explain subnetting out loud/in writing from scratch, no notes",
            ]},
            {"name": "Week 2 — OSI Model + Wireshark", "days": [
                "Learn all 7 OSI layers and what job each one does",
                "Install Wireshark, capture your own traffic loading a website",
                "Find the Ethernet header (L2) and IP header (L3) in your capture",
                "Find the TCP header (L4), follow a full TCP stream",
                "Find the HTTP data (L7), trace one full request/response",
                "Map ARP spoofing, IP spoofing, and SQLi to their correct OSI layers — explain why",
            ]},
            {"name": "Week 3 — Linux Fundamentals", "days": [
                "Filesystem structure + navigation commands (cd, ls, find, etc.)",
                "File permissions — chmod, chown, read/write/execute",
                "Processes — ps, top, kill, background/foreground jobs",
                "Bash basics — variables, pipes, redirection, grep/awk",
                "SSH — connect to a remote box with key-based auth",
                "Review day: explain TCP handshake + DNS resolution from scratch, no notes",
            ]},
        ],
    },
    {
        "key": "p2", "name": "Phase 2 — Web Fundamentals", "range": "Weeks 4–10", "color": "green",
        "weeks": [
            {"name": "Week 4 — SQL Injection", "days": [
                "Study how SQL injection works conceptually before touching labs",
                "PortSwigger Academy: SQLi labs — easy tier",
                "PortSwigger Academy: SQLi labs — medium tier",
                "Write your own explanation of 2 labs you completed, no AI",
            ]},
            {"name": "Week 5 — Cross-Site Scripting (XSS)", "days": [
                "Study reflected vs stored vs DOM-based XSS",
                "PortSwigger Academy: XSS labs — easy tier",
                "PortSwigger Academy: XSS labs — medium tier",
                "Write your own explanation of 2 labs you completed, no AI",
            ]},
            {"name": "Week 6 — IDOR & Auth Bypass", "days": [
                "Study how broken access control and IDOR happen",
                "PortSwigger Academy: access control labs",
                "PortSwigger Academy: authentication labs",
                "Write your own explanation of 2 labs you completed, no AI",
            ]},
            {"name": "Week 7 — SSRF & CSRF", "days": [
                "Study SSRF — what it is, why servers trust internal requests",
                "PortSwigger Academy: SSRF labs",
                "PortSwigger Academy: CSRF labs",
                "Write your own explanation of 2 labs you completed, no AI",
            ]},
            {"name": "Week 8 — Access Control & Business Logic", "days": [
                "Study business logic vulnerabilities (why automated scanners miss these)",
                "PortSwigger Academy: business logic labs",
                "PortSwigger Academy: file upload vulnerability labs",
                "Write your own explanation of 2 labs you completed, no AI",
            ]},
            {"name": "Week 9 — Rebuild Your Old Reports", "days": [
                "Pick 2 of your old AI-generated scan reports from GitHub",
                "Rewrite report 1 completely yourself, in your own words",
                "Rewrite report 2 completely yourself, in your own words",
                "Push the rewritten versions to GitHub, replacing the old ones",
            ]},
            {"name": "Week 10 — Review & Self-Test", "days": [
                "Re-do 2 labs from earlier weeks cold, no hints",
                "Write a one-page personal cheat sheet of the top 8 web vuln classes",
                "Self-test: explain SQLi, XSS, IDOR, SSRF, CSRF to an imaginary beginner",
                "Identify your weakest topic from this phase and note it down",
            ]},
        ],
    },
    {
        "key": "p3", "name": "Phase 3 — Real Targets", "range": "Weeks 11–16", "color": "amber",
        "weeks": [
            {"name": "Week 11 — First Real Boxes", "days": [
                "Set up TryHackMe or HackTheBox account",
                "Complete first easy box matching a topic you already know",
                "Write a short methodology note: what you tried, in what order",
            ]},
            {"name": "Week 12 — Second Box + Methodology", "days": [
                "Complete a second easy/medium box",
                "Start a running personal recon/exploitation checklist",
            ]},
            {"name": "Week 13 — Bug Bounty Setup", "days": [
                "Register on HackerOne and/or Bugcrowd",
                "Pick 2 beginner-friendly programs",
                "Read each program's scope and rules of engagement carefully",
            ]},
            {"name": "Week 14 — Recon Only", "days": [
                "Passive recon on your chosen program — subdomains, endpoints, tech stack",
                "No exploitation yet — just mapping the attack surface",
            ]},
            {"name": "Week 15 — Active Testing", "days": [
                "Actively test in-scope targets using what you learned in Phase 2",
                "Log every attempt, including failed ones — this is the real skill being built",
            ]},
            {"name": "Week 16 — First Writeup", "days": [
                "Write your first honest bug bounty writeup — a real finding or a documented non-finding",
                "Get feedback on it from a community (Discord/forum) if possible",
            ]},
        ],
    },
    {
        "key": "p4", "name": "Phase 4 — First Real Work", "range": "Weeks 17–20", "color": "red",
        "weeks": [
            {"name": "Week 17 — Build Your Offer", "days": [
                "Build a simple one-page portfolio: your real writeups + GitHub + certs",
                "Write a short, honest description of what you can offer (basic security review)",
            ]},
            {"name": "Week 18 — Outreach", "days": [
                "List 10 small local businesses/shops that might need a basic review",
                "Reach out to 5+ offering a free or very low-cost basic security review",
            ]},
            {"name": "Week 19 — First Real Review", "days": [
                "Perform your first real, small, authorized security review",
                "Document findings the way you practiced in Phase 2",
            ]},
            {"name": "Week 20 — Deliver & Reflect", "days": [
                "Deliver the report, walk the client/business through it",
                "Ask for a testimonial or reference if it went well",
                "Reflect: what's the next real target/skill to go after",
            ]},
        ],
    },
]


def flat_item_keys():
    keys = []
    for phase in RESTART_PLAN:
        for wi, week in enumerate(phase["weeks"]):
            for di, _ in enumerate(week["days"]):
                keys.append(f"{phase['key']}-w{wi}-d{di}")
    return keys
