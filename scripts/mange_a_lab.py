from supports import automate_hal
from pybliometrics.scopus import ScopusSearch
import pandas as pd
import numpy as np


def search_for_lab(search_query_range, affil_names, lab_db_path, save_to_path):
    '''
    Search for all the publications from a given lab, and in a given time range.

    Parameters:
    - search_query_range: string
        The search query range.
    - affil_names: list of strings
        The list of affiliation names.
    - lab_db_path: string
        The path to the lab database.

    Returns:
    - df_result: A dataframe of the results.
    '''

    search_query_affil = '('
    for affil_name in affil_names[:-2]:
        search_query_affil += 'AFFIL ({}) OR '.format(affil_name)
    search_query_affil += 'AFFIL ({}))'.format(affil_names[-1])

    lab_data = pd.read_excel(lab_db_path)
    search_query_author = '( '
    for index, row in lab_data.iterrows():
        if not np.isnan(row['Scopus id']):
            search_query_author += 'AU-ID({}) OR '.format(int(row['Scopus id']))
        else:
            search_query_author += '(AUTHLASTNAME({}) AND AUTHFIRST({})) OR '.format(row['Family name'], row['First name'][0])
    search_query_author = search_query_author[:-4]
    search_query_author += ')'

    search_query = search_query_range +' AND '+ search_query_affil +' AND '+ search_query_author
    
    results = ScopusSearch(search_query, view='COMPLETE', refresh=True)
    df_result = pd.DataFrame(results.results)
    df_result.to_csv(save_to_path, index=False)

    df_result.fillna(value='', inplace=True)
    
    return df_result


def check_hal_availability(df_result, save_to_path, auto_hal):
    # Iterate for all the papers and check if they are in HAL.
    for i, doc in df_result.iterrows():
        # Update the iteration index.
        auto_hal.ite = i
        print('{}/{} iterations: {}'.format(i+1, len(df_result), doc['eid']))
        # Process the corresponding paper.
        idInHal = auto_hal.reqWithIds(doc['doi'])
        if idInHal[0] > 0:
            print(f"already in HAL")
            df_result.loc[i, 'status'] = 'Already existed in HAL'
        else:
            try:
                titleInHal = auto_hal.reqWithTitle(doc['title'])
            except:
                df_result.loc[i, 'status'] = 'Error using auto_hal.reqWithTitle!'
                continue

            if titleInHal[0] > 0:
                print(f"already in HAL")
                df_result.loc[i, 'status'] = 'Already existed in HAL'
            else:
                print(f"Not existed in HAL")
                df_result.loc[i, 'status'] = 'Not existed in HAL'
    
    # Save the results.
    df_result.to_csv(save_to_path, index=False)


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
