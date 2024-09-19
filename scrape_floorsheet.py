from selenium import webdriver
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys

def log(message):
    """
    Custom log function for console output with timestamps.
    """
    print(f"[{datetime.now()}] {message}")


def search(driver):
    """
    Navigates to the price history and selects 50 entries.
    """
    log("Navigating to the CGH company page.")
    driver.get("https://www.sharesansar.com/company/cgh")
    
    log("Waiting for the 'Price History' button to appear.")
    price_history_btn = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="btn_cpricehistory"]'))
    )
    price_history_btn.click()
    log("'Price History' button clicked.")
    
    log("Waiting for the entries dropdown to appear.")
    select_entries = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[2]/div/section[2]/div[3]/div/div/div/div[2]/div/div[1]/div[2]/div/div[8]/div/div/div[1]/label/select')
        )
    )
    select_entries.click()
    log("Entries dropdown clicked. Now selecting '50 entries'.")
    
    option_50 = driver.find_element(By.XPATH, '/html/body/div[2]/div/section[2]/div[3]/div/div/div/div[2]/div/div[1]/div[2]/div/div[8]/div/div/div[1]/label/select/option[3]')
    option_50.click()  # Choose the "50 entries" option
    
    log("'50 entries' option selected.")
    
    log("Waiting for the price history table to load.")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="myTableCPriceHistory"]'))
    )
    log("Price history table loaded.")


def get_page_table(driver):
    """
    Extract table data from the price history table.
    """
    log("Extracting data from the price history table.")
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find the table using the specified XPath
    table = soup.find("table", {"id": "myTableCPriceHistory"})
    
    # Extract table data
    tab_data = [[cell.text.replace('\r', '').replace('\n', '').strip() for cell in row.find_all(["th", "td"])]
                for row in table.find_all("tr")]
    
    log("Table data extracted.")
    df = pd.DataFrame(tab_data)
    return df


def scrape_data(driver):
    """
    Scrape all pages and return the concatenated DataFrame.
    """
    df = pd.DataFrame()
    count = 0
    while True:
        count += 1
        log(f"Scraping page {count}.")
        
        # Get the table data
        page_table_df = get_page_table(driver)
        
        # Append to the overall DataFrame
        df = pd.concat([df, page_table_df], ignore_index=True)
        
        # Log a snippet of the data for this page
        log(f"Preview of data from page {count}:")
        log(page_table_df.head().to_string(index=False))  # Print a snippet of the table
        
        try:
            # Click on the "Next" button using the provided XPath
            next_btn = driver.find_element(By.XPATH, '//*[@id="myTableCPriceHistory_next"]')
            
            # Check if the "Next" button is disabled
            if "disabled" in next_btn.get_attribute("class"):
                log(f"No more pages to scrape. Scraping completed at page {count}.")
                break  # Exit the loop if there's no more pages
            
            # Click "Next" to go to the next page
            driver.execute_script("arguments[0].click();", next_btn)
            log(f"Clicked 'Next' button for page {count+1}.")
            
            # Wait for the table to refresh/load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="myTableCPriceHistory"]'))
            )
        except NoSuchElementException:
            log("No 'Next' button found. Scraping finished.")
            break

    driver.close()
    log("Browser closed.")
    return df


def clean_df(df):
    """
    Clean up the DataFrame: drop duplicates, set the correct headers, and format the columns.
    """
    log("Cleaning up the DataFrame.")
    
    # Drop duplicates
    new_df = df.drop_duplicates(keep='first')

    # Use the first row as the new header
    new_header = new_df.iloc[0]  # Get the first row as the header
    new_df = new_df[1:]  # Data without the header row
    new_df.columns = new_header  # Set the new header
    
    # Log the current state of the dataframe
    log(f"DataFrame columns after setting header: {new_df.columns}")

    # Drop the "S.N." column if it exists (previously "#")
    if "S.N." in new_df.columns:
        new_df.drop(["S.N."], axis=1, inplace=True)
        log("'S.N.' column dropped.")
    
    # Handle data conversion for numeric columns
    log("Converting 'Qty' and 'Turnover' columns to float.")
    
    # Convert numeric columns like "Qty" and "Turnover" to float after removing commas
    new_df["Qty"] = new_df["Qty"].apply(lambda x: float(x.replace(",", "")))
    new_df["Turnover"] = new_df["Turnover"].apply(lambda x: float(x.replace(",", "")))
    
    log("Data cleaning completed.")
    return new_df



def main():
    log("Starting the scraping process.")
    
    # Setup headless Chrome options
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)  # Start the browser
    driver.set_page_load_timeout(240)
    
    # Perform search and scraping
    search(driver)
    df = scrape_data(driver)
    
    # Clean the DataFrame
    final_df = clean_df(df)
    
    # Save the cleaned data to a CSV file
    date = datetime.today().strftime('%m/%d/%Y').replace("/", "_")
    file_name = f"Pdata/{date}.csv"
    
    final_df.to_csv(file_name, index=False)  # Save file
    
    log(f"Data saved to {file_name}.")
    log("Scraping process completed successfully.")


if __name__ == "__main__":
    main()
