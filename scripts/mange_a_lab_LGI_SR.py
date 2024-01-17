from supports import automate_hal, search_for_lab, check_hal_availability
import pandas as pd


# This script will check a research group, LGI-SR, searching for its publication in 2018-2024, and check the papers availability in HAL
# The members of the research team is defined in /data/inputs/lab_data_LGI_SR.xlsx
# We also check the list from HAL with the Stamp "LGI-SR".
# The script will produce a csv file with the results.

if __name__ == '__main__':
    # Generate search query to search for publications from a given lab and a given time range.    
    # Define the range of years.
    search_query_range = 'PUBYEAR > 2017 AND PUBYEAR < 2025'
    # Define differet ways of spelling the affiliation.
    affil_names = ['Centralesupelec', 'CentraleSupelec', 'Centralesupélec', 'CentraleSupélec', 'Centralesupelec', 'centralesupélec',
                'Paris-saclay', 'Paris-Saclay',
                'Laboratoire Genie Industriel']
    # Path to the database of all the researchers from a given lab.
    lab_db_path = './data/inputs/lab_data_LGI_SR.xlsx'
    save_to_path = './data/outputs/scopus_search_results_lgi_sr.csv'

    # lab_db_path = './data/inputs/lab_data.xlsx'
    # save_to_path = './data/outputs/scopus_search_results_lgi.csv'

    # Search for this lab.
    # df_result = search_for_lab(search_query_range, affil_names, lab_db_path, save_to_path)

    df_result = pd.read_csv(save_to_path)

    # Define paths for the input data.
    perso_data_path = './data/inputs/path_and_perso_data.json'
    author_db_path = './data/inputs/auth_db.csv'

    # Define the stamps you want to add to the paper.
    # If you don't want to add stamp: stamps = []
    stamp = 'LGI-SR'
    # stamps = ['LGI'] # Add your stamps here
    # Start processing.
    auto_hal = automate_hal(perso_data_path, author_db_path, stamps='')

    # Get the results from the stamped team.
    results_from_hal_team = auto_hal.reqHalStamp(stamp=stamp, start_year=2018, end_year=2025)
    for i in range(results_from_hal_team[0]):
        if i == 0:
            df_team = pd.DataFrame(results_from_hal_team[1][i])
        else:
            df_team = pd.concat([df_team, pd.DataFrame(results_from_hal_team[1][i])])
    
    # For each paper, check if it existed in HAL and in HAL stamped group.
    for i, doc in df_result.iterrows():
        # Update the iteration index.
        auto_hal.ite = i
        auto_hal.docid = {'eid': doc['eid'], 'doi': doc['doi'], 'doctype': ''}
        print('{}/{} iterations: {}'.format(i+1, len(df_result), doc['eid']))
        # Process the corresponding paper.
        try:
            if auto_hal.verify_if_existed_in_hal(doc):                
                df_result.loc[i, 'status'] = 'Already existed in HAL!'
                # Check if included in the stamped team already.
                paper_title = df_result.loc[i, 'title']
                if df_team['title_s'].str.contains(paper_title, case=False).any():
                    df_result.loc[i, 'stamped team'] = 'Already existed in the stamped team!'
                else:
                    df_result.loc[i, 'stamped team'] = 'Not existed in the stamped team!'
            else:
                df_result.loc[i, 'status'] = 'Not existed in HAL!'
                df_result.loc[i, 'stamped team'] = 'Not existed in the stamped team!'
        except Exception as error:
            print('Error processing paper: {}. Log saved.'.format(doc['eid']))
            print('Error is: {}'.format(error))
            auto_hal.addRow(docId=auto_hal.docid, state='Error processing paper.', treat_info='Error is: {}'.format(error))

    df_result.to_csv(save_to_path)

    


    # # # For debugging: Only upload the first rowRange records.
    # # # Comment this line if you want to upload all the records.
    # rowRange=[0, 5]  

    # # Process the record in the scopus dataset one by one.
    # for i, doc in df_result.iterrows():
    #     # if 'rowRange' in locals():
    #     #     # For debugging: Limit to first rowRange records.
    #     #     if i < min(rowRange) : continue
    #     #     elif i > max(rowRange) : break

    #     # Update the iteration index.
    #     auto_hal.ite = i
    #     print('{}/{} iterations: {}'.format(i+1, len(df_result), doc['eid']))
    #     # Process the corresponding paper.
    #     try:
    #         auto_hal.process_paper_ite(doc)
    #     except Exception as error:
    #         print('Error processing paper: {}. Log saved.'.format(doc['eid']))
    #         print('Error is: {}'.format(error))
    #         auto_hal.addRow(docId=auto_hal.docid, state='Error processing paper.', treat_info='Error is: {}'.format(error))
