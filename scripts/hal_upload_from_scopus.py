from supports import loadTables_and_createOutpus, loadBibliography, matchDocType, \
    extractAuthors, extractRawAffil, addRow, extractCorrespEmail, \
    retrieveScopusAuths, enrichWithAuthDB, getTitles, close_files, \
    reqWithIds, reqWithTitle
from gen_tei import prepareData, produceTeiTree, exportTei, hal_upload


if __name__ == "__main__":
    # Define paths for the input data.
    scopus_filename = "./data/inputs/scopus_results.csv"
    perso_data_path = './data/inputs/path_and_perso_data.json'
    author_db_path = './data/inputs/auth_db.csv'
    rowRange=[0, 10] # For debugging

    # Load the scopus dataset.
    loadTables_and_createOutpus(perso_data_path, author_db_path)
    publication_list = loadBibliography(scopus_filename)
	
    # Address the record in the scopus dataset one by one.
    for i, doc in enumerate(publication_list):
        # For debugging: Limit to first rowRange records.
        if i < min(rowRange) : continue
        elif i > max(rowRange) : break

        docId = {'eid': doc['EID'] , 'scopusLink': doc['Link'] , 'doi': doc['DOI']}
        print(f"\nite_{i}\n{docId['eid']}")

        # Verify if the publication type is supported.
        docId['doctype'] = matchDocType(doc['Document Type'])
        if not docId['doctype']: # If not supported, add to the log, and pass to the next record.
            addRow(docId ,'not treated', 'doctype not include : '+doc['Document Type'])
            continue

        # Verify if the publication existed in HAL.
        # First check by doi:
        idInHal = reqWithIds(doc['DOI'])
        if idInHal[0] > 0:
            print(f"already in HAL")
            addRow(docId, 'already in hal', '', 'ids match', idInHal[1])
            continue
        else: # Then, check with title
            titleInHal = reqWithTitle(doc['Title'])
            if titleInHal[0] > 0:
                addRow(docId, 'already in hal', '', 'ids match', titleInHal[1])
                continue        

        # Extract & enrich authors data
        # from scopus table extract name, initial, authId
        auths = extractAuthors(doc['Authors'], doc['Author(s) ID'])
        # from scopus table extract corresp auth email
        auths = extractCorrespEmail(auths, doc['Correspondence Address'])
        # from scopus table extract raw affil
        auths = extractRawAffil(auths, doc['Authors with affiliations'])
        # from scopus auhtors api retrieve forename, orcid
        auths = retrieveScopusAuths(auths)
        # from auth_db.csv get the author's affiliation structure_id in HAL.
        auths = enrichWithAuthDB(auths)

        # Produce TEI file.
        titles = getTitles(doc['Title'])

        dataTei = prepareData(doc, auths, docId['doctype'])
        docTei = produceTeiTree(doc, auths, dataTei, titles)
        xml_path = exportTei(docId, docTei, auths)
        hal_upload(xml_path)


    close_files()