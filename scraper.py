import json
import logging
import sys
from urllib.parse import urljoin

import pandas as pd
import pandera.pandas as pa
import requests
from bs4 import BeautifulSoup

# Configure system stdout/stderr encoding/errors to handle non-ASCII/Unicode correctly in terminal
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
except Exception:
    pass

# Configure logging
logger = logging.getLogger("scraper")
logger.setLevel(logging.INFO)

if not logger.handlers:
    # Formatter for logs
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler("scraper.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

SCHEMA = pa.DataFrameSchema({
    "Name of the business": pa.Column(str, nullable=False),
    "Address": pa.Column(str, nullable=False),
    "District": pa.Column(str, nullable=False),
    "Website / social media link": pa.Column(
        object,
        checks=pa.Check(lambda series: series.map(lambda x: isinstance(x, list)).all()),
        nullable=True
    ),
    "Services offered": pa.Column(
        object,
        checks=pa.Check(lambda series: series.map(lambda x: isinstance(x, list)).all()),
        nullable=True
    ),
    "Price range": pa.Column(str, nullable=True),
    "Rating + number of reviews": pa.Column(str, nullable=True)
},
    unique=["Name of the business", "Address", "District"], # In case there are salons appearing more than once
    strict=True,
    coerce=True,
)


class Scraper:
    def __init__(self):
        self.main_url = 'https://booksy.com/pl-pl/s/salon-kosmetyczny/3_warszawa'
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        self.salon_urls = []

    def run(self, num_of_pages: int):
        if not num_of_pages > 0:
            logger.error("ValueError: num_of_pages must be greater than 0 (received: %d)", num_of_pages)
            raise ValueError('num_of_pages must be greater than 0')

        logger.info("Starting Booksy scraper. Targeting %d pages.", num_of_pages)

        # 1. First, collect all urls to the saloons. One page consists of 20 salons
        for page_idx in range(1, num_of_pages + 1):
            page_query = f'?businessesPage={page_idx}'
            current_page_url = urljoin(self.main_url, page_query)
            logger.info("Collecting salon URLs from page %d/%d: %s", page_idx, num_of_pages, current_page_url)

            response = requests.get(current_page_url, headers=self.headers)
            soup = BeautifulSoup(response.text, features="html.parser")
            business_items = soup.find_all("div", class_="business-list-item")

            for item in business_items:
                salon_url = item.find('a', href=True)
                absolute_salon_url = urljoin(self.main_url, salon_url['href'])
                self.salon_urls.append(absolute_salon_url)

        logger.info("Discovered %d salon URLs. Starting detail extraction...", len(self.salon_urls))

        data_items = []

        # 2. Go to each url and get the data
        for idx, salon_url in enumerate(self.salon_urls, 1):
            logger.info("[%d/%d] Scraping details from: %s", idx, len(self.salon_urls), salon_url)

            response = requests.get(salon_url, headers=self.headers)
            soup = BeautifulSoup(response.text, features="html.parser")

            # Extract data from ld+json script
            script_tag = soup.find("script", attrs={"type": "application/ld+json", "data-hid": "ld-json-0"})
            ld_data = json.loads(script_tag.string)

            business_name = ld_data.get("name")
            logger.info("Processing salon: '%s'", business_name)

            street_address = ld_data.get("address", {}).get("streetAddress", "")
            address_parts = [part.strip() for part in street_address.split(",")]
            district = address_parts[-1] if address_parts else ""
            address = ", ".join(address_parts[:-1]) if address_parts else ""

            social_links = [salon_url] + ld_data.get("sameAs", [])

            for idx, social_link in enumerate(social_links):
                if 'booksy' in social_link:
                    social_links[idx] = social_links[idx].split('#')[0]  # Remove URL fragment from booksy website (e.g. #ba_s=sr_1)

            services_offered = sorted(list(set([offer.get("name") for offer in ld_data.get("makesOffer", [])])))
            price_range = ld_data.get("priceRange")
            if price_range:  # Sometimes, this value is not available
                price_range = price_range.replace('PLN', '').strip()
            aggregate_rating = ld_data.get("aggregateRating", {})
            rating = aggregate_rating.get("ratingValue")
            num_reviews = aggregate_rating.get("reviewCount")

            rating_str = str(float(rating))

            num_reviews_str = str(num_reviews)
            rating_num_of_reviews = f'{rating_str} {num_reviews_str}'

            data_item = {
                'Name of the business': business_name,
                'Address': address,
                'District': district,
                'Website / social media link': social_links,
                'Services offered': services_offered,
                'Price range': price_range,
                'Rating + number of reviews': rating_num_of_reviews
            }
            logger.info(f"Scraped data item: {data_item}")
            data_items.append(data_item)

        logger.info("Validating scraped data with Pandera...")
        df = pd.DataFrame(data_items)
        SCHEMA.validate(df)
        logger.info("Pandera validation successful!")

        logger.info("Saving %d scraped salon items to salons.json", len(df))
        df.to_json("salons.json", orient="records", force_ascii=False, indent=4)
        logger.info("Scraper pipeline run successfully completed!")


if __name__ == '__main__':
    scraper = Scraper()
    scraper.run(6)
