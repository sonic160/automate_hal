from supports import automate_hal
from pybliometrics.scopus import ScopusSearch
import pandas as pd


if __name__ == '__main__':
    # Define paths for the input data.
    scopus_filename = "./data/inputs/scopus_results.csv"
    perso_data_path = './data/inputs/path_and_perso_data.json'
    author_db_path = './data/inputs/auth_db.csv'
    
    # Define the stamps you want to add to the paper.
    # If you don't want to add stamp: stamps = []
    stamps = ['LGI-SR', 'CHAIRE-RRSC']

    # For debugging: Only upload the first rowRange records.
    # Comment this line if you want to upload all the records.
    # rowRange=[0, 10] 
    
    # Load the scopus dataset.
    mode = 'csv'
    auto_hal = automate_hal(perso_data_path, author_db_path, stamps, mode)
    publication_list = auto_hal.loadBibliography(scopus_filename)

    # Address the record in the scopus dataset one by one.
    for i, doc in enumerate(publication_list):
        # if 'rowRange' in locals():
        #     # For debugging: Limit to first rowRange records.
        #     if i < min(rowRange) : continue
        #     elif i > max(rowRange) : break
        
        # Update the iteration index.
        auto_hal.ite = i
        print('{}th iterations: {}'.format(i+1, doc['EID']))
        # Process the corresponding paper.
        auto_hal.process_paper_ite(doc)