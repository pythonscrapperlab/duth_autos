import logging
import requests
from typing import List, Optional, Dict, Any
import os
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

class BaseHelper:
    def __init__(self, name: str = __name__, log_file: str = "app.log"):
        # Configure logger
        self.config = {}
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            # File handler
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")

            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)

            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)

            self.logger.setLevel(logging.DEBUG)

        self.initialize_variables()

    def initialize_variables(self):
        config_file = os.path.join(os.getcwd(), "config.json")
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                self.config = json.load(f)
                self.proxies = self.config.get("proxies", {})
        else:
            self.logger.warning(f"Config file not found: {config_file}")

    # ----------------------------
    # HTTP Requests with Proxy
    # ----------------------------
    def get_with_proxy(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 45,
    ) -> Optional[requests.Response]:
        try:
            self.logger.debug(f"GET Request [Proxy] → {url}")
            response = requests.get(url, params=params, headers=headers, proxies=self.proxies, timeout=timeout)
            response.raise_for_status()
            self.logger.info(f"GET [Proxy] {url} | Status: {response.status_code}")
            return response
        except requests.RequestException as e:
            self.logger.error(f"GET [Proxy] {url} failed: {e}")
            return self.get_with_proxy(url, params, headers, timeout)

    def post_with_proxy(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 45,
    ) -> Optional[requests.Response]:
        try:
            self.logger.debug(f"POST Request [Proxy] → {url}")
            if self.proxies:
                response = requests.post(url, data=data, json=json, headers=headers, proxies=self.proxies, timeout=timeout)
            else:
                response = requests.post(url, data=data, json=json, headers=headers, timeout=timeout)
            response.raise_for_status()
            self.logger.info(f"POST [Proxy] {url} | Status: {response.status_code}")
            return response
        except requests.RequestException as e:
            self.logger.error(f"POST [Proxy] {url} failed: {e}")
            return self.post_with_proxy(url, data, json, headers, timeout)

    def put_with_proxy(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 45,
    ) -> Optional[requests.Response]:
        try:
            self.logger.debug(f"PUT Request [Proxy] → {url}")
            response = requests.put(url, data=data, json=json, headers=headers, proxies=self.proxies, timeout=timeout)
            response.raise_for_status()
            self.logger.info(f"PUT [Proxy] {url} | Status: {response.status_code}")
            return response
        except requests.RequestException as e:
            self.logger.error(f"PUT [Proxy] {url} failed: {e}")
            return self.put_with_proxy(url, data, json, headers, timeout)

    def save_to_csv(self, data: List[Dict[str, Any]], filename: str):
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        self.logger.info(f"Data saved to {filename}")

    def initChrome(self, headless=False, saveDriver=False, driverName='driver')->webdriver.Chrome:
        file_path = os.path.join(os.getcwd(), driverName)
        os.makedirs(file_path, exist_ok=True)
        options = Options()
        if saveDriver:options.add_argument(f"--user-data-dir={file_path}")
        options.add_argument("--log-level=3")
        options.add_argument('--start-maximized')
        if headless:  options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('ignore-certificate-errors')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.managed_default_content_settings.video": 2
            }
        options.add_experimental_option("prefs", prefs)
        # service = Service(executable_path="chromedriver.exe")
        driver = webdriver.Chrome(options=options)
        
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )
        
        return driver