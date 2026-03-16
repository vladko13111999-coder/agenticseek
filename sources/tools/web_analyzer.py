import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class WebAnalyzer:
    def __init__(self):
        self.name = "web_analyzer"
        self.description = "Analyzes a product URL and extracts name, description, price, images, and target audience."

    def execute(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            product_name = soup.find('h1').text if soup.find('h1') else "Neznámy názov"
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc['content'] if meta_desc else "Popis nenájdený"
            price_element = soup.find(class_=lambda x: x and 'price' in x.lower())
            price = price_element.text if price_element else "Cena neuvedená"
            images = [img['src'] for img in soup.find_all('img')[:5] if img.get('src')]

            result = {
                'url': url,
                'product_name': product_name.strip(),
                'description': description.strip(),
                'price': price.strip(),
                'images': images,
                'domain': urlparse(url).netloc
            }
            return result
        except Exception as e:
            return {'error': str(e), 'url': url}
