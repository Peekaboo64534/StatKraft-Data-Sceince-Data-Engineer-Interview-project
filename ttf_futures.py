import pandas as pd
import re
import pickle
import os
from datetime import datetime
from enum import Enum
from typing import Optional, Union, Tuple

class SecurityType(Enum):
    SPECIFIC = "specific"
    GENERIC = "generic"
    MONTHLY_GENERIC = "monthly_generic"
    SPREAD = "spread"  # New type for spreads

class DataStore:
    def __init__(self, csv_file=None, pickle_file=None):
        # Load either from CSV or from a serialized pickle file
        if pickle_file and os.path.exists(pickle_file):
            self.load_from_pickle(pickle_file)
        elif csv_file:
            # Load and clean the data
            self.df = pd.read_csv(csv_file, delimiter=';')
            self.df = self.clean_data()
        else:
            raise ValueError("Either csv_file or pickle_file must be provided")
        
    def parse_contract(self, tfm_code):
        """
        Parse TFM_Code to extract the month and year.
        """
        match = re.match(r'.*TFM\\([FGHJKMNQUVXZ])(\d{2})', tfm_code)
        if match:
            month_code, year = match.groups()
            month_map = {
                'F': 'January', 'G': 'February', 'H': 'March', 'J': 'April',
                'K': 'May', 'M': 'June', 'N': 'July', 'Q': 'August',
                'U': 'September', 'V': 'October', 'X': 'November', 'Z': 'December'
            }
            month = month_map[month_code]
            return f"{month} 20{year}"
        return None
    
    def clean_data(self):
        """
        Cleans and formats the data.
        """
        # Remove "ENDEX::F:" prefix from TFM_Code
        self.df['TFM_Code_original'] = self.df['TFM_Code']  # Keep original for reference
        self.df['TFM_Code'] = self.df['TFM_Code'].str.replace('ENDEX::F:', '', regex=False)
        
        # Extract delivery month using TFM_Code
        self.df['delivery_month'] = self.df['TFM_Code'].apply(self.parse_contract)
        
        # Standardize dates
        self.df['contract_month'] = pd.to_datetime(self.df['contract_month']).dt.strftime('%Y-%m')
        self.df['expiry_date'] = pd.to_datetime(self.df['expiry_date']).dt.strftime('%Y-%m-%d')
        
        # Extract month name for monthly generic queries
        self.df['month_name'] = pd.to_datetime(self.df['delivery_month'], errors='coerce').dt.strftime('%B')
        
        # Extract contract year 
        self.df['contract_year'] = pd.to_datetime(self.df['contract_month']).dt.year
        
        # Retain relevant columns
        self.df = self.df[['TFM_Code', 'TFM_Code_original', 'delivery_month', 
                           'contract_month', 'expiry_date', 'month_name', 'contract_year']]
        
        return self.df
    
    def query(self, security: str, security_type: Union[SecurityType, str], point_in_time: Optional[Union[str, Tuple[str, str]]] = None):
        """
        Unified query interface that accepts three parameters:
        - security:  "TFM1", "TFM\\J25", "TFMAPR1", "TFMDECJUN1"
        - security_type: specific, generic, monthly_generic, spread
        - point_in_time: Optional date or date range for filtering results
        Can be a single date string or a tuple of (start_date, end_date)
        
        Returns a  DataFrame with the query results.
        """
        # Convert string security_type to enum if needed
        if isinstance(security_type, str):
            security_type = SecurityType(security_type)
        
        # Create a copy of the DataFrame to work with
        result_df = self.df.copy()
        
        # Apply point-in-time filtering if provided
        reference_date = None
        if point_in_time:
            if isinstance(point_in_time, tuple) and len(point_in_time) == 2:
                start_date, end_date = point_in_time
                reference_date = pd.to_datetime(start_date)
                result_df = result_df[
                    (pd.to_datetime(result_df['expiry_date']) >= pd.to_datetime(start_date)) &
                    (pd.to_datetime(result_df['expiry_date']) <= pd.to_datetime(end_date))
                ]
            else:
                # Single date point-in-time query
                reference_date = pd.to_datetime(point_in_time)
                result_df = result_df[pd.to_datetime(result_df['expiry_date']) >= reference_date]
        
        # Apply security-specific filtering based on type
        if security_type == SecurityType.SPECIFIC:
            # Handle case with or without prefix
            clean_security = security.replace('ENDEX::F:', '', 1)
            return result_df[result_df['TFM_Code'] == clean_security]
        
        elif security_type == SecurityType.GENERIC:
            # Extract sequence number from generic code (e.g., TFM1 -> 1)
            match = re.match(r'TFM(\d+)', security)
            if match:
                sequence_number = int(match.group(1))
                return result_df.sort_values('contract_month').iloc[sequence_number-1:sequence_number]
            return pd.DataFrame()  # Return empty DataFrame if no match
        
        elif security_type == SecurityType.MONTHLY_GENERIC:
            # Handle monthly generics like TFMAPR1
            month_pattern = r'TFM([A-Za-z]+)(\d+)'
            match = re.match(month_pattern, security)
            
            if match:
                month_abbr, sequence_str = match.groups()
                sequence_number = int(sequence_str)
                
                # Map month abbreviation to full month name
                month_abbr = month_abbr.upper()
                month_map = {
                    'JAN': 'January', 'FEB': 'February', 'MAR': 'March', 'APR': 'April',
                    'MAY': 'May', 'JUN': 'June', 'JUL': 'July', 'AUG': 'August',
                    'SEP': 'September', 'OCT': 'October', 'NOV': 'November', 'DEC': 'December'
                }
                
                if month_abbr in month_map:
                    month_name = month_map[month_abbr]
                    
                    print(f"Looking for {month_name} contract, sequence {sequence_number}")
                    
                    # Store the month name in the result attributes for later use
                    month_info = {
                        'month_name': month_name,
                        'month_abbr': month_abbr
                    }
                    
                    # Filter by month name
                    monthly_df = result_df[result_df['month_name'] == month_name]
                    
                    print(f"Found {len(monthly_df)} {month_name} contracts")
                    
                    if reference_date is not None:
                        # Get the reference year
                        reference_year = reference_date.year
                        
                        # Find all contracts for this month that haven't expired yet
                        valid_contracts = monthly_df[
                            pd.to_datetime(monthly_df['expiry_date']) > reference_date
                        ].sort_values('contract_year')
                        
                        print(f"Found {len(valid_contracts)} valid (non-expired) contracts for {month_name}")
                        if not valid_contracts.empty:
                            for i, row in valid_contracts.iterrows():
                                print(f"  - {row['TFM_Code']} expires on {row['expiry_date']}")
                        
                        # Add metadata about expired contracts
                        metadata = {
                            'expired_contracts': [],
                            'next_available': None,
                            'month_info': month_info
                        }
                        
                        # Check if the current year's contract has expired
                        current_year_contract = monthly_df[monthly_df['contract_year'] == reference_year]
                        if not current_year_contract.empty:
                            current_year_expiry = pd.to_datetime(current_year_contract['expiry_date'].iloc[0])
                            if current_year_expiry < reference_date:
                                # Current year contract has expired
                                metadata['expired_contracts'].append({
                                    'year': reference_year,
                                    'expiry_date': current_year_expiry.strftime('%Y-%m-%d')
                                })
                                
                                print(f"NOTE: {month_name} {reference_year} contract has expired on {current_year_expiry.strftime('%Y-%m-%d')}")
                        
                        # Take the Nth contract that hasn't expired
                        if len(valid_contracts) >= sequence_number:
                            result = valid_contracts.iloc[sequence_number-1:sequence_number].copy()
                            
                            # Add metadata about the selected contract
                            if not result.empty:
                                metadata['next_available'] = {
                                    'year': result['contract_year'].iloc[0],
                                    'expiry_date': result['expiry_date'].iloc[0]
                                }
                                
                                print(f"Using {month_name} {result['contract_year'].iloc[0]} (expires on {result['expiry_date'].iloc[0]})")
                            
                            # Add metadata to the result
                            result.attrs['metadata'] = metadata
                            return result
                        else:
                            print(f"WARNING: Not enough valid contracts for {month_name} (sequence {sequence_number}). Only found {len(valid_contracts)}.")
                            return pd.DataFrame()  # Not enough valid contracts
                            
                    # If no reference date, just sort by year and take the Nth contract
                    sorted_df = monthly_df.sort_values('contract_year')
                    if len(sorted_df) >= sequence_number:
                        result = sorted_df.iloc[sequence_number-1:sequence_number].copy()
                        # Add basic metadata
                        result.attrs['metadata'] = {'month_info': month_info}
                        return result
            
            print(f"Could not match {security} as a monthly generic code")
            return pd.DataFrame()  # Return empty DataFrame if no match
            
        elif security_type == SecurityType.SPREAD:
            # Handle spread codes like TFMDECJUN1
            return self.query_spread(security, point_in_time)
        
        # Default fallback
        return pd.DataFrame()
    
    def query_spread(self, spread_code: str, point_in_time: Optional[str] = None):
        """
        Query for spread contracts (e.g., TFMDECJUN1, TFMDECDEC1)
        Params:
        spread_code : str
            The spread code, e.g., "TFMDECJUN1" or "TFMDECDEC1"
        point_in_time : str, optional
            The reference date for the spread 
        Returns:
        pd.DataFrame
            DataFrame with  specific contracts that make up the spread
        """
        # Parse the spread code (e.g., TFMDECJUN1)
        spread_pattern = r'TFM([A-Z]{3})([A-Z]{3})(\d+)'
        match = re.match(spread_pattern, spread_code)
        
        if not match:
            print(f"Invalid spread code format: {spread_code}")
            return pd.DataFrame()
        
        # Extract the two months and sequence number
        month1_abbr, month2_abbr, seq_num = match.groups()
        sequence_number = int(seq_num)
        
        # Map month abbreviations to full month names
        month_map = {
            'JAN': 'January', 'FEB': 'February', 'MAR': 'March', 'APR': 'April',
            'MAY': 'May', 'JUN': 'June', 'JUL': 'July', 'AUG': 'August',
            'SEP': 'September', 'OCT': 'October', 'NOV': 'November', 'DEC': 'December'
        }
        
        if month1_abbr not in month_map or month2_abbr not in month_map:
            print(f"Invalid month abbreviation in spread code: {spread_code}")
            return pd.DataFrame()
        
        # Get the full month names
        month1_full = month_map[month1_abbr]
        month2_full = month_map[month2_abbr]
        
        print(f"Processing spread {spread_code}: {month1_full}-{month2_full} (sequence {sequence_number})")
        
        # Query for the first month contract using monthly generic
        month1_query = f"TFM{month1_abbr}{sequence_number}"
        contract1 = self.query(month1_query, SecurityType.MONTHLY_GENERIC, point_in_time)
        
        if contract1.empty:
            print(f"Could not find first leg of spread: {month1_query}")
            return pd.DataFrame()
        
        # For the second leg, we need special logic
        # Determine the year for the second contract based on spread rules
        
        # Get the year of the first contract
        if 'contract_year' in contract1.columns and not contract1['contract_year'].empty:
            year1 = contract1['contract_year'].iloc[0]
            
            # For DEC-JUN: If month2 comes before month1 in calendar, use next year
            # For DEC-DEC: Always use next year for month2
            month_order = list(month_map.values())
            month1_idx = month_order.index(month1_full)
            month2_idx = month_order.index(month2_full)
            
            # If month2 comes before or is the same as month1 in the calendar, use next year
            year2 = year1
            if month2_idx <= month1_idx:
                year2 = year1 + 1
                print(f"Second leg will use next year: {year2} (based on calendar order)")
            
            # Find the specific contract for month2 and year2
            # First filter by month name
            month2_contracts = self.df[self.df['month_name'] == month2_full]
            # Then filter by year
            contract2_candidates = month2_contracts[month2_contracts['contract_year'] == year2]
            
            if contract2_candidates.empty:
                print(f"Could not find second leg for spread: {month2_full} {year2}")
                return pd.DataFrame()
            
            # Get the specific contract for the second leg
            contract2 = contract2_candidates.iloc[0:1]
            
            print(f"Spread legs: {contract1['TFM_Code'].iloc[0]} and {contract2['TFM_Code'].iloc[0]}")
            
            # Create a result DataFrame with both contracts
            result = pd.DataFrame({
                'spread_code': [spread_code],
                'contract1_code': [contract1['TFM_Code'].iloc[0]],
                'contract1_expiry': [contract1['expiry_date'].iloc[0]],
                'contract2_code': [contract2['TFM_Code'].iloc[0]],
                'contract2_expiry': [contract2['expiry_date'].iloc[0]],
                'spread_type': [f"{month1_abbr}-{month2_abbr}"]
            })
            
            # Add metadata about the spread
            result.attrs['metadata'] = {
                'spread_type': f"{month1_abbr}-{month2_abbr}",
                'leg1': {
                    'code': contract1['TFM_Code'].iloc[0],
                    'month': month1_full,
                    'year': year1
                },
                'leg2': {
                    'code': contract2['TFM_Code'].iloc[0],
                    'month': month2_full,
                    'year': year2
                }
            }
            
            return result
        
        print("Could not determine year for first contract leg")
        return pd.DataFrame()
    
    def get_spread_prices(self, spread_result, intraday_data):
        """
        Calculate spread prices from intraday data for the two contracts in the spread
        Params:
        spread_result : pd.DataFrame
            The result from query_spread
        intraday_data : pd.DataFrame
            DataFrame with intraday price data    
        Returns:
        pd.DataFrame
            DataFrame with intraday spread prices
        """
        if spread_result.empty or 'contract1_code' not in spread_result.columns:
            print("Invalid spread result provided")
            return pd.DataFrame()
        
        # Get the specific contract codes
        contract1_code = spread_result['contract1_code'].iloc[0]
        contract2_code = spread_result['contract2_code'].iloc[0]
        
        print(f"Calculating spread prices for {contract1_code} - {contract2_code}")
        
        # Filter intraday data for each contract
        contract1_data = intraday_data[intraday_data['symbol'] == contract1_code].copy()
        contract2_data = intraday_data[intraday_data['symbol'] == contract2_code].copy()
        
        if contract1_data.empty:
            print(f"No intraday data found for first leg: {contract1_code}")
            return pd.DataFrame()
        
        if contract2_data.empty:
            print(f"No intraday data found for second leg: {contract2_code}")
            return pd.DataFrame()
        
        # Create Timestamp column if it doesn't exist
        if 'Timestamp' not in contract1_data.columns:
            # Make sure Date column is datetime
            if not pd.api.types.is_datetime64_any_dtype(contract1_data['Date']):
                contract1_data['Date'] = pd.to_datetime(contract1_data['Date'])
            contract1_data['Timestamp'] = pd.to_datetime(contract1_data['Date'].astype(str) + ' ' + contract1_data['Time'])
        
        if 'Timestamp' not in contract2_data.columns:
            # Make sure Date column is datetime
            if not pd.api.types.is_datetime64_any_dtype(contract2_data['Date']):
                contract2_data['Date'] = pd.to_datetime(contract2_data['Date'])
            contract2_data['Timestamp'] = pd.to_datetime(contract2_data['Date'].astype(str) + ' ' + contract2_data['Time'])
        
        # Merge the data on Timestamp
        # Take only the columns we need to avoid duplicate column names
        spread_data = pd.merge(
            contract1_data[['Timestamp', 'Date', 'Time', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']],
            contract2_data[['Timestamp', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']],
            on='Timestamp',
            suffixes=('_1', '_2')
        )
        
        if spread_data.empty:
            print("No matching timestamps between the two contracts")
            return pd.DataFrame()
        
        # Calculate spread prices (leg1 - leg2)
        spread_data['OPEN'] = spread_data['OPEN_1'] - spread_data['OPEN_2']
        spread_data['HIGH'] = spread_data['HIGH_1'] - spread_data['HIGH_2']
        spread_data['LOW'] = spread_data['LOW_1'] - spread_data['LOW_2']
        spread_data['CLOSE'] = spread_data['CLOSE_1'] - spread_data['CLOSE_2']
        spread_data['VOLUME'] = (spread_data['VOLUME_1'] + spread_data['VOLUME_2']) / 2  # Average volume
        
        # Add spread metadata
        spread_data['spread_code'] = spread_result['spread_code'].iloc[0]
        spread_data['spread_type'] = spread_result['spread_type'].iloc[0]
        spread_data['contract1_code'] = contract1_code
        spread_data['contract2_code'] = contract2_code
        spread_data['symbol'] = spread_result['spread_code'].iloc[0]  # Use spread code as symbol
        
        # Keep only necessary columns (to match the original intraday data format)
        final_columns = ['Timestamp', 'Date', 'Time', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME', 
                          'symbol', 'spread_code', 'spread_type', 'contract1_code', 'contract2_code']
        
        return spread_data[final_columns]
    
    # Keep the original methods for backward compatibility
    def query_specific(self, tfm_code):
        """
        Query a specific contract by its TFM_Code.
        """
        return self.query(tfm_code, SecurityType.SPECIFIC)
    
    def query_generic(self, sequence_number):
        """
        Query a contract based on its sequence position.
        TFM1 refers to the first active contract.
        """
        return self.query(f"TFM{sequence_number}", SecurityType.GENERIC)
    
    def query_monthly_generic(self, month_name, sequence_number=1):
        """
        Query contracts for a specific month and sequence.
         TFMAPR1 refers to the first active April contract.
        """
        # Convert full month name to abbreviation
        month_abbr_map = {
            'January': 'JAN', 'February': 'FEB', 'March': 'MAR', 'April': 'APR',
            'May': 'MAY', 'June': 'JUN', 'July': 'JUL', 'August': 'AUG',
            'September': 'SEP', 'October': 'OCT', 'November': 'NOV', 'December': 'DEC'
        }
        
        month_abbr = month_abbr_map.get(month_name, month_name[:3].upper())
        return self.query(f"TFM{month_abbr}{sequence_number}", SecurityType.MONTHLY_GENERIC)
    
    def save_to_pickle(self, file_path):
        """
        Serialize the DataStore to disk using pickle.
        Params:
        file_path (str): Path where the pickle file will be saved
        """
        with open(file_path, 'wb') as f:
            pickle.dump(self.df, f)
        print(f"DataStore successfully serialized to {file_path}")
        
    def load_from_pickle(self, file_path):
        """
        Load a serialized DataStore from a pickle file.
        Params:
        file_path (str): Path to the pickle file
        """
        with open(file_path, 'rb') as f:
            self.df = pickle.load(f)

# testing
if __name__ == "__main__":
    # Check if serialized data exists
    pickle_file = "ttf_futures_data.pkl"
    
    if os.path.exists(pickle_file):
        # Load from serialized file
        print(f"Loading from serialized file: {pickle_file}")
        datastore = DataStore(pickle_file=pickle_file)
    else:
        # Initialize the DataStore from CSV
        print("Loading from CSV file and creating new serialized data")
        datastore = DataStore(csv_file="ttf_calendar.csv")
        # Save to disk for future use
        datastore.save_to_pickle(pickle_file)
    
    # Test the monthly generic functionality
    test_date = "2025-01-12"
    security_code = "TFMJAN1"
    monthly_result = datastore.query(security_code, SecurityType.MONTHLY_GENERIC, test_date)
    print(f"\nMonthly Generic Query for {security_code} on {test_date}:")
    print(monthly_result)
    
    if not monthly_result.empty and hasattr(monthly_result, 'attrs') and 'metadata' in monthly_result.attrs:
        metadata = monthly_result.attrs['metadata']
        month_info = metadata.get('month_info', {})
        month_name = month_info.get('month_name', 'Unknown')
        
        if 'expired_contracts' in metadata and metadata['expired_contracts']:
            for expired in metadata['expired_contracts']:
                print(f"Note: {month_name} {expired['year']} contract expired on {expired['expiry_date']}")
        
        if 'next_available' in metadata and metadata['next_available']:
            next_avail = metadata['next_available']
            print(f"Using next available contract: {month_name} {next_avail['year']} (expires on {next_avail['expiry_date']})")
    
    # Test spread functionality
    print("\n----- Testing Spread Functionality -----")
    test_spread = "TFMDECJUN1"
    spread_result = datastore.query(test_spread, SecurityType.SPREAD, test_date)
    print(f"\nSpread Query for {test_spread} on {test_date}:")
    print(spread_result)
    
    if not spread_result.empty and hasattr(spread_result, 'attrs') and 'metadata' in spread_result.attrs:
        spread_metadata = spread_result.attrs['metadata']
        print(f"Spread Type: {spread_metadata['spread_type']}")
        print(f"Leg 1: {spread_metadata['leg1']['code']} ({spread_metadata['leg1']['month']} {spread_metadata['leg1']['year']})")
        print(f"Leg 2: {spread_metadata['leg2']['code']} ({spread_metadata['leg2']['month']} {spread_metadata['leg2']['year']})")