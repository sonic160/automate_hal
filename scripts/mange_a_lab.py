from supports import automate_hal, search_for_lab, check_hal_availability
import pandas as pd
import numpy as np


if __name__ == '__main__':
    # Generate search query to search for publications from a given lab and a given time range.    
    # Define the range of years.
    search_query_range = 'PUBYEAR > 2017 AND PUBYEAR < 2025'
    # Define differet ways of spelling the affiliation.
    affil_names = ['Centralesupelec', 'CentraleSupelec', 'Centralesupélec', 'CentraleSupélec']
    # Path to the database of all the researchers from a given lab.
    lab_db_path = './data/inputs/lab_data.xlsx'
    save_to_path = './data/outputs/scopus_search_results_lgi.csv'
    # Search for this lab.
    df_result = search_for_lab(search_query_range, affil_names, lab_db_path, save_to_path)

    # df_result = pd.read_csv(save_to_path)

    # Define paths for the input data.
    perso_data_path = './data/inputs/path_and_perso_data.json'
    author_db_path = './data/inputs/auth_db.csv'

    # Define the stamps you want to add to the paper.
    # If you don't want to add stamp: stamps = []
    # stamps = ['LGI-SR', 'CHAIRE-RRSC']
    stamps = ['LGI'] # Add your stamps here
    # Start processing.
    auto_hal = automate_hal(perso_data_path, author_db_path, stamps)
    
    # For each paper, check if it existed in HAL.
    # check_hal_availability(df_result, save_to_path, auto_hal)

    # # For debugging: Only upload the first rowRange records.
    # # Comment this line if you want to upload all the records.
    # rowRange=[49, 400]  

    # Process the record in the scopus dataset one by one.
    for i, doc in df_result.iterrows():
        # if 'rowRange' in locals():
        #     # For debugging: Limit to first rowRange records.
        #     if i < min(rowRange) : continue
        #     elif i > max(rowRange) : break

        # Update the iteration index.
        auto_hal.ite = i
        print('{}/{} iterations: {}'.format(i+1, len(df_result), doc['eid']))
        # Process the corresponding paper.
        try:
            auto_hal.process_paper_ite(doc)
        except Exception as error:
            print('Error processing paper: {}. Log saved.'.format(doc['eid']))
            print('Error is: {}'.format(error))
            auto_hal.addRow(docId=auto_hal.docid, state='Error processing paper.', treat_info='Error is: {}'.format(error))
