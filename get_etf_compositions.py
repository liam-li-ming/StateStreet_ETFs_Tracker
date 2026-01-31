import pandas as pd


class GetEtfCompositions:

    def __init__(self):
        
        self.base_url = "https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/"


    def fetch_etf_composition_to_df(self, etf_ticker):
        """
        Fetch ETF composition Excel file for a given ETF ticker.
        :param etf_ticker: ETF ticker symbol
        :return: DataFrame with ETF composition data
        """

        etf_excel = f"holdings-daily-us-en-{etf_ticker.lower()}.xlsx"
        etf_url = self.base_url + etf_excel
        print(etf_url)
        
        try: 
            
            metadata_df = pd.read_excel(etf_url, nrows = 3, header = None)

            etf_name = str(metadata_df.iloc[0, 1]).strip() if len(metadata_df.columns) > 1 else ""
            ticker = str(metadata_df.iloc[1, 1]).strip() if len(metadata_df.columns) > 1 else ""
            text_date = str(metadata_df.iloc[2, 1]).strip() if len(metadata_df.columns) > 1 else ""

            if "As of" in text_date:
                text_date = text_date.replace("As of", "").strip()
            date_obj = pd.to_datetime(text_date, format = '%d-%b-%Y')
            
            # Date in YYYY-MM-DD format
            composition_date = date_obj.strftime('%Y-%m-%d') 

        except Exception as e:
            print(f"Error fetching metadata for {etf_ticker} from {etf_url}: {e}")
            return None

        try: 
            holdings_df = pd.read_excel(etf_url, header = 4)

            # to check where the data ends
            end_keywords = ['State Street Global Advisors', 'Past performance', 'Portfolio holdings', 'Bonds generally']

            last_valid_row = len(holdings_df) 
            for index, row in holdings_df.iterrows(): 

                name_val = str(row.get('Name', ''))
                ticker_val = str(row.get('Ticker', ''))

                # If Name contains footer keywords, stop here
                if any(keyword.lower() in name_val.lower() for keyword in end_keywords):
                    last_valid_row = index
                    break
            
                # If we hit a row where Name and Ticker are both NaN/empty
                if pd.isna(row.get('Name')) and pd.isna(row.get('Ticker')):
                    last_valid_row = index
                    break

            holdings_df = holdings_df.iloc[:last_valid_row]

            holdings_df = holdings_df.rename(columns = {
                'Name': 'component_name',
                'Ticker': 'ticker',
                'Identifier': 'identifier',
                'SEDOL': 'sedol',
                'Weight': 'weight',
                'Sector': 'sector',
                'Shares Held': 'shares',
                'Local Currency': 'currency'
            })

            # clean column names
            holdings_df['ticker'] = holdings_df['ticker'].astype(str).str.strip().str.upper()
            holdings_df['component_name'] = holdings_df['component_name'].astype(str).str.strip()

            if 'weight' in holdings_df.columns:
                # Weight is already in decimal format in this file
                holdings_df['weight'] = pd.to_numeric(holdings_df['weight'], errors = 'coerce').round(8)

            if 'shares' in holdings_df.columns:
                holdings_df['shares'] = pd.to_numeric(holdings_df['shares'], errors = 'coerce').round(8)

            # Add ETF metadata columns
            holdings_df['etf_name'] = etf_name
            holdings_df['etf_ticker'] = ticker
            holdings_df['composition_date'] = composition_date
            holdings_df['number_of_holdings'] = len(holdings_df)

            # Reorder columns so metadata columns are first
            metadata_cols = ['etf_name', 'etf_ticker', 'composition_date', 'number_of_holdings']
            other_cols = [col for col in holdings_df.columns if col not in metadata_cols]
            holdings_df = holdings_df[metadata_cols + other_cols]

            return holdings_df
        
        except Exception as e: 
            print(f"Error fetching components for {etf_ticker} from {etf_url}: {e}")
            return None

if __name__ == "__main__":
    get = GetEtfCompositions()

    etf_ticker = "spy"  # Example ETF ticker
    print("Fetching ETF composition for:", etf_ticker)
    print("running the function")
    df = get.fetch_etf_composition_to_df(etf_ticker)
    
    print(f"ETF Composition for {etf_ticker}:\n")

    print(df.to_string())
    print(f"\nTotal components found: {len(df)}")