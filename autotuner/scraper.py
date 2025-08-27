
import requests
from utlis.helper import BaseHelper
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import ast

class AutoTunerScraper(BaseHelper):
    def __init__(self):
        super().__init__(name="AutoTunerScraper", log_file="autotuner_scraper.log")
        self.headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'dnt': '1',
                'priority': 'u=1, i',
                'referer': 'https://www.autotuner.com/nl/pages/compatibiliteit',
                'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            }
    def get_vehicles(self, page="0"):
        params = {
            'search': '',
            'type': '',
            'ecuType': '',
        }

        response = requests.get(
            f'https://www.autotuner.com/a/app/compatibility/search/page/{page}',
            params=params,
            headers=self.headers,
        )
        data = response.json()
        if data:
            return data.get('data', []), data.get('nbPage', 0)
        else:
            return [], 0

    def start(self, max_workers=10):
        self.logger.info("Starting AutoTunerScraper...")

        # First fetch page 1 to know how many total pages
        vehicles, nb_page = self.get_vehicles(page=1)
        if not vehicles:
            self.logger.info("No vehicles found on page 1. Exiting.")
            return
        
        self.logger.info(f"Found {len(vehicles)} vehicles on page 1.")
        all_vehicles = vehicles[:]  # copy initial results
        
        # Now fetch the rest of the pages in parallel
        self.logger.info(f"Fetching remaining {nb_page-1} pages with {max_workers} threads...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.get_vehicles, page): page for page in range(2, nb_page + 1)}

            for future in as_completed(futures):
                page = futures[future]
                try:
                    vehicles, _ = future.result()
                    if vehicles:
                        self.logger.info(f"Found {len(vehicles)} vehicles on page {page}.")
                        all_vehicles.extend(vehicles)
                    else:
                        self.logger.info(f"No vehicles found on page {page}.")
                except Exception as e:
                    self.logger.error(f"Error fetching page {page}: {e}")

        # Save everything once at the end
        self.save_to_csv(all_vehicles, "autotuner_vehicles.csv")
        df = pd.read_csv("autotuner_vehicles.csv")
        df['Logo'] = df['manufacturerId'].apply(lambda x: f"https://assets.autotuner.com/brand/logo/{x}.png")
        df['Method Logos'] = df['methods'].apply(lambda x: ", ".join([f"https://www.autotuner.com/cdn/shop/t/24/assets/{met}.svg" for met in ast.literal_eval(x)]))
        df.to_csv("autotuner_vehicles.csv", index=False)
        self.logger.info(f"Saved {len(all_vehicles)} vehicles to autotuner_vehicles.csv")
