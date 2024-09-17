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

def search(driver, date):
    """
    Date in mm/dd/yyyy
    """
    print(f"Accessing website to search for date: {date}")
    driver.get("https://merolagani.com/Floorsheet.aspx")
    print("Website accessed.")
    
    try:
        # Wait for the date input element to be present
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/form/div[4]/div[4]/div/div/div[1]/div[4]/input"))
        )
        date_input = driver.find_element(By.XPATH, '/html/body/form/div[4]/div[4]/div/div/div[1]/div[4]/input')
        search_btn = driver.find_element(By.XPATH, '/html/body/form/div[4]/div[4]/div/div/div[2]/a[1]')
        date_input.send_keys(date)
        search_btn.click()
        print("Search button clicked.")
    except NoSuchElementException as e:
        print(f"Error during search: {e}")
        driver.close()
        sys.exit()
    
    # Check for error message
    if driver.find_elements(By.XPATH, "//*[contains(text(), 'Could not find floorsheet matching the search criteria')]"):
        print("No data found for the given search.")
        print("Script Aborted")
        driver.close()
        sys.exit()

def get_page_table(driver, table_class):
    print("Fetching page table.")
    try:
        # Wait for the table to be present
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/form/div[4]/div[5]/div/div[4]/table"))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find("table", {"class": table_class})
        tab_data = [[cell.text.replace('\r', '').replace('\n', '') for cell in row.find_all(["th", "td"])]
                    for row in table.find_all("tr")]
        
        # Log a snapshot of the first few rows
        sample_data = tab_data[:5]
        print(f"Sample data retrieved: {sample_data}")
        
        df = pd.DataFrame(tab_data)
        print("Table fetched successfully.")
        return df
    except Exception as e:
        print(f"Error fetching page table: {e}")
        raise

def scrape_data(driver, date):
    print("Starting data scraping.")
    search(driver, date=date)
    df_list = []
    count = 0
    while True:
        count += 1
        print(f"Scraping page {count}")
        page_table_df = get_page_table(driver, table_class="table table-bordered table-striped table-hover sortable")
        df_list.append(page_table_df)
        try:
            next_btn = driver.find_element(By.LINK_TEXT, 'Next')
            driver.execute_script("arguments[0].click();", next_btn)
            print("Clicked 'Next' button.")
        except NoSuchElementException:
            print("No 'Next' button found. Scraping completed.")
            break
    driver.close()
    # Concatenate all DataFrames in the list into a single DataFrame
    df = pd.concat(df_list, ignore_index=True)
    print("Data scraping completed.")
    return df

def clean_df(df):
    print("Starting data cleaning.")
    new_df = df.drop_duplicates(keep='first')
    new_header = new_df.iloc[0]
    new_df = new_df[1:]
    new_df.columns = new_header
    new_df.drop(["#"], axis=1, inplace=True)
    new_df["Rate"] = new_df["Rate"].apply(lambda x: float(x.replace(",", "")))
    new_df["Amount"] = new_df["Amount"].apply(lambda x: float(x.replace(",", "")))
    print("Data cleaning completed.")
    return new_df

def main():
    print("Script started.")
    options = Options()
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(240)
    date = '09/16/2024'
    search(driver, date)
    df = scrape_data(driver, date)
    final_df = clean_df(df)
    file_name = date.replace("/", "_")
    final_df.to_csv(f"data/{file_name}.csv", index=False)
    print(f"Data saved to data/{file_name}.csv")
    print("Script completed.")

if __name__ == "__main__":
    main()
