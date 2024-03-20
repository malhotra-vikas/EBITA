import requests
import xml.etree.ElementTree as ET

def fetch_sitemap(url):
    """Fetch the sitemap content from a given URL."""
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch sitemap from {url}")
        return None

def parse_sitemap(sitemap_content):
    """Parse sitemap XML content and extract URL details."""
    parsed_locs = []  # List to hold all the loc URLs
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    root = ET.fromstring(sitemap_content)
    urls = root.findall('.//sitemap:url', namespace)  # Adjusted for correct path
    for url in urls:
        loc = url.find('.//sitemap:loc', namespace).text  # Adjusted for correct path
        parsed_locs.append(loc)
    return parsed_locs

def process_sitemap_urls(file_path, output_file_path):
    """Process each URL in the file to fetch, parse its sitemap, and save parsed locs."""
    all_locs = []  # List to collect all locs across sitemaps
    with open(file_path, 'r') as file:
        for url in file:
            url = url.strip()  # Remove any leading/trailing whitespace
            sitemap_content = fetch_sitemap(url)
            if sitemap_content:
                parsed_locs = parse_sitemap(sitemap_content)
                all_locs.extend(parsed_locs)  # Add the parsed locs from this sitemap

    # Write all collected loc URLs to the output file
    with open(output_file_path, 'w') as out_file:
        for loc in all_locs:
            out_file.write(f"{loc}\n")

# Replace 'path/to/your/file.txt' with the actual file path
site_map_file_path = '/Users/vikas/builderspace/EBITA-1/bizbuysellscrapper/utils/SiteMapToURLList/businessforsale-urls.txt'
url_list_file_path = '/Users/vikas/builderspace/EBITA-1/bizbuysellscrapper/utils/SiteMapToURLList/urls.txt'
process_sitemap_urls(site_map_file_path, url_list_file_path)
