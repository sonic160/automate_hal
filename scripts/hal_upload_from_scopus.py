from supports import automate_hal


if __name__ == "__main__":
    # Define paths for the input data.
    scopus_filename = "./data/inputs/scopus_results.csv"
    perso_data_path = './data/inputs/path_and_perso_data.json'
    author_db_path = './data/inputs/auth_db.csv'
    
    # Define the stamps you want to add to the paper.
    # If you don't want to add stamp: stamps = []
    stamps = ['LGI-SR', 'CHAIRE-RRSC']

    # For debugging: Only upload the first rowRange records.
    # Comment this line if you want to upload all the records.
    rowRange=[0, 10] 
    
    # Load the scopus dataset.
    auto_hal = automate_hal()    
    auto_hal.loadTables_and_createOutpus(perso_data_path, author_db_path)
    publication_list = auto_hal.loadBibliography(scopus_filename)
	
    # Address the record in the scopus dataset one by one.
    for i, doc in enumerate(publication_list):
        if 'rowRange' in locals():
            # For debugging: Limit to first rowRange records.
            if i < min(rowRange) : continue
            elif i > max(rowRange) : break

        # Get the ids of each paper.
        docId = {'eid': doc['EID'] , 'scopusLink': doc['Link'] , 'doi': doc['DOI']}
        print(f"\nite_{i}\n{docId['eid']}")

        # Verify if the publication type is supported.
        docId['doctype'] = auto_hal.matchDocType(doc['Document Type'])
        if not docId['doctype']: # If not supported, add to the log, and pass to the next record.
            auto_hal.addRow(docId ,'not treated', 'doctype not include : '+doc['Document Type'])
            continue

        # Verify if the publication existed in HAL.
        # First check by doi:
        idInHal = auto_hal.reqWithIds(doc['DOI'])
        if idInHal[0] > 0:
            print(f"already in HAL")
            auto_hal.addRow(docId, 'already in hal', '', 'ids match', idInHal[1])
            continue
        else: # Then, check with title
            titleInHal = auto_hal.reqWithTitle(doc['Title'])
            if titleInHal[0] > 0:
                auto_hal.addRow(docId, 'already in hal', '', 'ids match', titleInHal[1])
                continue        

        # Extract & enrich authors data
        # from scopus table extract name, initial, authId
        auths = auto_hal.extractAuthors(doc['Authors'], doc['Author(s) ID'], doc['Author full names'])
        # from scopus table extract corresp auth email
        auths = auto_hal.extractCorrespEmail(auths, doc['Correspondence Address'])
        # from scopus table extract raw affil
        auths = auto_hal.extractRawAffil(auths, doc['Authors with affiliations'])
        # from scopus auhtors api retrieve forename, orcid
        auths = auto_hal.retrieveScopusAuths(auths)
        # from auth_db.csv get the author's affiliation structure_id in HAL.
        auths = auto_hal.enrichWithAuthDB(auths)

        # Produce TEI file.
        titles = auto_hal.getTitles(doc['Title'])
        dataTei = auto_hal.prepareData(doc, auths, docId['doctype'])
        docTei = auto_hal.produceTeiTree(doc, auths, dataTei, titles, stamps)
        xml_path = auto_hal.exportTei(docId, docTei, auths)
        auto_hal.hal_upload(docId, xml_path)

    # Close all the files. End the program.
    auto_hal.close_files()