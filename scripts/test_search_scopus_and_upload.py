from AutomateHal import AutomateHal
from pybliometrics.scopus import ScopusSearch
import pandas as pd


if __name__ == '__main__':
    # Define search query.
    search_query = 'AU-ID(55659850100) OR AU-ID(55348807500) OR AU-ID(7102745133) AND PUBYEAR > 2017 AND PUBYEAR < 2025 AND AFFIL (centralesupelec)'
    # search_query = 'AU-ID(55348807500) AND PUBYEAR > 2016 AND PUBYEAR < 2025' # Zhiguo Zeng
    # search_query = 'AU-ID(7005289082) AND PUBYEAR > 2000  AND PUBYEAR < 2025 AND (AFFIL (centralesupelec) OR AFFIL (Supelec))' # Enrico Zio
    # search_query = 'AU-ID(7005289082) AND PUBYEAR > 2000  AND PUBYEAR < 2025' # Enrico Zio
    # search_query = 'AU-ID(6602469780) AND PUBYEAR > 2000 AND PUBYEAR < 2025 AND AFFIL (centralesupelec)' # Bernard Yannou
    # search_query = 'AU-ID(56609542700) AND PUBYEAR > 2000 AND PUBYEAR < 2025 AND (AFFIL (centralesupelec) OR AFFIL (Supelec))' # Yanfu Li
    # search_query = 'AU-ID(14049106600) AND PUBYEAR > 2000  AND PUBYEAR < 2025 AND (AFFIL (centralesupelec) OR AFFIL (Supelec))' # Nicola Pedroni
    # search_query = 'AU-ID(7102745133) AND PUBYEAR > 2000 AND PUBYEAR < 2025' # Anne Barros
    # search_query = 'EID (2-s2.0-85165459332)'

    results = ScopusSearch(search_query, view='COMPLETE', refresh=True)
    df_result = pd.DataFrame(results.results)
    # df_result.to_csv('./data/outputs/scopus_search_results.csv', index=False)

    # df_result = pd.read_csv('./data/outputs/scopus_search_results.csv')

    df_result.fillna(value='', inplace=True)

    # Define paths for the input data.
    perso_data_path = './data/inputs/path_and_perso_data.json'
    author_db_path = './data/inputs/auth_db.csv'
    # affil_db_path = './data/inputs/affiliation_db.csv'
    affil_db_path = ''

    # Define the stamps you want to add to the paper.
    # If you don't want to add stamp: stamps = []
    stamps = ['LGI-SR', 'CHAIRE-RRSC']
    # stamps = [] # Add your stamps here

    # Load the scopus dataset.
    auto_hal = AutomateHal(perso_data_path=perso_data_path, affil_db_path=affil_db_path,
				author_db_path=author_db_path, stamps=stamps)

    # For debugging: Only upload the first rowRange records.
    # Comment this line if you want to upload all the records.
    rowRange=[0, 10]
    auto_hal.debug_affiliation_search = True
    auto_hal.debug_hal_upload = True
    auto_hal.allow_create_new_affiliation = False

    auto_hal.process_papers(df_result=df_result)