import pandas as pd
# Set decimal places to 8 for more accuracy
pd.set_option('display.float_format', '{:.8f}'.format)


class GetEtfComposition:

    def __init__(self):
        
        self.base_url = "https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/"

    def fetch_etf_composition_to_df(self, etf_ticker):
        """
        Fetch ETF composition Excel file for a given ETF ticker.
        :param etf_ticker: ETF ticker symbol
        :return: DataFrame with ETF composition data
        """
        etf_holdings = f"holdings-daily-us-en-{etf_ticker.lower()}.xlsx"
        etf_navhist = f"navhist-us-en-{etf_ticker.lower()}.xlsx"
        print(etf_holdings, etf_navhist)

        etf_holdings_url = self.base_url + etf_holdings
        etf_navhist_url = self.base_url + etf_navhist
        
        try: 
            
            metadata_df = pd.read_excel(etf_holdings_url, nrows = 3, header = None)

            etf_name = str(metadata_df.iloc[0, 1]).strip() if len(metadata_df.columns) > 1 else ""
            ticker = str(metadata_df.iloc[1, 1]).strip() if len(metadata_df.columns) > 1 else ""
            text_date = str(metadata_df.iloc[2, 1]).strip() if len(metadata_df.columns) > 1 else ""

            if "As of" in text_date:
                text_date = text_date.replace("As of", "").strip()
            date_obj = pd.to_datetime(text_date, format = '%d-%b-%Y')
            
            # Date in YYYY-MM-DD format
            composition_date = date_obj.strftime('%Y-%m-%d') 

        except Exception as e:
            print(f"Error fetching metadata for {etf_ticker} from {etf_holdings_url}: {e}")
            return None

        try: 
            holdings_df = pd.read_excel(etf_holdings_url, header = 4)

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

            try:
                # Read the navhist Excel: skip first 3 metadata rows, row 4 = headers, read up to 10 data rows
                navhist_df = pd.read_excel(etf_navhist_url, header = 3, nrows = 10)

                # Strip whitespace from column names to avoid mismatches (e.g. "NAV " vs "NAV")
                navhist_df.columns = navhist_df.columns.str.strip()

                # Convert Date column to YYYY-MM-DD string format to match composition_date
                navhist_df['Date'] = pd.to_datetime(navhist_df['Date']).dt.strftime('%Y-%m-%d')

                # Filter navhist_df for the row where Date == composition_date (from holdings file)
                matched_row = navhist_df[navhist_df['Date'] == composition_date]

                if not matched_row.empty:
                    # Date match found — use this row's NAV data
                    nav_row = matched_row.iloc[0]
                else:
                    # No matching date — skip this ETF entirely, dates are out of sync
                    print(f"Skipped {etf_ticker}: NAV date mismatch (holdings={composition_date}, latest navhist={navhist_df['Date'].iloc[0]})")
                    return None

                # Assign the 3 scalar values as new columns in holdings_df.
                # Since nav_row is a single pandas Series, assigning a scalar to a DataFrame column
                # broadcasts that value to every row — effectively merging fund-level data
                # into each component row without needing pd.merge or pd.concat.
                holdings_df['nav'] = nav_row.get('NAV', None)
                holdings_df['shares_outstanding'] = pd.to_numeric(nav_row.get('Shares Outstanding', None), errors = 'coerce')
                holdings_df['total_net_assets'] = pd.to_numeric(nav_row.get('Total Net Assets', None), errors = 'coerce')
            except Exception as e:
                # If navhist fetch/parse fails entirely, skip this ETF
                print(f"Skipped {etf_ticker}: Could not fetch NAV history - {e}")
                return None

            # Reorder columns: place metadata + navhist columns first, then component-level columns
            metadata_cols = ['etf_name', 'etf_ticker', 'composition_date', 'number_of_holdings',
                             'nav', 'shares_outstanding', 'total_net_assets']
            other_cols = [col for col in holdings_df.columns if col not in metadata_cols]
            holdings_df = holdings_df[metadata_cols + other_cols]

            return holdings_df
        
        except Exception as e: 
            print(f"Error fetching components for {etf_ticker} from {etf_holdings_url}: {e}")
            return None

if __name__ == "__main__":
    get = GetEtfComposition()

    etf_ticker = "SPY"  # Example ETF ticker
    print("Fetching ETF composition for:", etf_ticker)
    print("running the function")
    df = get.fetch_etf_composition_to_df(etf_ticker)
    
    print(f"ETF Composition for {etf_ticker}:\n")

    # Save to CSV to verify all data is captured
    # output_file = f"{etf_ticker}_composition.csv"
    # df.to_csv(output_file, index=False)
    # print(f"Saved full composition to: {output_file}")

    # Display first and last few rows
    print("\nFirst 5 rows:")
    print(df.head().to_string())
    print("\nLast 5 rows:")
    print(df.tail().to_string())
    print(f"\nTotal components found: {len(df)}")