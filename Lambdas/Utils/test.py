import urllib.request

def download_image(urls, file_name):
    for index, url in enumerate(urls):
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status == 200:
                    content = response.read()
                    # Generate a unique filename for each URL
                    unique_file_name = f"{file_name[:-4]}_{index}{file_name[-4:]}"
                    with open(unique_file_name, 'wb') as file:
                        file.write(content)
                    print(f"Image successfully downloaded from {url} and saved as {unique_file_name}")
                    return
                else:
                    print(f"Failed to download from {url}. Status code: {response.status}")
        except urllib.error.HTTPError as e:
            print(f"HTTP error occurred while trying to download from {url}: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            print(f"URL error occurred while trying to download from {url}: {e.reason}")
        except Exception as e:
            print(f"An unspecified error occurred while trying to download from {url}: {e}")
    print("All attempts failed.")

# List of URLs to try downloading the image from
urls = [
    "https://images.bizbuysell.com/shared/listings/225/2253329/f7ec12ee-e15e-4318-a85e-4ed4c2a904b2-W768.png"
]

# File name under which the image will be saved if the download is successful
file_name = "downloaded_image.png"

download_image(urls, file_name)
