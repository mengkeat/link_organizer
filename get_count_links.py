import re

def extract_links_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Match markdown links: [text](url)
    md_links = re.findall(r'\[[^\]]+\]\((https?://[^\s)]+)\)', content)
    # Match bare URLs (not inside markdown links)
    bare_links = re.findall(r'(?<!\]\()(?<!\]\s)(https?://[^\s)]+)', content)
    # Combine and deduplicate
    links = list(dict.fromkeys(md_links + bare_links))
    return links

if __name__ == "__main__":
    links = extract_links_from_file('links.md')
    for link in links:
        print(link)
    print(f"Total: {len(links)}")
