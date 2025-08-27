import os
import pandas as pd
from utlis.helper import BaseHelper
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

class AlienTechScraper(BaseHelper):
    def __init__(self):
        super().__init__(name="AlienTechScraper", log_file="alientech_scraper.log")
        self.base_url = 'https://www.alientech-tools.com/wp-admin/admin-ajax.php'
        self.headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'dnt': '1',
            'origin': 'https://www.alientech-tools.com',
            'priority': 'u=1, i',
            'referer': 'https://www.alientech-tools.com/vehicles/',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        
    def get_params(self, page_number="0") -> dict:
        return {
                'action': 'attvl_archive_filter_vehicle_types',
                'vehicleType': '',
                'brand': '',
                'fuel': '',
                'year': '',
                'pageNumber': page_number,
                'doIncrementPage': 'false',
                'rowsPerPage': '20',
                'tool': '',
                'connectionMode': '',
                'model': '',
                'version': '',
                'engineCode': '',
                'searchQuery': '',
                'doRefreshWhenOnboarding': 'true',
                'doReset': 'false',
                'openEcuListOnPageLoad': 'false',
            }
        
    def get_vehicles(self, soup: BeautifulSoup):
        all_vehicles = []
        for row in soup.find_all("tr", {"class":"vehicle-list-table-row"}):
            columns = row.find_all("td")
            if len(columns)<9:
                print("No columns found")
                continue
            vehicle_type = columns[0].text.strip()
            brand = columns[1].text.strip()
            model = columns[2].text.strip()
            version = columns[3].text.strip()
            year = columns[4].text.strip()
            fuel = columns[5].text.strip()
            engine_code = columns[6].text.strip()
            tools = ", ".join([li.text.strip().replace("\n", " ") for li in columns[7].find_all("li")])
            tools_imgs = ", ".join([img["src"] for img in columns[7].find_all("img")])
            connection_modes = ", ".join([li.text.strip().replace("\n", " ") for li in columns[8].find_all("li")])
            connection_modes_imgs = ", ".join([img["src"] for img in columns[8].find_all("img")])
            url = row['onclick'].replace("window.location='", "").replace("'", "")
            all_vehicles.append({
                "URL": url,
                "Vehicle Type": vehicle_type,
                "Brand": brand,
                "Model": model,
                "Version": version,
                "Year": year,
                "Fuel": fuel,
                "Engine Code": engine_code,
                "Tools Text": tools,
                "Tools Images": tools_imgs,
                "Connection Modes Text": connection_modes,
                "Connection Modes Images": connection_modes_imgs
            })
        return all_vehicles

    def scrape_data(self):
        self.logger.info("Scraping data from AlienTech...")

        # Fetch the first page
        params = self.get_params()
        response = self.post_with_proxy(self.base_url, headers=self.headers, data=params)
        data = response.json() if response else {}
        
        # Unescape & parse
        raw_html = data.get("html", "")
        soup = BeautifulSoup(raw_html, "html.parser")
        
        total_pages = data.get('totalPages', 0)
        self.logger.info(f"Total Pages: {total_pages}")

        all_vehicles = self.get_vehicles(soup)

        # Function for scraping a single page
        def scrape_page(page):
            self.logger.info(f"Scraping page {page}/{total_pages}...")
            params = self.get_params(page_number=str(page))
            response = self.post_with_proxy(self.base_url, headers=self.headers, data=params)
            if not response:
                return []
            data = response.json()
            raw_html = data.get("html", "")
            soup = BeautifulSoup(raw_html, "html.parser")
            return self.get_vehicles(soup)

        # Use ThreadPoolExecutor to parallelize page scraping
        with ThreadPoolExecutor(max_workers=10) as executor:  # adjust workers depending on proxies/infra
            futures = {executor.submit(scrape_page, page): page for page in range(2, total_pages + 1)}
            for future in as_completed(futures):
                page = futures[future]
                try:
                    vehicles = future.result()
                    all_vehicles.extend(vehicles)
                except Exception as e:
                    self.logger.error(f"Error scraping page {page}: {e}")

        self.logger.info(f"Total vehicles scraped: {len(all_vehicles)}")
        self.save_to_csv(all_vehicles, "alientech_vehicles.csv")
        return all_vehicles

    def start(self):
        # all_vehicles = self.scrape_data()
        all_vehicles_df = pd.read_csv("alientech_vehicles.csv")
        total = len(all_vehicles_df)
        self.logger.info(f"Processing {total} vehicles...")

        all_vehicles_detailed = []
        driver = self.initChrome(headless=True, saveDriver=False)  # new browser per thread

        def fetch_details(row, idx):
            try:
                driver.get(row["URL"])
                soup = BeautifulSoup(driver.page_source, "html.parser")
                vehicle_details = {}

                # Extract details
                for heading in soup.find_all("h2", {"class": "vehicle-card-subtitle"}):
                    details = heading.find_next_sibling("dl", {"class": "vehicle-card-dl"})
                    vehicle_details |= {
                        d_title.text.strip(): d_value.text.strip()
                        for d_title, d_value in zip(details.find_all("dt"), details.find_all("dd"))
                    }

                for heading in soup.find_all("h2", {"class": "vehicle-card-title"}):
                    details = heading.find_next_sibling("dl", {"class": "vehicle-card-dl"})
                    vehicle_details |= {
                        d_title.text.strip(): d_value.text.strip()
                        for d_title, d_value in zip(details.find_all("dt"), details.find_all("dd"))
                    }

                for heading in soup.find_all("h3", {"class": "vehicle-card-subtitle"}):
                    details = heading.find_next_sibling("dl", {"class": "vehicle-card-dl"})
                    if details:
                        vehicle_details |= {
                            d_title.text.strip(): d_value.text.strip()
                            for d_title, d_value in zip(details.find_all("dt"), details.find_all("dd"))
                        }
                    else:
                        ul = heading.find_next_sibling("ul", {"class": "vehicle-card-icon-list"})
                        if ul:
                            vehicle_details[heading.text.strip()] = str(ul)

                return {**row.to_dict(), **vehicle_details}, idx
            except Exception as e:
                self.logger.error(f"Got Error: {e}")

        # Parallel scraping
        # with ThreadPoolExecutor(max_workers=5) as executor:  # tune workers
        #     futures = {executor.submit(fetch_details, row, i): i for i, row in all_vehicles_df.iterrows()}
        #     done_count = 0
        #     for future in as_completed(futures):
        #         idx = futures[future]
        #         try:
        #             result, idx = future.result()
        #             all_vehicles_detailed.append(result)
        #             done_count += 1
        #             print(f"[{done_count}/{total}] Done -> Vehicle {idx+1}: {result.get('Model','Unknown')}")
        #         except Exception as e:
        #             self.logger.error(f"Error scraping vehicle {idx+1}: {e}")
        for ind, row in all_vehicles_df.iterrows():
            # if ind<18580:continue
            result, idx = fetch_details(row, ind)
            all_vehicles_detailed.append(result)
            self.logger.info(f"[{ind+1}/{total}] Done -> Vehicle {ind+1}: {result.get('Model','Unknown')}")
            if ind % 100 == 0:
                pd.DataFrame(all_vehicles_detailed).to_csv("alientech_vehicles_details.csv", index=False)

        self.logger.info(f"Total detailed vehicles processed: {len(all_vehicles_detailed)}")
        pd.DataFrame(all_vehicles_detailed).to_csv("alientech_vehicles_details.csv", index=False)
        self.logger.info("Scraping completed.")
