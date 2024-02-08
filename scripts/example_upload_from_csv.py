from AutomateHal import AutomateHal
from pybliometrics.scopus import ScopusSearch
import pandas as pd


if __name__ == '__main__':
    # Define paths for the input data.
    scopus_filename = "./data/inputs/scopus_results.csv"
    perso_data_path = './data/inputs/path_and_perso_data.json'
    author_db_path = './data/inputs/auth_db.csv'
    # affil_db_path = './data/inputs/affiliation_db.csv'
    affil_db_path = ''
    
    # Define the stamps you want to add to the paper.
    # If you don't want to add stamp: stamps = []
    # stamps = ['LGI-SR', 'CHAIRE-RRSC']
    stamps = [] # Add your stamps here

    # For debugging: Only upload the first rowRange records.
    # Comment this line if you want to upload all the records.
    # rowRange=[0, 10] 
    
    # Load the scopus dataset.
    mode = 'csv'
    auto_hal = AutomateHal(perso_data_path=perso_data_path, affil_db_path=affil_db_path,
				author_db_path=author_db_path, stamps=stamps, mode=mode)
    df_result = pd.read_csv(scopus_filename)

    # For debugging: Only upload the first rowRange records.
    # Comment this line if you want to upload all the records.
    rowRange=[0, 10]
    auto_hal.debug_affiliation_search = False
    auto_hal.debug_hal_upload = False
    auto_hal.allow_create_new_affiliation = False

    auto_hal.process_papers(df_result=df_result)
