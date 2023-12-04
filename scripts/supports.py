from pybliometrics.scopus import AuthorRetrieval, AbstractRetrieval
import csv, json, requests
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


	def __init__(self, perso_data_path, author_db_path, stamps, mode='search_query'):
		'''
		Initialize the automate_hal object with HAL credentials, stamps, and loads valid authors' data.

		Parameters:
		- perso_data_path (path): path to the json file containing the personal data of the authors
		- author_db_path (path): path to the csv file containing the validated author data
		- stamps (list): A list of stamps to be used in the Tei files

		Returns: None
		'''
		self.hal_user_name = ''
		self.hal_pswd = ''
		self.AuthDB = ''
		self.docs_table = ''
		self.writeDoc = ''
		self.mode = mode
		self.ite = -1
		self.stamps = stamps
		self.docid = ''
		self.auths = []
		self.info_complement = {}

		# Check mode:
		if mode != 'search_query' and mode != 'csv':
			raise ValueError('mode must be either "search_query" or "csv".')

		# Load the personal credentials and author database.
		self.loadTables_and_createOutpus(perso_data_path, author_db_path)


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

		Returns: None
		"""
		print(f"added to csv: state = {state}")
		self.writeDoc.writerow([docId['eid'], docId['doi'], docId['doctype'],
							state, treat_info, hal_match, ', '.join(uris), emails ])


	def complementPaperData(self, ab):
		"""
		Completes paper data with information from the abstract retrival api.
		The complemental information about the paper will be updated in self.info_comp attribute.

		Parameters:
		- ab (structure): the results from abstract retrival api.

		Returns: None. 
		"""

		if ab.confdate:
			confdate = "{:04}-{:02d}-{:02d}".format(
				ab.confdate[0][0], ab.confdate[0][1], ab.confdate[0][2])
		else:
			confdate = ''
		self.info_complement = {
			'funding': ab.funding,
			'funding_text': ab.funding_text,
			'language': ab.language,
			'isbn': ab.isbn,
			'confname': ab.confname,
			'confdate': confdate,
			'conflocation': ab.conflocation,
			'startingPage': ab.startingPage,
			'endingPage': ab.endingPage,
			'publisher': ab.publisher
			}


	def enrichWithAuthDB(self):
		"""
		Completes author data with information from the author database provided by the user.
		For each author in the user-defined database, the mail, HAL-id and Affiliation ID in HAL will be used to replace the corresponding fields in 
		self.auths.
		"""
		auths = self.auths
		for item in auths:
			key = item['surname'] + ' ' + item['initial']
			if key in self.AuthDB:
				# Use 'forename' to verify the authors.
				if item['forename'] != self.AuthDB[key]['forename']: # If not matching, do nothing.
					print(f"!!warning: forename mismatch for {key}: {item['forename']} vs {self.AuthDB[key]['forename']}")
				else: # If mathing, get the affil_id and idHAL from database.
					fields = ['affil_id', 'idHAL', 'mail']
					# If nothing from Scopus but present in the local database, then add values
					for f in fields:
						# If nothing is present, enrich with author database
						if not item[f]:
							item[f] = self.AuthDB[key][f]
		self.auths = auths

	def extractAuthors(self):
		"""
		Extracts author information for the authors in a give paper, and then update the information in self.auths.

		Parameters:
		- doc: A dictionary containing the info of a paper.

		Returns: 
		- ab: An object containging the paper details from the Abstract Retrival API.
		"""      

		# Get details for each paper using AbstractRetrieval API.
		ab = AbstractRetrieval(self.docid['eid'], view='FULL')
		authors = ab.authorgroup

		# Initialize an empty list to store author information
		auths = []        
		# Iterate through each author in the list
		for auth_idx in range(len(authors)):
			duplicated = False # Flag to identify duplicated authors.
			# Parse author name info:            
			auth = authors[auth_idx]           
			# Get the different fields.
			surname = auth.surname
			indexed_name = auth.indexed_name
			auth_forename = auth.given_name
			initial = indexed_name[len(surname)+1:]            

			# Get the ORCID.
			orcid = AuthorRetrieval(authors[auth_idx].auid).orcid                 
			if orcid is None:
				orcid = False

			# Check if the author exists in auths but only with a different affiliation.
			for i in range(len(auths)):
				tmp_auth = auths[i]
				if surname == tmp_auth['surname'] and auth_forename == tmp_auth['forename']:
					auths[i]['affil'].append(auth.organization)
					auths[i]['affil_country'].append(auth.city)
					auths[i]['affil_address'].append(auth.addresspart)
					auths[i]['affil_postalcode'].append(auth.postalcode)
					auths[i]['affil_city'].append(auth.city)
					duplicated = True
					break                

			# Append author information to the list
			if not duplicated:
				auths.append({
					'surname': surname,
					'initial': initial,
					'forename': auth_forename,
					'scopusId': authors[auth_idx].auid,
					'orcid': orcid,
					'mail': False,
					'corresp': False,
					'affil': [auth.organization],
					'affil_city': [auth.city],
					'affil_country': [auth.country],
					'affil_address': [auth.addresspart],
					'affil_postalcode': [auth.postalcode],
					'affil_id': '',
					'idHAL': ''
				})

		# Check corresponding author.        
		correspondanes = ab.correspondence
		if correspondanes:
			for correspond in correspondanes:
				for item in auths:
					if item["surname"] == correspond.surname and item["initial"] == correspond.initials:
						item["corresp"] = True
						break  # Stop iterating once the match is found                       
		self.auths = auths

		return ab


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


	def loadTables_and_createOutpus(self, perso_data_path, author_db_path):
		"""
		Loads local data, HAL credentials, Scopus API keys, and valid authors database.
		Initializes CSV output for system log.

		Parameters:
		- perso_data_path (str): Path to the personal data file.
		- author_db_path (str): Path to the valid authors database file.

		Returns: None
		"""
		# Load local data: path and personal data
		with open(perso_data_path) as fh:
			local_data = json.load(fh)

		# Get HAL credentials
		self.hal_user_name = local_data.get("perso_login_hal")
		self.hal_pswd = local_data.get("perso_mdp_hal")

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
		Matches Scopus document types to HAL document types, and update the self.docid['doctype'] dictionary.
	]

		Parameters:
		- doctype (str): Scopus document type.

		Returns: True - Match found, False - No match found.
		"""
		# Dictionary mapping Scopus document types to HAL document types
		doctype_scopus2hal = {
			'Article': 'ART', 'Article in press': 'ART', 'Review': 'ART', 'Business article': 'ART',
			"Data paper": "ART", "Data Paper": "ART",
			'Conference paper': 'COMM', 'Conference Paper': 'COMM',
			'Conference review': 'COMM', 'Conference Review': 'COMM',
			'Book': 'OUV', 'Book chapter': 'COUV', 'Book Chapter': 'COUV'
		}

		# Check if the provided Scopus document type is in the mapping
		# If supported, add the paper type in docid.
		if doctype in doctype_scopus2hal.keys():
			# Set the corresponding HAL document type
			self.docid['doctype'] = doctype_scopus2hal[doctype]
			return True
		else:
			# If not supported: Log the error, and return to process the next paper.
			self.addRow(self.docid, 'not treated', 'doctype not included in HAL: '+doc['subtypeDescription'])
			return False
		

	def process_paper_ite(self, doc):
		"""
		Process each paper:
			- Parse data, get the needed information.
			- Generate TEI-X
			- Upload to HAL
			- Log the process

		Parameters:
		- doc: a dictionary of the paper data.

		Returns: None
		"""

		# Get the ids of each paper.
		if self.mode == 'search_query':
			self.docid = {'eid': doc['eid'], 'doi': doc['doi']}
		elif self.mode =='csv':
			self.docid = {'eid': doc['EID'], 'doi': doc['DOI']}
		else: ValueError('Mode value error!')		
		
		# Verify if the publication type is supported.
		if self.mode == 'search_query':
			doc_type = doc['subtypeDescription']
		elif self.mode =='csv':
			doc_type = doc['Document Type']
		else: ValueError('Mode value error!')
		if not self.matchDocType(doc_type):
			return
		# Verify if the paper is already in HAL.
		elif self.verify_if_existed_in_hal(doc):
			return
		else:        
			# Extract & enrich authors data
			ab = self.extractAuthors()
			# from auth_db.csv get the author's affiliation structure_id in HAL.
			self.enrichWithAuthDB()
			# Complement the paper data based on the Abstract Retrival API.
			self.complementPaperData(ab)
			# Prepare the data for outputing TEI-xml.         
			dataTei = self.prepareData(doc)
			
			# Produce the TEI-xml tree.
			# Prepare input data for the TEI-xml tree.
			if self.mode == 'search_query':
				title = doc['title']
				pub_name = doc["publicationName"]
				issue = doc['issueIdentifier'] 
				volume = doc['volume']
				page_range = doc['pageRange']
				cover_date = doc['coverDate']
				kw_list = doc['authkeywords'].split(" | ")
			elif self.mode =='csv':
				title = doc['Title']
				pub_name = doc["Source title"]
				issue = doc['Issue'] 
				volume = doc['Volume']
				if doc['Page start'] and doc['Page end'] :
					page_range = doc['Page start']+ "-"+doc['Page end']
				else : 
					page_range = ""
				cover_date = doc['Year']
				kw_list = doc['Author Keywords'].split(" ; ")
			else: ValueError('Mode value error!')
			# Produce the xml tree.							
			docTei = self.produceTeiTree(dataTei, title=title, pub_name=pub_name,
								issue=issue, volume=volume, page_range=page_range,
								cover_date=cover_date, keywords_list=kw_list)

			# Export Tei-xml file.
			xml_path = self.exportTei(docTei)

			# Upload to HAL.
			self.hal_upload(xml_path)


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

		# Check if doi is empty:
		if doi == '':
			return idInHal

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
		req = prefix + '&q=' + field + str(value) + suffix
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
		suffix = "&fl=docid,label_s&wt=json"
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


	def verify_if_existed_in_hal(self, doc):
		"""
		Verify if the document is already in HAL.

		Parameters:
		- doc (dict): Document information.
		
		Returns: True if the document is already in HAL; False otherwise.

		"""

		# Verify if the publication existed in HAL.
		# First check by doi:
		idInHal = self.reqWithIds(self.docid['doi'])
		
		if idInHal[0] > 0:
			print(f"already in HAL")
			self.addRow(self.docid, 'already in hal', '', 'ids match', idInHal[1])
			return True
		else: # Then, check with title
			if self.mode == 'search_query':
				titleInHal = self.reqWithTitle(doc['title'])
			elif self.mode == 'csv':
				titleInHal = self.reqWithTitle(doc['Title'])
			else:
				ValueError("mode value error!")
			if titleInHal[0] > 0:
				self.addRow(self.docid, 'already in hal', '', 'ids match', titleInHal[1])
				return True
			
		return False


	def prepareData(self, doc):
		"""
		Prepares data in the format expected by TEI (Text Encoding Initiative).

		Parameters:
		- doc (dict): Document information.

		Returns:
		dict: Data in the TEI format.
		"""
		dataTei = {}
		dataTei['doctype'] = self.docid['doctype']

		# Extract funding data
		dataTei['funders'] = []
		if self.mode == 'search_query':
			if doc['fund_acr']:
				if not doc['fund_no']:
					dataTei['funders'].append(doc['fund_acr'])
				else:
					dataTei['funders'].append('Funder: {}, Grant NO: {}'.format(doc['fund_acr'], doc['fund_no']))
		elif self.mode =='csv':
			if doc['Funding Details']:
				dataTei['funders'].append(doc['Funding Details'])
		else: ValueError('Mode value error!')

		if self.info_complement['funding_text']:
			dataTei['funders'].append(self.info_complement['funding_text'])

		# Get HAL journalId and ISSN
		dataTei['journalId'], dataTei['issn'] = False, False
		if self.mode == 'search_query':
			doc_issn = doc['issn']
		elif self.mode =='csv':
			doc_issn = doc['ISSN']
		else: ValueError('Mode value error!')
		
		if doc_issn:
			# Format ISSN
			zeroMissed = 8 - len(doc_issn)
			issn = ("0" * zeroMissed + doc_issn) if zeroMissed > 0 else doc_issn
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
		scopus_lang = self.info_complement['language'].split(";")[0]
		with open("./data/matchLanguage_scopus2hal.json") as fh:
			matchlang = json.load(fh)
			dataTei["language"] = matchlang.get(scopus_lang, "und")

		# Extract abstract
		if self.mode == 'search_query':
			abstract = doc['description']
		elif self.mode =='csv':
			abstract = doc['Abstract']
		else: ValueError('Mode value error!')

		dataTei['abstract'] = False if abstract.startswith('[No abstr') else abstract[: abstract.find('©') - 1]

		# Extract ISBN
		if self.info_complement['isbn']:
			if ';' in self.info_complement['isbn']:
				# If multiple ISBNs, take the first one only
				dataTei["isbn"] = self.info_complement['isbn'][:self.info_complement['isbn'].index(';')]
			else:
				dataTei["isbn"] = self.info_complement['isbn']
		else:
			dataTei['isbn'] = ''

		return dataTei


	def produceTeiTree(self, dataTei, title, pub_name, 
					issue, volume, page_range, cover_date, keywords_list):
		"""
		Produces a TEI tree based on document information, author data, and TEI data.

		Parameters:
		- dataTei (dict): Data in the TEI format.

		Returns:
		ElementTree: TEI tree.
		"""

		stamps = self.stamps
		# Verify inputs:
		# If stamps is not a list, make it a list
		if not isinstance(stamps, list):
			stamps = [stamps]

		auths = self.auths

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
				
		eTitle = ET.Element('title', {'xml:lang': dataTei["language"] })
		eTitle.text = title
		eAnalytic.insert(0, eTitle)

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

			# Handling the affiliations.
			# if affili_id is provided in authDB: Use them directly.
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
			else:
				# Extract the affiliation name from the search results.
				aut_affils = aut['affil']
				for aut_affil in aut_affils:
					# Remove the ';' at the end of the affiliation. 
					if aut_affil.endswith('; '):
						aut_affil = aut_affil.rstrip('; ')                   
					
					# Search HAL to find the affiliation.
					affi_exist_in_hal = False
					search_result = self.reqHalRef(ref_name='structure', value=aut_affil)
					if search_result[0] > 0: # Find affiliation with the same names in HAL.
						# Check the HAL affiliation contains some other affiliation.
						for i in range(len(search_result[1])):
							affli_info = search_result[1][i]
							if aut_affil.lower() == affli_info['label_s'].lower():								
								# Set affil_id
								affil_id =  search_result[1][i]['docid']
								# Create a new 'affiliation' element under the 'eAuth' element
								eAffiliation_i = ET.SubElement(eAuth, 'affiliation')
								# Set the 'ref' attribute of the 'affiliation' element with a value based on the current id
								eAffiliation_i.set('ref', '#struct-' + affil_id)
								affi_exist_in_hal = True
								break
					
					# If the affiliation does not exist in HAL, add the affiliation manually.
					if not affi_exist_in_hal: 
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
		if not dataTei['doctype'] == 'COMM':
			if not dataTei['journalId'] and dataTei["issn"] :
				eIdIssn = ET.Element('idno', {'type':'issn'})
				eIdIssn.text = dataTei['issn']
				eIdIssn.tail = '\n'+'\t'*8
				eMonogr.insert(0,eIdIssn)

		# if journal not in hal and doctype is ART then paste journal title
		if not dataTei['journalId'] and dataTei['doctype'] == "ART" : 
			eTitleJ = ET.Element('title', {'level':'j'})
			eTitleJ.text =  pub_name
			eTitleJ.tail = '\n'+'\t'*8
			eMonogr.insert(1,eTitleJ)
			index4meeting+=2

		# if it is COUV or OUV paste book title
		if dataTei['doctype'] == "COUV" or dataTei['doctype'] == "OUV" :
			eTitleOuv = ET.Element('title', {'level':'m'})
			eTitleOuv.text = pub_name
			eTitleOuv.tail = '\n'+'\t'*8
			eMonogr.insert(1 , eTitleOuv)
			index4meeting+=2

		## ADD SourceDesc / bibliStruct / monogr / meeting : meeting
		if dataTei['doctype'] == 'COMM' : 
			#conf title
			eMeeting = ET.Element('meeting')
			eMonogr.insert(index4meeting,eMeeting)
			eTitle = ET.SubElement(eMeeting, 'title')
			eTitle.text = self.info_complement['confname']
					
			#meeting date
			eDate = ET.SubElement(eMeeting, 'date', {'type':'start'}) 
			eDate.text = self.info_complement['confdate']
					
			#settlement
			eSettlement = ET.SubElement(eMeeting, 'settlement')
			eSettlement.text = self.info_complement['conflocation'] if self.info_complement['conflocation'] else 'unknown'

			#country
			eSettlement = ET.SubElement(eMeeting, 'country',{'key':'fr'})

		#___ CHANGE  sourceDesc / monogr / imprint :  vol, issue, page, pubyear, publisher
		eImprint = root.find(biblStructPath+'/tei:monogr/tei:imprint', ns)
		for e in list(eImprint):
			if e.get('unit') == 'issue': 
				if issue: e.text = issue if isinstance(issue, str) else str(int(issue))
			if e.get('unit') == 'volume' : 
				if volume: e.text = volume if isinstance(volume, str) else str(int(volume))
			if e.get('unit') == 'pp' : 
				if page_range: e.text = page_range
			if e.tag.endswith('date') : e.text = cover_date
			if e.tag.endswith('publisher') : e.text = self.info_complement['publisher']

		#_____ADD  sourceDesc / biblStruct : DOI & Pubmed
		eBiblStruct = root.find(biblStructPath, ns)
		if self.docid['doi'] : 
			eDoi = ET.SubElement(eBiblStruct, 'idno', {'type':'doi'} )
			eDoi.text = self.docid['doi']

		#___CHANGE  profileDesc / langUsage / language
		eLanguage = root.find(biblFullPath+'/tei:profileDesc/tei:langUsage/tei:language', ns)
		eLanguage.attrib['ident'] = dataTei["language"]

		#___CHANGE  profileDesc / textClass / keywords/ term
		eKeywords = root.find(biblFullPath+'/tei:profileDesc/tei:textClass/tei:keywords', ns)
		eKeywords.clear()
		eKeywords.set('scheme', 'author')
		for i in range(0, len(keywords_list)):
			eTerm_i = ET.SubElement(eKeywords, 'term')
			eTerm_i.set('xml:lang', dataTei['language'])
			eTerm_i.text = keywords_list[i]

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


	def exportTei(self, docTei):
		"""
		Exports TEI data to an XML file and adds a row with relevant information.

		Parameters:
		- docTei (ElementTree): TEI tree.

		Returns:
		str: Path to the exported XML file.
		"""

		docId = self.docid

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

		emails = [elem["mail"] for elem in self.auths if elem["mail"]]

		self.addRow(docId, "TEI generated", '', '', '', ", ".join(emails))

		return xml_path


	def hal_upload(self, filepath):
		"""
		Uploads TEI XML file to HAL using SWORD protocol.

		Parameters:
		- filepath (str): Path to the TEI XML file.

		Returns:
		None
		"""

		docId = self.docid

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
