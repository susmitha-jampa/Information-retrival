import os
import re
import time
import csv
from collections import deque
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class SimpleCrawler:
    def __init__(self):
        self.base_url = "https://pureportal.coventry.ac.uk"
        self.endpoint = "/en/publications"
        self.crawling_url = self.base_url + self.endpoint
        self.visited_urls = deque()
        self.browser = None
        self.results = []
        self.search_query = ""
        self.results_with_authors = 0
        self.results_without_authors = 0

        try:
            self.browser = self._create_web_browser()
            self._initialize_crawler()
        except WebDriverException as e:
            print("Error starting the browser:", e)

    def _create_web_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--timeout=20")
        options.add_experimental_option("detach", True)
        driver_path = 'chromedriver.exe'
        return webdriver.Chrome(options=options, executable_path=driver_path)

    def _initialize_crawler(self):
        self.browser.get(self.crawling_url)
        try:
            WebDriverWait(self.browser, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]'))).click()
        except NoSuchElementException:
            pass

        search_input = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.ID, "global-search-input")))
        search_query = input("Please enter a search query you want to perform: ")
        search_input.send_keys(search_query)

        search_button = self.browser.find_element_by_id("normalSearch")
        search_button.click()

        self.search_query = search_query
        self._start_crawling(self.browser.current_url)

    def _start_crawling(self, web_url):
        self.visited_urls.append(web_url)
        response = requests.get(web_url)
        plain_text = response.text
        soup = BeautifulSoup(plain_text, "html.parser")
        for publication in soup.findAll('li', {'class': re.compile('^list-result-item list-result-item.*')}):
            title = publication.find('h3', {'class': 'title'})
            if title:
                article_name = title.text.strip()
                article_name_url_formatted = article_name.lower().replace(" ", "-")
                article_url = f"{self.base_url}/en/publications/{article_name_url_formatted}"

                authors = publication.findAll('a', {'rel': 'Person'})
                authors_list = [author.text.strip() for author in authors]
                authors_urls_list = [author.get('href') for author in authors]

                if not authors_list:
                    self.results_without_authors += 1
                    continue

                publication_details = publication.find('span', {'class': 'date'})
                publication_date = publication_details.text.strip() if publication_details else ""

                result_row = {
                    'Search Query': self.search_query,
                    'Result No.': len(self.results) + 1,
                    'Article Title': article_name,
                    'Article URL': article_url,
                    'Authors': ", ".join(authors_list),
                    'Author URLs': ", ".join(authors_urls_list),
                    'Publish Date': publication_date
                }

                self.results.append(result_row)
                self.results_with_authors += 1

                print(f"\033[32mResult No.: {len(self.results)}\033[0m")
                print()
                print("\033[34mArticle Title:\033[0m", article_name)
                print()
                print("\033[34mArticle URL:\033[0m", article_url)
                print()
                print("\033[34mAuthors:\033[0m", ", ".join(authors_list))
                print()
                print("\033[34mAuthor URLs:\033[0m", ", ".join(authors_urls_list))
                print()
                print("\033[34mPublish Date:\033[0m", publication_date)
                print()
                print()

        try:
            time.sleep(5)
            next_page = self.browser.find_element_by_class_name("next")
            if next_page.is_enabled():
                time.sleep(3)
                next_page.click()
                time.sleep(5)
                web_url = self.browser.current_url
                self._start_crawling(web_url)
        except NoSuchElementException:
            print("End of pages")
            self._write_to_csv()

    def _write_to_csv(self):
        csv_filename = "query_results.csv"
        with open(csv_filename, mode='w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['Search Query', 'Result No.', 'Article Title', 'Article URL', 'Authors', 'Author URLs', 'Publish Date']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)

        print(f"Results written to '{csv_filename}'.")
        print(f"Total Search results found: {len(self.results) + self.results_without_authors}")
        print(f"Number of results found from Coventry University Authors: {self.results_with_authors}")
        print(f"Number of results found from outside Coventry University Authors: {self.results_without_authors}")
        open_csv_file = input("Do you want to open the CSV file? (yes/no): ").lower()
        if open_csv_file == 'yes':
            try:
                os.system(f'start {csv_filename}')
            except Exception as e:
                print("Error opening CSV file:", e)

if __name__ == "__main__":
    SimpleCrawler()
