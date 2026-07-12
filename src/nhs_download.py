import json
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import time


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

BASE_URL = "https://www.nhsinform.scot"
AZ_URL = f"{BASE_URL}/illnesses-and-conditions/a-to-z/"


STOP_HEADING = "Help us improve NHS inform"

SKIP_HEADINGS = {
    "Return to Symptoms",
    "Last Updated:",
    "Next Review Date:",
    "Find your local services",
}

SKIP_TEXT = {
    "Return to Symptoms",
    "Last Updated:",
    "Next Review Date:",
    "Search for a service near you by entering your postcode below.",
    "Please input your postcode in the following format: A12 1BC",
    "Find your local services",
    "You told us your credentials were:",
    "You said:",
    "Based on the information you gave us, we made the following recommendation:",
}

CLEAN_PREFIXES = (
   "Read more",
    "Source:",
    "Last updated",
    "NHS inform has more information",
)

def html_to_markdown(container: Tag) -> str:
    """
    Convert the main article HTML into simple Markdown.
    """

    lines = []
    started = False    

    # for element in container.descendants:
    for element in container.find_all(["h1", "h2", "h3", "p", "li"]):        

        if not isinstance(element, Tag):
            continue

        text = element.get_text(" ", strip=True)

        if not text:
            continue

        if text in SKIP_TEXT:
         continue        

        # ----------------------------
        # Start at the page title (H1)
        # ----------------------------
        if element.name == "h1":
            started = True

        if not started:
            continue


        if any(text.startswith(p) for p in CLEAN_PREFIXES):
            continue        

        # ----------------------------
        # Stop before footer
        # ----------------------------
        if element.name in ("h1", "h2", "h3"):

            if text == STOP_HEADING:
                break

            if text in SKIP_HEADINGS:
                continue

        if element.name == "h1":
            lines.append(f"# {text}\n")

        elif element.name == "h2":
            lines.append(f"\n## {text}\n")

        elif element.name == "h3":
            lines.append(f"\n### {text}\n")

        elif element.name == "p":
            lines.append(text + "\n")

        elif element.name == "li":
            lines.append(f"- {text}")

    return "\n".join(lines).strip()


def get_symptom_links():
    """
    Extract all symptom page URLs from the NHS Inform A-Z page.

    Returns:
        list[(title, url)]
    """
    
    # response = requests.get(AZ_URL)
    # response.raise_for_status()    
    
    for attempt in range(3):
        try:
            response = requests.get(AZ_URL, timeout=30)
            response.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 2:
                raise
            print(f"Request failed ({e}), retrying...")
            time.sleep(2)        

    soup = BeautifulSoup(response.text, "html.parser")

    links = []

    for a in soup.select("a[href]"):

        href = a["href"]

        path = urlparse(href).path  # works for both relative + absolute
        print(href,path)
        if not path.startswith("/illnesses-and-conditions/"):
            continue

        if path.rstrip("/") == "/illnesses-and-conditions":
            continue

        title = a.get_text(strip=True)

        if not title:
            continue

        url = urljoin(BASE_URL, href)

        links.append((title, url))

    # remove duplicates while preserving order
    seen = set()
    unique = []

    for title, url in links:
        if url not in seen:
            unique.append((title, url))
            seen.add(url)

    return unique

def clean_article(article):
    # Remove navigation / UI / metadata blocks
    for tag in article.select("nav, footer, form, aside"):
        tag.decompose()

    # Remove known NHS widgets 
    for tag in article.select(".postcode-search"):
        tag.decompose()

    # Remove “read more” blocks
    for tag in article.find_all(string=lambda t: "Read more" in t):
        parent = tag.parent
        if parent:
            parent.decompose()

    # Remove source / metadata lines container if present
    for tag in article.find_all(string=lambda t: "Last updated" in t or "Source" in t):
        parent = tag.parent
        if parent:
            parent.decompose()

    return article


def scrape_symptom_page(title: str, url: str):
    """
    Scrape one NHS symptom page.
    """

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    article = soup.find("main")
    

    if article is None:
        article = soup

    article = clean_article(article)

    markdown = html_to_markdown(article)

    slug = urlparse(url).path.rstrip("/").split("/")[-1]

    return {
        "id": slug,
        "category": "symptom",
        "section": title,
        "url": url,
        "content": markdown,
    }


def build_symptom_dataset(output_file="data/nhs-symptom.json"):
    """
    Build the complete NHS symptom dataset.
    """

    records = []

    links = get_symptom_links()

    print(f"Found {len(links)} symptom pages")

    for i, (title, url) in enumerate(links, start=1):

        print(f"[{i}/{len(links)}] {title}")

        try:
            record = scrape_symptom_page(title, url)
            records.append(record)

        except Exception as ex:
            print(f"Failed: {url}")
            print(ex)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(records)} records to {output_file}")

    return records


if __name__ == "__main__":
    build_symptom_dataset()

