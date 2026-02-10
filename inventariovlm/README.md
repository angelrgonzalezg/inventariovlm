# Inventory Management System

## Overview
This project is a simple inventory management system built using Python's Tkinter for the graphical user interface and SQLite for the database. It allows users to manage inventory items, import data from CSV files, and export inventory records.

## Features
- Initialize and manage an SQLite database for inventory items.
- Import inventory data from CSV files.
- Search for items by code.
- Save inventory counts and differences.
- Export inventory data to Excel or CSV formats.
- User-friendly interface for easy interaction.

## Setup Instructions
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/inventariovlm.git
   cd inventariovlm
   ```

2. **Install dependencies:**
   It is recommended to use a virtual environment. You can create one using `venv`:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

   Then install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   Execute the following command to start the application:
   ```bash
   python app.py
   ```

## Usage
- Use the "Import Catalog CSV" button to load inventory data from a CSV file.
- Enter the item code to search for existing items.
- Fill in the quantities for "Magazijn" and "Winkel" and click "Save" to record inventory counts.
- Use the "Export Excel / CSV" button to save the inventory records.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.