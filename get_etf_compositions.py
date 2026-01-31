import pandas as pd


class GetEtfCompositions:

    def __init__(self):
        
        self.base_url = "https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/"

        self.pem = "holdings-daily-us-en-heco.xlsx" 


    def fetch_etf_composition_in_excel(self, etf_ticker):
        """
        Fetch ETF composition Excel file for a given ETF ticker.
        :param etf_ticker: ETF ticker symbol
        :return: DataFrame with ETF composition data
        """

        etf_excel = f"holdings-daily-us-en-{etf_ticker.lower()}.xlsx"

        etf_url = self.base_url + etf_excel

        df = pd.read_excel(etf_url, skiprows = 4)

        return df
    
if __name__ == "__main__":
    get = GetEtfCompositions()

    etf_ticker = "HECO"  # Example ETF ticker
    df = get.fetch_etf_composition_in_excel(etf_ticker)

    print(f"ETF Composition for {etf_ticker}:\n")
    print(df.head())  # Print first few rows of the DataFrame