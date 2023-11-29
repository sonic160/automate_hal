import json, csv, requests
import xml.etree.ElementTree as ET


class automate_hal:
	"""
    A class for automating the generation and upload of TEI XML files to the HAL repository.

    Attributes:
    - hal_user_name (str): HAL username for authentication.
    - hal_pswd (str): HAL password for authentication.
    - apikey (str): API key for accessing the Scopus API.
    - insttoken (str): Scopus institution token for API access.
    - AuthDB (dict): A dictionary storing valid authors' information loaded from a local file.
    - docs_table (file): A CSV file for logging system activities.
    - writeDoc (csv.writer): CSV writer for adding rows to the system log.

    Methods:
    - __init__: Initializes the automate_hal object with HAL credentials, Scopus API keys, and loads valid authors' data.
    - extractCorrespEmail: Extracts corresponding author emails from a list of authors and corresponding addresses.
    - extractRawAffil: Extracts raw affiliations from a Scopus table and associates them with authors.
    - loadTables_and_createOutpus: Loads local data and initializes system log files and credentials.
    - matchDocType: Matches Scopus document types to HAL document types.
    - addRow: Adds a row to the system log CSV file with information about a document's processing.
    - reqWithIds: Searches HAL to check if a DOI or PubMed ID is already present in the repository.
    - reqWithTitle: Searches HAL for a document with a given title.
    - reqHal: Sends a request to the HAL API and retrieves the number of items found and document details.
    - retrieveScopusAuths: Retrieves additional author information (forename and ORCID) from the Scopus API.
    - reqScopus: Sends a request to the Scopus API and returns the JSON response.
    - enrichWithAuthDB: Completes author data with information from a local file containing valid authors.
    - getTitles: Extracts titles from a Scopus table.
    - close_files: Closes open CSV files.

    TEI XML Generation and HAL Upload Methods:
    - prepareData: Structures data as expected by the TEI format, including funding details, journal information, and more.
    - produceTeiTree: Generates a TEI XML tree based on the provided document data, authors, and titles.
    - exportTei: Exports TEI data to an XML file, adds a row to the system log, and returns the XML file path.
    - hal_upload: Uploads a TEI XML file to the HAL repository using the SWORD protocol.
    """


	def __init__(self):
		'''
		Initialize the automate_hal object with HAL credentials, Scopus API keys, and loads valid authors' data.
		'''
		self.apikey = ''
		self.insttoken = ''
		self.hal_user_name = ''
		self.hal_pswd = ''
		self.AuthDB = ''
		self.docs_table = ''
		self.writeDoc = ''
		

	def loadBibliography(self, path):
		"""
		Load bibliography data from a CSV file.

		Parameters:
		- path (str): The path to the CSV file containing bibliography data.

		Returns:
		- csv.DictReader: A DictReader object for reading data from the CSV file.
		"""
		# Open the CSV file with proper encoding and return a DictReader
		t = open(path, newline='', encoding='utf-8-sig')
		return csv.DictReader(t)


	def extractAuthors(self, authors, authId):
		"""
		Extracts author information from a given list of authors and their corresponding IDs.

		Parameters:
		- authors (str): A string containing a list of authors separated by commas.
		- authId (str): A string containing author IDs separated by semicolons.

		Returns:
		- list: A list of dictionaries, each containing author information such as surname, initial,
				Scopus ID, and placeholders for other details like ORCID, email, correspondence,
				affiliation, and affiliation ID.
		"""
		# Split the input strings to get lists of authors and author IDs
		authors_cut = authors.split(',')
		authId_cut = authId[:-1].split(';')

		# Check if the number of authors and author IDs match
		if not len(authors_cut) == len(authId_cut):
			print("Error: The number of authors and author IDs do not match.")
			quit()

		# Initialize an empty list to store author information
		auths = []
		
		# Iterate through each author in the list
		for auth_idx, auth in enumerate(authors_cut):
			# Check for special cases where author names are grouped, and skip them
			if '.' not in auth:
				print(f"\tEscaped author:\t{auth}")
				continue

			# Process the author name to extract surname and initials
			auth = auth.strip()
			elem = auth.split()

			# Identify the surname and initials
			for i in reversed(range(len(elem))):
				if not elem[i].endswith('.'):
					idx = auth.index(elem[i]) + len(elem[i])
					surname = auth[:idx]
					initial = auth[idx:].strip()
					break

			# Check for potential issues with extracted names
			if len(surname) == 0 or len(initial) < 1:
				print('!! Issue with author name:\t', auth)
				quit()

			# Append author information to the list
			auths.append({
				'surname': surname,
				'initial': initial,
				'forename': False,
				'scopusId': authId_cut[auth_idx],
				'orcid': False,
				'mail': False,
				'corresp': False,
				'affil': '',
				'affil_id': '',
				'idHAL': ''
			})

		return auths

	

	def extractCorrespEmail(self, auths, corresp):
		"""
		Extracts corresponding author email addresses from a given list of authors and corresponding addresses.

		Parameters:
		- auths (list): A list of dictionaries containing author information.
		- corresp (str): A string containing corresponding author addresses, where each address may span multiple lines.

		Returns:
		- list: The updated list of dictionaries with added email and correspondence information.
		"""
		# Iterate through each author in the list
		for item in auths:
			# Iterate through each line in the corresponding author addresses
			for addr in corresp.split('\n'):
				# Check if the address starts with the author's surname
				if addr.startswith(item["surname"]):
					# Extract email address from the line
					mail = [elem for elem in addr.split(" ") if "@" in elem]
					if mail:
						# Update author information with email and set correspondence flag
						item['mail'] = mail[0]
						item['corresp'] = True
						break

		return auths


	def extractRawAffil(self, auths, rawAffils):
		"""
		Extracts raw affiliations from a Scopus table based on author information.

		Parameters:
		- auths (list): A list of dictionaries containing author information.
		- rawAffils (str): A string containing raw affiliation information from a Scopus table.

		Returns:
		- list: The updated list of dictionaries with added affiliation information.
		"""
		# Get the total number of authors
		nbAuth = len(auths)
		i = 1
		# Iterate through each author
		while i <= nbAuth:
			# Construct the full name of the current author
			preFullName = auths[i-1]['surname'] + ", " + auths[i-1]['initial']

			if i == nbAuth:
				# If it's the last author, extract affiliation from the current author to the end
				aff = rawAffils[rawAffils.index(preFullName):]
			else:
				# If it's not the last author, construct the full name of the next author
				postFullName = auths[i]['surname'] + ", " + auths[i]['initial']
				# Extract affiliation from the current author to the next author
				aff = rawAffils[rawAffils.index(preFullName):rawAffils.index(postFullName)]

			# Exclude the author's name from the affiliation
			nameLen = len(preFullName + ', ')
			# Update author information with affiliation
			auths[i-1]['affil'] = aff[nameLen:]
			i += 1

		return auths


	def loadTables_and_createOutpus(self, perso_data_path, author_db_path):
		"""
		Loads local data, HAL credentials, Scopus API keys, and valid authors database.
		Initializes CSV output for system log.

		Parameters:
		- perso_data_path (str): Path to the personal data file.
		- author_db_path (str): Path to the valid authors database file.

		Returns:
		None
		"""
		# Load local data: path and personal data
		with open(perso_data_path) as fh:
			local_data = json.load(fh)

		# Get HAL credentials
		self.hal_user_name = local_data.get("perso_login_hal")
		self.hal_pswd = local_data.get("perso_mdp_hal")

		# Scopus API keys
		self.apikey = local_data.get("perso_scopusApikey")
		self.insttoken = local_data.get("perso_scopusInstToken")

		# Load valid authors database
		with open(author_db_path, 'r', encoding="utf-8") as auth_fh:
			reader = csv.DictReader(auth_fh)
			self.AuthDB = {row['key']: row for row in reader}

		# CSV output for system log
		self.docs_table = open('./data/outputs/log.csv', 'w', newline='', encoding="utf8")
		self.writeDoc = csv.writer(self.docs_table, delimiter=',')
		# Write header to the CSV file
		self.writeDoc.writerow(['eid', 'doi', 'doctype', 'state', 'treat_info', 'hal_match', 'halUris', 'email_corr_auth'])


	def matchDocType(self, doctype):
		"""
		Matches Scopus document types to HAL document types.

		Parameters:
		- doctype (str): Scopus document type.

		Returns:
		str or False: Corresponding HAL document type or False if no match.
		"""
		# Dictionary mapping Scopus document types to HAL document types
		doctype_scopus2hal = {
			'Article': 'ART', 'Article in Press': 'ART', 'Review': 'ART', 'Business Article': 'ART',
			"Data Paper": "ART", 'Conference Paper': 'COMM',
			'Conference Review': 'COMM', 'Book': 'OUV', 'Book Chapter': 'COUV'
		}

		# Check if the provided Scopus document type is in the mapping
		if doctype in doctype_scopus2hal.keys():
			# Return the corresponding HAL document type
			return doctype_scopus2hal[doctype]
		else:
			# Return False if no match is found
			return False


	def addRow(self, docId, state, treat_info='', hal_match='', uris='', emails=''):
		"""
		Adds a row to the CSV log file.

		Parameters:
		- docId (dict): Dictionary containing document information (eid, doi, doctype, etc.).
		- state (str): State of the document.
		- treat_info (str): Additional treatment information (default: '').
		- hal_match (str): HAL matching information (default: '').
		- uris (list): List of HAL URIs (default: '').
		- emails (str): Emails related to the document (default: '').

		Returns:
		None
		"""
		print(f"added to csv: state = {state}")
		self.writeDoc.writerow([docId['eid'], docId['doi'], docId['doctype'],
							state, treat_info, hal_match, ', '.join(uris), emails ])


	def reqWithIds(self, doi):
		"""
		Searches in HAL to check if the DOI or PUBMEDID is already present.

		Parameters:
		- doi (str): Document DOI or PUBMEDID.

		Returns:
		list: List containing the number of items found and a list of HAL URIs.
			Example: [2, ['uri1', 'uri2']]
		"""
		idInHal = [0, []]  # Number of items, list of URIs

		# Perform a HAL request to find documents by DOI
		reqId = self.reqHal('doiId_id:', doi)
		idInHal[0] = reqId[0]

		# Append HAL URIs to the result list
		for i in reqId[1]:
			idInHal[1].append(i['uri_s'])

		return idInHal


	def reqWithTitle(self, titles):
		"""
		Searches in HAL to check if a record with the same title exists.

		Parameters:
		- titles (list): List of titles to search for.

		Returns:
		list: List containing the number of items found and a list of HAL URIs.
			Example: [2, ['uri1', 'uri2']]
		"""
		titleInHal = [0, []]

		# Perform a HAL request to find documents by title
		reqTitle = self.reqHal('title_t:\"', titles + '\"')

		# Append HAL URIs to the result list
		for i in reqTitle[1]:
			titleInHal[1].append(i['uri_s'])

		# Test with the second title
		if len(titles[1]) > 3:
			reqTitle_bis = self.reqHal('title_t:\"', titles[1] + '\"')
			reqTitle[0] += reqTitle_bis[0]

			for i in reqTitle_bis[1]:
				titleInHal[1].append(i['uri_s'])

		titleInHal[0] = reqTitle[0]
		return titleInHal


	def reqHal(self, field, value=""):
		"""
		Performs a request to the HAL API based on the specified field and value.

		Parameters:
		- field (str): Field to search in (e.g., 'title_t', 'doiId_id').
		- value (str): Value to search for (default: "").

		Returns:
		list: List containing the number of items found and a list of HAL documents.
			Example: [2, [{'uri_s': 'uri1', 'title_s': 'Title 1'}, {'uri_s': 'uri2', 'title_s': 'Title 2'}]]
		"""
		prefix = 'https://api.archives-ouvertes.fr/search/?'
		suffix = "&fl=uri_s,title_s&wt=json"
		req = prefix + '&q=' + field + value + suffix
		found = False

		# Perform the request until a valid JSON response is obtained
		while not found:
			req = requests.get(req)
			try:
				fromHal = req.json()
				found = True
			except:
				pass

		num = fromHal['response'].get('numFound')
		docs = fromHal['response'].get('docs', [])
		return [num, docs]
	

	def reqHalRef(self, ref_name, value=""):
		"""
		Performs a request to the HAL API to get references to some fields.

		Parameters:
		- ref_name (str): Reference field that you want information (e.g., 'structure', 'author').
		- value (str): Value to search for (default: "").

		Returns:
		list: List containing the number of items found and a list of HAL documents.
			Example: [2, [{'docid': 'uri1'}, {'docid': 'uri2'}]]
		"""

		prefix = 'https://api.archives-ouvertes.fr/ref/'
		suffix = "&fl=docid&wt=json"
		req = prefix + ref_name + '/?q=' + value + suffix
		found = False

		# Perform the request until a valid JSON response is obtained
		while not found:
			req = requests.get(req)
			try:
				fromHal = req.json()
				found = True
			except:
				pass

		num = fromHal['response'].get('numFound')
		docs = fromHal['response'].get('docs', [])

		return [num, docs]


	def retrieveScopusAuths(self, auths):
		"""
		Retrieves additional information (forename and ORCID) from Scopus for each author.

		Parameters:
		- auths (list): List of author dictionaries.

		Returns:
		list: Updated list of author dictionaries with additional information.
		"""
		# If no Scopus API key is provided, return the original author list
		if not self.apikey:
			return auths

		# Iterate through each author in the list
		for item in auths:
			# If both forename and ORCID are already present, skip to the next author
			if item["forename"] and item["orcid"]:
				continue

			try:
				# Make a request to Scopus API to retrieve additional author information
				req = self.reqScopus('author?author_id=' + item['scopusId'] + '&field=surname,given-name,orcid')

				try:
					# Handle response structure variations
					req = req['author-retrieval-response'][0]
				except:
					pass

				# Get forename
				if not item["forename"] and req.get("preferred-name"):
					item["forename"] = req["preferred-name"].get('given-name')

				# Get ORCID
				if not item["orcid"] and req.get("coredata"):
					item['orcid'] = req['coredata'].get("orcid")

			except:
				pass

		return auths


	def reqScopus(self, suffix):
		"""
		Sends a request to the Scopus API and returns the JSON response.

		Parameters:
		- suffix (str): The endpoint suffix for the API request.

		Returns:
		dict: The JSON response from the Scopus API.
		"""
		prefix = "https://api.elsevier.com/content/"
		req = requests.get(
			prefix + suffix,
			headers={'Accept': 'application/json', 'X-ELS-APIKey': self.apikey}
		)
		req = req.json()

		# Check for API service errors
		if req.get("service-error"):
			print(f"\n\n!!problem with Scopus API:\n\n{req}")
			quit()

		return req


	def enrichWithAuthDB(self, auths):
		"""
		Completes author data with information from the local file 'validUvsqAuth'.

		Parameters:
		- auths (list): List of author dictionaries.

		Returns:
		list: Updated list of author dictionaries with additional information.
		"""
		for item in auths:
			key = item['surname'] + ' ' + item['initial']
			if key in self.AuthDB:
				fields = ['forename', 'affil_id', 'idHAL']  # Exclude email from the local database
				# If nothing from Scopus but present in the local database, then add values
				for f in fields:
					# If nothing is present, enrich with UVSQ author database
					if not item[f]:
						item[f] = self.AuthDB[key][f]
		return auths


	def getTitles(self, inScopus):
		"""
		Extracts titles from a Scopus table entry.

		Parameters:
		- inScopus (str): Scopus table entry containing titles.

		Returns:
		list: List containing one or two titles extracted from the Scopus entry.
		"""
		cutTitle = inScopus.split('[')
		if len(cutTitle) > 1:
			cutindex = inScopus.index('[')
			titleOne = inScopus[0: cutindex].rstrip()
			titleTwo = inScopus[cutindex + 1: -1].rstrip()
		else:
			titleOne = inScopus
			titleTwo = ""
		return [titleOne, titleTwo]


	def close_files(self):
		"""
		Closes open files, such as the CSV output file for system logs.
		"""
		self.docs_table.close()


	def prepareData(self, doc, auths, docType):
		"""
		Prepares data in the format expected by TEI (Text Encoding Initiative).

		Parameters:
		- doc (dict): Document information.
		- auths (list): List of author dictionaries.
		- docType (str): Type of the document.

		Returns:
		dict: Data in the TEI format.
		"""
		dataTei = {}
		dataTei['doctype'] = docType

		# Extract funding data
		dataTei['funders'] = []
		if doc['Funding Details']:
			dataTei['funders'].append(doc['Funding Details'])
		temp = [doc['Funding Text ' + str(i)] for i in range(1, 10) if doc.get('Funding Text ' + str(i))]
		dataTei['funders'].extend(temp)

		# Get HAL journalId and ISSN
		dataTei['journalId'], dataTei['issn'] = False, False
		if doc['ISSN']:
			# Format ISSN
			zeroMissed = 8 - len(doc['ISSN'])
			issn = ("0" * zeroMissed + doc['ISSN']) if zeroMissed > 0 else doc['ISSN']
			issn = issn[0:4] + '-' + issn[4:]

			# Query HAL to get journalId from ISSN
			prefix = 'http://api.archives-ouvertes.fr/ref/journal/?'
			suffix = '&fl=docid,valid_s,label_s'
			req = requests.get(prefix + 'q=issn_s:' + issn + suffix)
			req = req.json()
			reqIssn = [req['response']['numFound'], req['response']['docs']]

			# If journals found, get the first journalId
			if reqIssn[0] > 0:
				dataTei['journalId'] = str(reqIssn[1][0]['docid'])

			# If no journal found, store the ISSN
			if reqIssn[0] == 0:
				dataTei['issn'] = issn

		# Find HAL domain
		dataTei['domain'] = 'spi' # Default: Engineering / physics

		# Query HAL with journalId to retrieve domain
		if dataTei['journalId']:
			prefix = 'http://api.archives-ouvertes.fr/search/?rows=0'
			suffix = '&facet=true&facet.field=domainAllCode_s&facet.sort=count&facet.limit=2'
			req = requests.get(prefix + '&q=journalId_i:' + dataTei['journalId'] + suffix)
			try:
				req = req.json()
				if req["response"]["numFound"] > 9:  # Retrieve domain from journal if there are more than 9 occurrences
					dataTei['domain'] = req['facet_counts']['facet_fields']['domainAllCode_s'][0]
			except:
				print('\tHAL API did not work for retrieving domain with journal')
				pass

		if not dataTei['domain']:
			dataTei['domain'] = 'sdv'
			print('\t!! Domain not found: Defaulted to "sdv". Please verify its relevance.')

		# Match language
		scopus_lang = doc['Language of Original Document'].split(";")[0]
		with open("./data/matchLanguage_scopus2hal.json") as fh:
			matchlang = json.load(fh)
			dataTei["language"] = matchlang.get(scopus_lang, "und")

		# Extract abstract
		abstract = doc['Abstract']
		dataTei['abstract'] = False if abstract.startswith('[No abstr') else abstract[: abstract.find('©') - 1]

		# Extract ISBN
		if ';' in doc['ISBN']:
			# If multiple ISBNs, take the first one only
			dataTei["isbn"] = doc['ISBN'][:doc['ISBN'].index(';')]
		else:
			dataTei["isbn"] = doc['ISBN']

		return dataTei


	def produceTeiTree(self, doc, auths, dataTei, titles, stamps):
		"""
		Produces a TEI tree based on document information, author data, and TEI data.

		Parameters:
		- doc (dict): Document information.
		- auths (list): List of author dictionaries.
		- dataTei (dict): Data in the TEI format.
		- titles (list): List of document titles.
		- stamps (list): List of document stamps.

		Returns:
		ElementTree: TEI tree.
		"""

		# Verify inputs:
		# If stamps is not a list, make it a list
		if not isinstance(stamps, list):
			stamps = [stamps]

		tree = ET.parse('./data/tei_modele.xml')
		root = tree.getroot()
		ET.register_namespace('',"http://www.tei-c.org/ns/1.0")
		ns = {'tei':'http://www.tei-c.org/ns/1.0'}
		biblFullPath = 'tei:text/tei:body/tei:listBibl/tei:biblFull'

		#___CHANGE titlesStmt : suppr and add funder	
		#clear titlesStmt elements ( boz redundant info)
		eTitleStmt = root.find(biblFullPath+'/tei:titleStmt', ns)
		eTitleStmt.clear()

		# if applicable add funders	
		if len(dataTei['funders']) > 0 : 
			for fund in dataTei['funders']: 
				eFunder = ET.SubElement(eTitleStmt, 'funder')
				eFunder.text = fund.replace('\n', ' ').replace('\r', ' ')

		#___CHANGE editionStmt : suppr
		eBiblFull = root.find(biblFullPath, ns)
		eEdition = root.find(biblFullPath+'/tei:editionStmt', ns)
		eBiblFull.remove(eEdition)

		#___CHANGE seriesStmt
		eSeriesStmt = root.find(biblFullPath+'/tei:seriesStmt', ns)
		eSeriesStmt.clear()
		eSeriesIdno_dict = {}
		for i in range(0, len(stamps)):
			eSeriesIdno_i = ET.SubElement(eSeriesStmt, 'idno')
			eSeriesIdno_i.set('type','stamp')
			eSeriesIdno_i.set('n', stamps[i])
			eSeriesIdno_dict[stamps[i]] = eSeriesIdno_i

		#___CHANGE  sourceDesc / title
		eAnalytic = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic', ns)
		eTitle = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic/tei:title', ns)
		eAnalytic.remove(eTitle) 
				
		# Si pas de 2e titre, le titre est celui du document
		if not titles[1] : 
			eTitle = ET.Element('title', {'xml:lang': dataTei["language"] })
			eTitle.text = titles[0]
			eAnalytic.insert(0,eTitle )

		# Si un 2e titre est présent, le 1er titre est en en le 2nd dans la lang du doc
		if titles[1] : 
			eTitle = ET.Element('title', {'xml:lang':'en'})
			eTitle.text = titles[0]
			eAnalytic.insert(0,eTitle)
			eTitle2 = ET.Element('title', {'xml:lang': dataTei["language"] } )
			eTitle2.text = titles[1]
			eAnalytic.insert(1,eTitle2)

		#___CHANGE  sourceDesc / biblStruct / analytics / authors
		biblStructPath = biblFullPath+'/tei:sourceDesc/tei:biblStruct'
		author = root.find(biblStructPath+'/tei:analytic/tei:author', ns)
		eAnalytic.remove(author)

		# Locate the back section of the xml file.
		eListOrg = root.find('tei:text/tei:back/tei:listOrg', ns)
		eOrg = root.find('tei:text/tei:back/tei:listOrg/tei:org', ns)
		eListOrg.remove(eOrg)

		# Reset new affiliation index and list.
		new_affiliation_idx = 0
		new_affliation = []

		# For each author, write author information to the xml tree.
		for aut in auths : 
			role  = 'aut' if not aut['corresp'] else 'crp' #correspond ou non
			eAuth = ET.SubElement(eAnalytic, 'author', {'role':role}) 
			ePers = ET.SubElement(eAuth, 'persName')

			eForename = ET.SubElement(ePers, 'forename', {'type':"first"})
			if not aut['forename'] : eForename.text = aut['initial']
			else : eForename.text = aut['forename']

			eSurname = ET.SubElement(ePers, 'surname')
			eSurname.text = aut['surname']	

			#if applicable  add email 
			if aut['mail'] :
				eMail = ET.SubElement(eAuth, 'email')
				eMail.text = aut['mail'] 

			#if applicable add orcid
			if aut['orcid'] : 
				orcid = ET.SubElement(eAuth,'idno', {'type':'https://orcid.org/'})
				orcid.text = aut['orcid']
			
			#if applicable add idHAL
			if aut['idHAL'] : 
				idHAL = ET.SubElement(eAuth,'idno', {'type':'idhal'})
				idHAL.text = aut['idHAL']

			# Get the affilication.
			aut_affil = aut['affil']
			# Remove the ';' at the end of the affiliation. 
			if aut_affil.endswith('; '):
				aut_affil = aut_affil.rstrip('; ')
			
			# If aut['affil_id'] is not provided by the database, 
			# search HAL to see if the affiliation is already in the HAL.			
			if not aut['affil_id']:
				search_result = self.reqHalRef(ref_name='structure', value=aut_affil)
				if search_result[0] > 0: # Existed in HAL.
					# Set affil_id
					aut['affil_id'] = search_result[1][0]['docid']

			# if applicable add structId
			if aut['affil_id']:
				affil_ids = aut['affil_id'].split(', ') 			
				# Dictionary to store eAffiliation elements
				eAffiliation_dict = {}
				# Create an 'affiliation' element for each id
				for affil_id in affil_ids:
					# Create a new 'affiliation' element under the 'eAuth' element
					eAffiliation_i = ET.SubElement(eAuth, 'affiliation')
					# Set the 'ref' attribute of the 'affiliation' element with a value based on the current id
					eAffiliation_i.set('ref', '#struct-' + affil_id)
					# Store the 'eAffiliation_i' element in the dictionary with the current id as the key
					eAffiliation_dict[affil_id] = eAffiliation_i
			else: # If not, add the affiliation manually.
				# If it is the first new affiliation, create directly.
				if new_affiliation_idx == 0:
					new_affiliation_idx += 1 # Update the index.
					# Create the new organization.
					eBackOrg_i = ET.SubElement(eListOrg, 'org')
					eBackOrg_i.set('type', 'institution')
					eBackOrg_i.set('xml:id', 'localStruct-' + str(new_affiliation_idx))
					eBackOrg_i_name = ET.SubElement(eBackOrg_i, 'orgName')
					eBackOrg_i_name.text = aut_affil
					new_affliation.append(aut_affil)
					# Make reference to the created affliation.
					eAffiliation_manual = ET.SubElement(eAuth, 'affiliation')				
					eAffiliation_manual.set('ref', 'localStruct-' + str(new_affiliation_idx))
				else: # If it is not the first new affiliation, search if it has been created by us before.
					try:
						idx = new_affliation.index(aut_affil)
						# If it has been created, make reference to it.
						eAffiliation_manual = ET.SubElement(eAuth, 'affiliation')				
						eAffiliation_manual.set('ref', 'localStruct-' + str(idx+1))	
					except ValueError: # If not created, create a new one.
						# Update the index.
						new_affiliation_idx += 1
						# Create the new organization.
						eBackOrg_i = ET.SubElement(eListOrg, 'org')
						eBackOrg_i.set('type', 'institution')
						eBackOrg_i.set('xml:id', 'localStruct-' + str(new_affiliation_idx))
						eBackOrg_i_name = ET.SubElement(eBackOrg_i, 'orgName')
						eBackOrg_i_name.text = aut_affil
						new_affliation.append(aut_affil)	
						# Make reference to the created affliation.
						eAffiliation_manual = ET.SubElement(eAuth, 'affiliation')				
						eAffiliation_manual.set('ref', 'localStruct-' + str(new_affiliation_idx))

		# In the end, if no new affiliations are added, remove the 'eBack' element.
		if new_affiliation_idx == 0:
			eBack_Parent = root.find('tei:text', ns)
			eBack = root.find('tei:text/tei:back', ns)
			eBack_Parent.remove(eBack)						
					
		## ADD SourceDesc / bibliStruct / monogr : isbn
		eMonogr = root.find(biblStructPath+'/tei:monogr', ns)
		index4meeting = 0

		## ne pas coller l'ISBN si c'est un doctype COMM sinon cela créée une erreur (2021-01)
		if dataTei['isbn']  and not dataTei['doctype'] == 'COMM':  
			eIsbn = ET.Element('idno', {'type':'isbn'})
			eIsbn.text = dataTei["isbn"]
			eMonogr.insert(0, eIsbn)

		## ADD SourceDesc / bibliStruct / monogr : issn
		# if journal is in Hal
		if dataTei['journalId'] :
			eHalJid = ET.Element('idno', {'type':'halJournalId'})
			eHalJid.text = dataTei['journalId']
			eHalJid.tail = '\n'+'\t'*8
			eMonogr.insert(0,eHalJid)
			index4meeting+=1

		# if journal not in hal : paste issn
		if not dataTei['journalId'] and dataTei["issn"] :
			eIdIssn = ET.Element('idno', {'type':'issn'})
			eIdIssn.text = dataTei['issn']
			eIdIssn.tail = '\n'+'\t'*8
			eMonogr.insert(0,eIdIssn)

		# if journal not in hal and doctype is ART then paste journal title
		if not dataTei['journalId'] and dataTei['doctype'] == "ART" : 
			eTitleJ = ET.Element('title', {'level':'j'})
			eTitleJ.text =  doc["Source title"]
			eTitleJ.tail = '\n'+'\t'*8
			eMonogr.insert(1,eTitleJ)
			index4meeting+=2

		# if it is COUV or OUV paste book title
		if dataTei['doctype'] == "COUV" or dataTei['doctype'] == "OUV" :
			eTitleOuv = ET.Element('title', {'level':'m'})
			eTitleOuv.text = doc["Source title"]
			eTitleOuv.tail = '\n'+'\t'*8
			eMonogr.insert(1 , eTitleOuv)
			index4meeting+=2

		## ADD SourceDesc / bibliStruct / monogr / meeting : meeting
		if dataTei['doctype'] == 'COMM' : 
			#conf title
			eMeeting = ET.Element('meeting')
			eMonogr.insert(index4meeting,eMeeting)
			eTitle = ET.SubElement(eMeeting, 'title')
			eTitle.text = doc.get('Conference name', 'unknown')
					
			#meeting date
			eDate = ET.SubElement(eMeeting, 'date', {'type':'start'}) 
			eDate.text = doc.get('Conference date', 'unknown')[-4:] if doc.get('Conference date') else doc.get('Year', 'unknown')
					
			#settlement
			eSettlement = ET.SubElement(eMeeting, 'settlement')
			eSettlement.text = doc.get('Conference location', 'unknown')

			#country
			eSettlement = ET.SubElement(eMeeting, 'country',{'key':'fr'})

		#___ ADD SourceDesc / bibliStruct / monogr : Editor
		if doc['Editors'] : 
			eEditor = ET.Element('editor')
			eEditor.text = doc['Editors']
			eMonogr.insert(index4meeting+1,eEditor)

		#___ CHANGE  sourceDesc / monogr / imprint :  vol, issue, page, pubyear, publisher
		eImprint = root.find(biblStructPath+'/tei:monogr/tei:imprint', ns)
		for e in list(eImprint):
			if e.get('unit') == 'issue' : e.text = doc['Issue']
			if e.get('unit') == 'volume' : e.text = doc['Volume']
			if e.get('unit') == 'pp' : 
				if doc['Page start'] and doc['Page end'] :
					e.text = doc['Page start']+ "-"+doc['Page end']
				else : 
					e.text = ""
			if e.tag.endswith('date') : e.text = doc['Year']
			if e.tag.endswith('publisher') : e.text = doc['Publisher']

		#_____ADD  sourceDesc / biblStruct : DOI & Pubmed
		eBiblStruct = root.find(biblStructPath, ns)
		if doc['DOI'] : 
			eDoi = ET.SubElement(eBiblStruct, 'idno', {'type':'doi'} )
			eDoi.text = doc['DOI']

		if doc['PubMed ID'] : 
			ePubmed = ET.SubElement(eBiblStruct, 'idno', {'type':'pubmed'} )
			ePubmed.text = doc['PubMed ID']


		#___CHANGE  profileDesc / langUsage / language
		eLanguage = root.find(biblFullPath+'/tei:profileDesc/tei:langUsage/tei:language', ns)
		eLanguage.attrib['ident'] = dataTei["language"]

		#___CHANGE  profileDesc / textClass / keywords/ term
		eTerm = root.find(biblFullPath+'/tei:profileDesc/tei:textClass/tei:keywords/tei:term', ns)
		eTerm.text = doc['Author Keywords']

		#___CHANGE  profileDesc / textClass / classCode : hal domaine & hal doctype
		eTextClass = root.find(biblFullPath+'/tei:profileDesc/tei:textClass', ns)
		for e in list(eTextClass):
			if e.tag.endswith('classCode') : 
				if e.attrib['scheme'] == 'halDomain': e.attrib['n'] = dataTei['domain']
				if e.attrib['scheme'] == 'halTypology': e.attrib['n'] = dataTei['doctype']

		#___CHANGE  profileDesc / abstract 
		eAbstract = root.find(biblFullPath+'/tei:profileDesc/tei:abstract', ns)
		eAbstract.text = dataTei['abstract']

		return tree


	def exportTei(self, docId, docTei, auths):
		"""
		Exports TEI data to an XML file and adds a row with relevant information.

		Parameters:
		- docId (dict): Document identifier information.
		- docTei (ElementTree): TEI tree.
		- auths (list): List of author dictionaries.

		Returns:
		str: Path to the exported XML file.
		"""
		tree = docTei
		root = tree.getroot()
		ET.register_namespace('', "http://www.tei-c.org/ns/1.0")
		root.attrib["xmlns:hal"] = "http://hal.archives-ouvertes.fr/"

		xml_path = './data/outputs/TEI/' + docId['eid'] + ".xml"
		ET.indent(tree, space="\t", level=0)
		tree.write(xml_path,
				xml_declaration=True,
				encoding="utf-8",
				short_empty_elements=False)

		emails = [elem["mail"] for elem in auths if elem["mail"]]

		self.addRow(docId, "TEI generated", '', '', '', ", ".join(emails))

		return xml_path


	def hal_upload(self, docId, filepath):
		"""
		Uploads TEI XML file to HAL using SWORD protocol.

		Parameters:
		- filepath (str): Path to the TEI XML file.

		Returns:
		None
		"""
		url = 'https://api.archives-ouvertes.fr/sword/hal'
		head = {
			'Packaging': 'http://purl.org/net/sword-types/AOfr',
			'Content-Type': 'text/xml',
			'X-Allow-Completion': None
		}
		# If pdf: Content-Type: application/zip

		xmlfh = open(filepath, 'r', encoding='utf-8')
		xmlcontent = xmlfh.read()  # The XML must be read, otherwise import time is very long
		xmlcontent = xmlcontent.encode('UTF-8')

		if len(xmlcontent) < 10:
			self.addRow(docId, "HAL upload: Success", '', 'File not loaded', '', '')
			quit()

		response = requests.post(url, headers=head, data=xmlcontent, auth=(self.hal_user_name, self.hal_pswd))
		if response.status_code == 202:
			self.addRow(docId, "HAL upload: Success", '', '', '', '')
			print("HAL upload: Success")
		else:
			self.addRow(docId, "HAL upload: Error", '', response.text, '', '')
			print("HAL upload: Error")
			print(response.text)

		xmlfh.close()
