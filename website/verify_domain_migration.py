"""Verify canonical-domain metadata and mocked nginx host redirects."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
SITE_URL = "https://agrownex.com"
ROUTES = [
    "/",
    "/solutions",
    "/inputs",
    "/advisory",
    "/produce",
    "/finance",
    "/brands",
    "/export-support",
    "/programmes",
    "/future",
    "/app",
    "/wholesale",
    "/partners",
    "/about",
    "/contact",
    "/privacy",
    "/delete-account",
]


def html_for(route: str) -> str:
    name = "index.html" if route == "/" else route.removeprefix("/") + ".html"
    return (ROOT / name).read_text(encoding="utf-8")


def attr(head: str, pattern: str) -> str:
    match = re.search(pattern, head, flags=re.I | re.S)
    assert match, pattern
    return match.group(1)


def head_values(route: str) -> dict[str, str]:
    head = attr(html_for(route), r"<head>(.*?)</head>")
    return {
        "title": attr(head, r"<title>(.*?)</title>"),
        "description": attr(head, r'<meta name="description" content="([^"]*)">'),
        "canonical": attr(head, r'<link rel="canonical" href="([^"]*)">'),
        "og:url": attr(head, r'<meta property="og:url" content="([^"]*)">'),
        "og:image": attr(head, r'<meta property="og:image" content="([^"]*)">'),
        "og:site_name": attr(head, r'<meta property="og:site_name" content="([^"]*)">'),
    }


def verify_metadata() -> None:
    for route in ROUTES:
        values = head_values(route)
        expected = SITE_URL + ("/" if route == "/" else route)
        assert values["canonical"] == expected, (route, values["canonical"])
        assert values["og:url"] == expected, (route, values["og:url"])
        assert values["og:image"].startswith(SITE_URL + "/"), (route, values["og:image"])
        assert values["og:site_name"] == "AgrowNex", route

    home = html_for("/")
    schemas = re.findall(r'<script type="application/ld\+json">(.*?)</script>', home, flags=re.S)
    graph = json.loads(schemas[0])["@graph"]
    organization = next(node for node in graph if node.get("@type") == "Organization")
    assert organization["name"] == "AgrowNex"
    assert organization["url"] == SITE_URL
    assert organization["logo"].startswith(SITE_URL + "/")
    assert organization["address"]["addressLocality"] == "Thoothukudi"
    assert organization["address"]["addressRegion"] == "Tamil Nadu"
    assert organization["address"]["addressCountry"] == "IN"
    assert organization["sameAs"] == [
        "https://www.linkedin.com/company/agrownex",
        "https://www.instagram.com/agrowai/",
    ]


def verify_sitemap_and_robots() -> None:
    root = ElementTree.parse(ROOT / "sitemap.xml").getroot()
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text for node in root.findall("s:url/s:loc", namespace)]
    assert urls == [SITE_URL + ("/" if route == "/" else route) for route in ROUTES]
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    assert f"Sitemap: {SITE_URL}/sitemap.xml" in robots


def redirect_result(host: str, request_uri: str, forwarded_host: str = "") -> tuple[int, str | None]:
    config = (ROOT / "default.conf.template").read_text(encoding="utf-8")
    redirect_hosts = set(re.findall(r"^\s+([\w.-]+)\s+1;$", config, flags=re.M))
    target = attr(config, r"return 301 (https://[^$;]+)\$request_uri")
    candidate = forwarded_host.split(",", 1)[0].strip() if forwarded_host else host
    hostname = urlsplit("//" + candidate).hostname or ""
    return (301, target + request_uri) if hostname.lower() in redirect_hosts else (200, None)


def verify_redirects() -> None:
    cases = [
        ("agrowai.in", "/about?x=1", "", 301, "https://agrownex.com/about?x=1"),
        ("www.agrowai.in", "/contact?from=old", "", 301, "https://agrownex.com/contact?from=old"),
        ("www.agrownex.com", "/", "", 301, "https://agrownex.com/"),
        ("agrownex.com", "/", "", 200, None),
        ("railway.internal", "/about?x=1", "agrowai.in", 301, "https://agrownex.com/about?x=1"),
        ("admin.agrowai.in", "/", "", 200, None),
        ("api.agrowai.in", "/", "", 200, None),
        ("example.up.railway.app", "/", "", 200, None),
        ("localhost:8080", "/", "", 200, None),
    ]
    for host, uri, forwarded, expected_status, expected_location in cases:
        actual = redirect_result(host, uri, forwarded)
        assert actual == (expected_status, expected_location), (host, uri, forwarded, actual)
        source = f" via X-Forwarded-Host={forwarded}" if forwarded else ""
        location = f" {actual[1]}" if actual[1] else ""
        print(f"{host}{uri}{source} -> {actual[0]}{location}")


if __name__ == "__main__":
    verify_metadata()
    verify_sitemap_and_robots()
    verify_redirects()
    for route in ("/", "/about"):
        print(f"HEAD {route}: {json.dumps(head_values(route), ensure_ascii=False)}")
    print("Domain migration verification passed.")
