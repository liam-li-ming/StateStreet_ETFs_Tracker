from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import quote
from datetime import datetime
from playwright.sync_api import sync_playwright

class GetAvailableEtfs:

    def __init__(self):
        self.base_url = "https://www.ssga.com/us/en/intermediary/fund-finder"

    def asset_class_select(self, asset_class):
        """
        :param asset_class: ["alternative", "equity", "fixed-income", "Multi-Asset"]
        :return: a constructed url that filters the asset class
        """
        asset = quote(f"assetclass:{asset_class}")
        etf_list_url = self.base_url + f"?g={asset}"

        return etf_list_url

    @staticmethod
    def fetch_url_content(etf_list_url, wait_time = 5000):
        """
        Fetch HTML content with JavaScript rendering using Playwright.
        :param etf_list_url: URL to fetch
        :param wait_time: Time to wait for JS to render (in milliseconds)
        :return: Rendered HTML content
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless = True)
            page = browser.new_page()
            page.goto(etf_list_url)
            # Wait for the page to load and JS to render
            page.wait_for_timeout(wait_time)
            url_content = page.content()
            browser.close()

        return url_content

    @staticmethod
    def parse_etf_table(url_content):
        """
        Parse the HTML content and extract ETF data into a DataFrame.
        :param url_content: HTML content from fetch_content
        :return: DataFrame with ETF data
        """
        soup = BeautifulSoup(url_content, 'html.parser')

        rows = soup.find_all('tr')

        etf_data = []
        for row in rows:
            domicile_td = row.find('td', class_ = 'domicile')
            if not domicile_td:
                continue

            domicile = domicile_td.find('div')
            domicile = domicile.get_text(strip = True) if domicile else ''

            if not domicile or domicile == 'Domicile':
                continue

            fund_name_td = row.find('td', class_ = 'fundName')
            fund_name = fund_name_td.find('a').get_text(strip = True) if fund_name_td and fund_name_td.find('a') else ''

            ticker_td = row.find('td', class_ = 'fundTicker')
            ticker = ticker_td.find('a').get_text(strip = True) if ticker_td and ticker_td.find('a') else ''
            if not ticker and ticker_td:
                ticker_div = ticker_td.find('div')
                ticker = ticker_div.get_text(strip = True) if ticker_div else ''

            ter_td = row.find('td', class_ = 'ter')
            ter = ter_td.find('div').get_text(strip = True) if ter_td and ter_td.find('div') else ''

            nav_td = row.find('td', class_ = 'nav')
            nav = nav_td.find('div').get_text(strip = True) if nav_td and nav_td.find('div') else ''

            aum_td = row.find('td', class_ = 'aum')
            aum = aum_td.find('div').get_text(strip = True) if aum_td and aum_td.find('div') else ''

            as_of_date_td = row.find('td', class_ = 'asOfDate')
            as_of_date_raw = as_of_date_td.find('div').get_text(strip = True) if as_of_date_td and as_of_date_td.find('div') else ''
            try:
                as_of_date = datetime.strptime(as_of_date_raw, '%b %d %Y').strftime('%Y-%m-%d')
            except ValueError:
                as_of_date = as_of_date_raw

            etf_data.append({
                'Domicile': domicile,
                'Name': fund_name,
                'Ticker': ticker,
                'Gross Expense Ratio': ter,
                'NAV': nav,
                'AUM': aum,
                'Date': as_of_date
            })

        df_url_list = pd.DataFrame(etf_data)
        return df_url_list

if __name__ == "__main__":

    get = GetAvailableEtfs()

    url_edit = get.asset_class_select("equity") # Options: alternative, equity, fixed-income, Multi-Asset
    print(f"Fetching: {url_edit}")
    content = get.fetch_url_content(url_edit)

    df = get.parse_etf_table(content)
    print(df.to_string())
    print(f"\nTotal ETFs found: {len(df)}")