from supports import automate_hal
from pybliometrics.scopus import ScopusSearch
import pandas as pd


if __name__ == '__main__':
    # Define search query.
    # search_query = 'AU-ID(55659850100) OR AU-ID(55348807500) OR AU-ID(7102745133) AND PUBYEAR > 2017 AND PUBYEAR < 2025 AND AFFIL (centralesupelec)'
    search_query = 'AU-ID(55348807500) AND PUBYEAR > 2016 AND PUBYEAR < 2025'
    
    results = ScopusSearch(search_query, view='COMPLETE', refresh=True)
    df_result = pd.DataFrame(results.results)
    df_result.to_csv('./data/outputs/scopus_search_results.csv', index=False)

    # df_result = pd.read_csv('./data/outputs/scopus_search_results.csv')

    df_result.fillna(value='', inplace=True)

    # Define paths for the input data.
    perso_data_path = './data/inputs/path_and_perso_data.json'
    author_db_path = './data/inputs/auth_db.csv'

    # Define the stamps you want to add to the paper.
    # If you don't want to add stamp: stamps = []
    # stamps = ['LGI-SR', 'CHAIRE-RRSC']
    stamps = [] # Add your stamps here

    # # For debugging: Only upload the first rowRange records.
    # # Comment this line if you want to upload all the records.
    # rowRange=[30, 100]

    # Load the scopus dataset.
    auto_hal = automate_hal(perso_data_path, author_db_path, stamps)    

    # Address the record in the scopus dataset one by one.
    n = len(df_result)
    for i, doc in df_result.iterrows():
        # if 'rowRange' in locals():
        #     # For debugging: Limit to first rowRange records.
        #     if i < min(rowRange) : continue
        #     elif i > max(rowRange) : break
        
        # Update the iteration index.
        auto_hal.ite = i
        print('{}/{} iterations: {}'.format(i+1, n, doc['eid']))
        # Process the corresponding paper.
        try:
            auto_hal.process_paper_ite(doc)
        except:
            print('Error processing paper: {}. Log saved.'.format(doc['eid']))
