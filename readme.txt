# **TTF Futures Case Study - Final Submission**

## **Overview**

This is my submission for the Statkraft Data Scientist Case Study. The solution includes:

- A Python module (`ttf_futures.py`) that constructs and queries a data structure for TTF futures contracts.
- A Dash application (`app.py`) that visualizes intraday price movements.
- Pickle-based data storage for efficient querying.
- Support for specific, generic, and monthly generic contracts.
- **Bonus Feature**: Spread contract support (e.g., DEC-JUN, DEC-DEC spreads)

---

## **Project Structure**

```
📁 TTF_Futures_Case_Study
│── app.py                 # Dash application
│── ttf_futures.py         # Data structure module- generates .pkl file
│── requirements.txt       # Required dependencies
│── contract_data.csv      # Intraday trading data/ 30 min bars
│── ttf_calendar.csv       # Expiry calendar for TTF contracts
│── ttf_futures_data.pkl   # auto-generated 
│── README.md              # This document
```

---

## **Installation & Setup**

### **Step 1: Install Dependencies**

Run the following command to install the required Python libraries:

```
pip install -r requirements.txt
```

### **Step 2: Generate the Data Structure**

If `ttf_futures_data.pkl` does not exist, generate it by running:

```
python ttf_futures.py
```

### **Step 3: Run the Dash Application**

Start the visualization app on a local server:

```
python app.py
```

The app will be available at `http://127.0.0.1:8050/`.

---

## **Features Implemented**

### **Part 1: Data Structure (ttf\_futures.py)**

- Parses `ttf_calendar.csv` to extract contract details.
- Supports querying for specific, generic, and monthly generic contracts.
- Implements Pickle serialization for faster access.
- **Bonus**: Supports time spread contracts (e.g., DEC-JUN, DEC-DEC)

### **Part 2: Dash Visualization (app.py)**

- Intraday price visualization for selected TTF contracts.
- Supports security type selection (Specific, Generic, Monthly Generic).
- Includes date selection and multi-day analysis.
- Two visualization types: OHLC chart & Price Change from Previous Close.
- **Bonus**: Spread Analysis tab with spread price visualization and leg comparison.

---

## **Using the Application**

### **Intraday Price Changes Tab**

1. Select a contract type (Specific, Generic, Monthly Generic)
2. Enter the contract code (e.g., "TFM\\J25" or "TFM1")
3. Choose a reference date
4. Select number of days to include in the analysis
5. Choose between "Price Change" or "OHLC" visualizations

### **Spread Analysis Tab (Bonus Feature)**

1. Select a spread type (DEC-JUN, DEC-DEC, JAN-APR)
2. Choose a reference date
3. Select number of days to include in the analysis
4. Choose between "Spread Price" or "Individual Legs" visualizations
   - "Spread Price" shows the price difference between the two contracts
   - "Individual Legs" displays both contract prices and the spread calculation

---

## **Running the Application**

Once dependencies are installed, the application runs in three steps:

1. Generate the data structure using `python ttf_futures.py`.
2. Start the Dash application with `python app.py`.
3. Access the visualization interface in a web browser at `http://127.0.0.1:8050/`.

---

## **Technical Details**

### **Spread Contract Implementation**

The spread contract functionality follows the specifications from the case study:
- Supports spreads like DEC-JUN and DEC-DEC
- Implements the correct logic for determining which contracts to use for each spread
- For example, TFMDECJUN1 refers to the first DEC contract minus the first JUN contract that follows this specific DEC

This implementation does not require any additional dependencies beyond the requirements.txt file.