from pybliometrics.scopus import AuthorRetrieval, AbstractRetrieval
import csv, json, requests, os, re, math
import xml.etree.ElementTree as ET
import numpy as np
from pybliometrics.scopus import ScopusSearch
import pandas as pd
from unidecode  import unidecode 
import pycountry as pycountry
import copy


class automate_hal:
	"""
    A class for automatically 
	- searching documents in Scopus, 
	- generating the corresponding TEI XML files for HAL, 
	- and uploading the document reference to the HAL repository.

    Attributes:
    - `hal_user_name` (str): HAL username.
    - `hal_pswd` (str): HAL password.
    - `AuthDB` (str): Path to a CSV file containing validated author data.
    - `docs_table` (str): Path to a CSV file for logging system activities.
    - `writeDoc` (str): CSV writer for adding rows to the system log.
    - `mode` (str): Mode of operation, either 'search_query' or 'csv'.
    - `ite` (int): Index of the current literature.
    - `stamps` (list): List of stamps to be used in the Tei files.
    - `docid` (dict): Document ID, in the format `{'eid': (str), 'doi': (str), 'doctype': (str)}`.
    - `auths` (list): List to store author information. 
	Each element in the list is a dictionary with the following format: `{'surname': (str),
					'initial': (str),
					'forename': (str),
					'scopusId': (str),
					'orcid': (list),
					'mail': (str),
					'corresp': (str),
					'affil': (list),
					'affil_city': (list),
					'affil_country': (list),
					'affil_address': (list),
					'affil_postalcode': (list),
					'affil_id': (list),
					'idHAL': (list)}`.
    - `info_complement` (dict): Dictionary to store additional information. Format: `{'funding': (dict),
			'funding_text': (str),
			'language': (str),
			'isbn': (str),
			'confname': (str),
			'confdate': (str),
			'conflocation': (str),
			'startingPage': (str),
			'endingPage': (str),
			'publisher': (str)
		}`


    Methods:
    - `__init__(self, perso_data_path, author_db_path, stamps, mode='search_query')`: Initializes the `automate_hal` object with HAL credentials, stamps, and loads valid authors' data.
    - `loadTables_and_createOutpus(self, perso_data_path, author_db_path)`: Loads personal credentials and author database.
    - `addRow(self, docId, state, treat_info='', hal_match='', uris='', emails='')`: Adds a row to the CSV log file.
    - `complementPaperData(self, ab)`: Completes paper data with information from the abstract retrieval API.
    - `enrichWithAuthDB(self)`: Completes author data with information from the author database provided by the user.
    - `extractAuthors(self)`: Extracts author information for the authors in a given paper and updates the information in `self.auths`.
    - `loadBibliography(self, path)`: Loads bibliography data from a CSV file.
    - `matchDocType(self, doctype)`: Matches Scopus document types to HAL document types and updates `self.docid['doctype']`.
    - `process_paper_ite(self, doc)`: Main function to process each paper, parse data, generate TEI-X, upload to HAL, and log the process.
    - `reqWithIds(self, doi)`: Searches in HAL to check if the DOI is already present.
    - `reqWithTitle(self, titles)`: Searches in HAL to check if a record with the same title exists.
    - `reqHal(self, field, value="")`: Performs a request to the HAL API based on the specified field and value.
    - `reqHalRef(self, ref_name, value="")`: Performs a request to the HAL API to get references to some fields.
    - `verify_if_existed_in_hal(self, doc)`: Verifies if the document is already in HAL.
    - `prepareData(self, doc)`: Prepares data in the format expected by TEI (Text Encoding Initiative).
    - `produceTeiTree(self, dataTei, title, pub_name, issue, volume, page_range, cover_date, keywords_list)`: Produces a TEI tree based on document information, author data, and TEI data.
	"""

	def __init__(self, perso_data_path, author_db_path, stamps, mode='search_query'):
		'''
		Initialize the automate_hal object with HAL credentials, stamps, and loads valid authors' data.

		Parameters:
		- perso_data_path (path): path to the json file containing the personal data of the authors
		- author_db_path (path): path to the csv file containing the validated author data
		- stamps (list): A list of stamps to be used in the Tei files. Example: ['stamp_1', 'stamp_2']

		Returns: None
		'''
		self.hal_user_name = '' # HAL username
		self.hal_pswd = '' # HAL password
		self.AuthDB = '' # Path to a csv files that define user data to refine the search results.
		self.docs_table = '' # Path to a CSV file for logging system activities.
		self.writeDoc = '' # CSV writer for adding rows to the system log.
		self.mode = mode # Mode of operation: search_query or csv
		self.ite = -1 # Index of the current iterature.
		self.stamps = stamps # List of stamps to be used in the Tei files.
		self.docid = '' # Document ID: A dictionary in format of {'eid': '', 'doi': '', 'doctype': ''}
		self.auths = [] # A dictionary to store author information. 
		self.info_complement = {
			'funding': None,
			'funding_text': '',
			'language': '',
			'isbn': '',
			'confname': '',
			'confdate': '',
			'conflocation': '',
			'startingPage': '',
			'endingPage': '',
			'publisher': ''
		} # A dictionary to store additional information about the document.
		self.debug_mode = False # Whether to run in debug mode. If True, not verifying if existed in HAL.
		self.upload_to_hal = True # Whether to upload the document reference to the HAL repository.

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

		# Get conference data and format it according to HAL requirement.
		if ab.confdate:
			confdate = "{:04}-{:02d}-{:02d}".format(
				ab.confdate[0][0], ab.confdate[0][1], ab.confdate[0][2])
		else:
			confdate = ''
		# Output the results:
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

		Parameters: None.
		Returns: None.
		"""

		# Get the author list
		auths = self.auths
		# Iterate over the authors, and enrich the author data.
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

		Parameters: None.

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
			'Book': 'OUV', 'Book chapter': 'COUV', 'Book Chapter': 'COUV', 'Editorial': 'ART', 'Short Survey': 'ART',
			'Journal': 'ART', 'Conference Proceeding': 'COMM', 'Book Series': 'OUV'
		}

		# Check if the provided Scopus document type is in the mapping
		# If supported, add the paper type in docid.
		if doctype in doctype_scopus2hal.keys():
			# Set the corresponding HAL document type
			self.docid['doctype'] = doctype_scopus2hal[doctype]
			return True
		else:
			# If not supported: Log the error, and return to process the next paper.
			self.docid['doctype'] = 'Unknown'
			self.addRow(self.docid, 'not treated', 'doctype not included in HAL: '+doctype)
			return False
		

	def process_paper_ite(self, doc):
		"""
		Main function: Process each paper
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
			doc_type = doc['aggregationType']
		elif self.mode =='csv':
			doc_type = doc['Document Type']
		else: ValueError('Mode value error!')
		if not self.matchDocType(doc_type):
			return
		# Verify if the paper is already in HAL.
		elif not self.debug_mode and self.verify_if_existed_in_hal(doc):
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
			if self.upload_to_hal:
				self.hal_upload(xml_path)


	def reqWithIds(self, doi):
		"""
		Searches in HAL to check if the DOI is already present.

		Parameters:
		- doi (str): Document DOI.

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

		titles = re.sub(r'&amp;', ' ', titles)
		titles = re.sub(r'[^a-zA-Z0-9 ]', '', titles)		

		# Perform a HAL request to find documents by title
		reqTitle = self.reqHal('title_t:(', titles + ')')

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
	

	def reqHalStamp(self, stamp, start_year, end_year=2099):
		"""
		Performs a request to the HAL API to get the results from a group by its stamp.

		Parameters:
		- stamp (str): The stamp of a group.

		Returns:
		list: List containing the number of items found and a list of HAL documents.
		"""

		req = 'https://api.archives-ouvertes.fr/search/index/?q=collCode_s:{}'.format(stamp) + \
			'+producedDateY_i:[2018+TO+2025]&sort=producedDateY_i%20desc&submit=&docType_s=ART+OR+COMM+OR+POSTER+OR+OUV+OR+COUV+OR+PROCEEDINGS+OR+BLOG+OR+ISSUE+OR+NOTICE+OR+TRAD+OR+PATENT+OR+OTHER+OR+UNDEFINED+OR+REPORT+OR+THESE+OR+HDR+OR+LECTURE+OR+VIDEO+OR+SON+OR+IMG+OR+MAP+OR+SOFTWARE&submitType_s=notice+OR+file+OR+annex&rows=3000'

		prefix = 'https://api.archives-ouvertes.fr/search/?'
		prefix_produceDate = '+producedDateY_i:[{}+TO+{}]'.format(start_year, end_year)
		prefix_sort = '&sort=producedDateY_i%20desc'
		prefix_type = '&docType_s=ART+OR+COMM+OR+POSTER+OR+OUV+OR+COUV+OR+PROCEEDINGS+OR+BLOG+OR+ISSUE+OR+NOTICE+OR+TRAD+OR+PATENT+OR+OTHER+OR+UNDEFINED+OR+REPORT+OR+THESE+OR+HDR+OR+LECTURE+OR+VIDEO+OR+SON+OR+IMG+OR+MAP+OR+SOFTWARE&submitType_s=notice+OR+file+OR+annex&rows=3000'
		suffix = "&fl=docid, uri_s,title_s&wt=json"
		req = prefix + 'q=collCode_s:' + str(stamp) + prefix_produceDate + prefix_produceDate + prefix_sort + prefix_type + suffix
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


	def reqHalRef(self, ref_name, value="", return_field="&fl=docid,label_s&wt=json"):
		"""
		Performs a request to the HAL API to get references to some fields.

		Parameters:
		- ref_name (str): Reference field that you want information (e.g., 'structure', 'author').
		- value (str): Value to search for (default: "").
		- return_field (str): Field to return (default: "&fl=docid,label_s&wt=json").

		Returns:
		list: List containing the number of items found and a list of HAL documents.
			Example: [2, [{'docid': 'docid1', 'label_s': 'Label 1'}, {'docid': 'docid2', 'label_s': 'Label 2}]]
		"""

		prefix = 'https://api.archives-ouvertes.fr/ref/'
		suffix = return_field
		# Encode the value to deal with special symbols like &
		value = re.sub(r'&amp;', '& ', value)
		value = re.sub(r'&', ' ', value)
		# value = quote(value, safe='')
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

		if self.info_complement['funding_text'] and isinstance(self.info_complement['funding_text'], str):
			dataTei['funders'].append(self.info_complement['funding_text'])

		# Get HAL journalId and ISSN
		dataTei['journalId'], dataTei['issn'] = False, False
		if self.mode == 'search_query':
			doc_issn = doc['issn']
		elif self.mode =='csv':
			doc_issn = doc['ISSN']
		else: ValueError('Mode value error!')
		
		if doc_issn and isinstance(doc_issn, str):
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
			dataTei['isbn'] = ''

			if isinstance(self.info_complement['isbn'], list) or isinstance(self.info_complement['isbn'], tuple):
				dataTei["isbn"] = self.info_complement['isbn'][0]
				
			if isinstance(self.info_complement['isbn'], str):
				dataTei["isbn"] = self.info_complement['isbn']

			if ';' in dataTei["isbn"]:
				# If multiple ISBNs, take the first one only
				dataTei["isbn"] = dataTei["isbn"][:dataTei["isbn"].index(';')]		
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
		biblStructPath = biblFullPath+'/tei:sourceDesc/tei:biblStruct'


		# Define private sub-function to parse differet part of the xml tree.
		def parse_funder():
			''' Parse funder element. 
			'''
			#___CHANGE titlesStmt : suppr and add funder	
			#clear titlesStmt elements ( boz redundant info)
			eTitleStmt = root.find(biblFullPath+'/tei:titleStmt', ns)
			eTitleStmt.clear()

			# if applicable add funders	
			if len(dataTei['funders']) > 0 : 
				for fund in dataTei['funders']: 
					eFunder = ET.SubElement(eTitleStmt, 'funder')
					eFunder.text = fund.replace('\n', ' ').replace('\r', ' ')


		def parse_stamp():
			''' Parse stamp element.
			'''
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


		def parse_title():
			''' Parse title element.
			'''
			#___CHANGE  sourceDesc / title
			eAnalytic = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic', ns)
			eTitle = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic/tei:title', ns)
			eAnalytic.remove(eTitle) 
					
			eTitle = ET.Element('title', {'xml:lang': dataTei["language"] })
			eTitle.text = title
			eAnalytic.insert(0, eTitle)


		# Define a function to pick the affiliation in HAL, based on the search result.
			
		def pick_affiliation_in_hal(search_result, affil_country='', affil_city='', affil_name='', aut='', parent_affil_id='', invalide_affil=False):
			'''
			This function checks the results from HAL and pick the best-matched affiliation. It will create a section based on the accociated affiliation id in the xml tree.
			
			Parameters:
				- search_result (list): The result from HAL search.
				- affil_city (str): The city of the affiliation to be added.
				- parent_affil_id (str): The id of the parent affiliation.  

			Return:
				- affi_exist_in_hal (bool): If the affiliation exists in HAL, return True. Otherwise, return False. 
				- best_match_affil_id (str): The dict of the best match affiliation.
			'''

			# Subfunction defintions.

			# If too many candidates with parents, we drop this item as we are not sure to achieve confident extraction.
			# We count the number of parent institutions. If too many, this indicates that it is better to look at parent affiliations.
			def check_affil_city(df_affli_found, affil_city):
				'''
				Given an input DataFrame of possible affiliations, find the best match for the specified pattern. 

				Parameters:
					- df_affli_found (pd.DataFrame): The DataFrame of possible affiliations.
					- affil_city (str): The city of the affiliation to be added. 

				Return:
					- affi_exist_in_hal (bool): If the affiliation exists in HAL, return True. Otherwise, return False.
					- affil_dict (dict): A dictionary of the affiliation of the best match found.
				'''

				# Custom function to clean and format the address
				def clean_and_format_address(address):
					output = ''
					if pd.notna(address):
						address = unidecode(address)								
						cleaned_address = re.sub(r'[^a-zA-Z0-9 ]', ' ', address)  # Keep only letters and numbers
						output = cleaned_address.lower()
				
					return output

				if not df_affli_found.empty:
					affil_city = clean_and_format_address(affil_city)
					if 'address_s' in df_affli_found.columns:
						# Conditino 2: Address contains the city
						df_affli_found['cleaned address_s'] = df_affli_found['address_s'].apply(clean_and_format_address)
						condition_2 = df_affli_found['cleaned address_s'].str.contains(affil_city, regex=False)				
					
						# Condition 1: XXX [Location] in affilication name
						pattern = "[{}]".format(affil_city)				
						condition_1 = df_affli_found['label_s'].str.lower().str.contains(pattern, regex=False)

						# Condition 3: NaN in the address
						condition_3 = pd.isna(df_affli_found['address_s'])	

						df_affli_found = df_affli_found[condition_1 | condition_2 | condition_3]
					
				return df_affli_found
			

			# Define a function to sort df_affli_found based on the number of words in the affliation name.
			def sort_by_name_length(df):																			
				# Function to calculate the number of words in a string
				def count_words(text):
					return len(text.split())										
				# Add a new column 'word_count' with the number of words in 'label_s'
				df['word_count'] = df['label_s'].apply(count_words)
				# Sort the DataFrame based on the 'word_count' column
				df_sorted = df.sort_values(by='word_count').reset_index(drop=True)
				# Drop the 'word_count' column if you don't need it in the final result
				df_sorted = df_sorted.drop(columns='word_count')

				return df_sorted
			

			def check_university_group(df_affli_found):
				'''
				Check if an affiliation in df_affil_found is the parent of others in df_affil_found.
				If so, we could remove the children from the candidate list.

				Parameters:
					- df_affli_found: Pandas DataFrame, the dataframe of the affiliation found in the database.
				Return:
					- df_affli_found: After removal.
				'''

				# Function to check if a row is a child of other rows.
				def not_child(row):
					other_rows = df_affli_found[df_affli_found.index != row.name]  # Exclude the current row
					if 'parentDocid_i' in row.index:
						parent_ids = row['parentDocid_i']
						if isinstance(pd.isna(parent_ids), bool):
							if pd.isna(parent_ids):
								return True								
						else:
							if all(pd.isna(parent_ids)):
								return True
					
						for _, other_row in other_rows.iterrows():
							if other_row['docid'] in parent_ids:
								return False
							
					return True


				if not df_affli_found.empty:
					# Apply the function to identify the child affiliations.
					flag = []
					for i in range(len(df_affli_found)):
						flag.append(not_child(df_affli_found.iloc[i]))

					df_affli_found = df_affli_found[flag]

				return df_affli_found
			

			def check_published_before(df_affli_found, aut):
				affi_exist_in_hal = False
				best_affil_dict = {}

				if not df_affli_found.empty:
					# Check in the remaining candidates, if the authors appeared in HAL with the candidate affiliation before.
					flag = []
					for i in range(len(df_affli_found)):
						field = 'structId_i:{}&fq=auth_t:"{} {}"'.format(df_affli_found.iloc[i]['docid'], aut['forename'], aut['surname'])
						num, _ = self.reqHal(field=field)
						flag.append(num>0)
					if any(flag):
						df_affli_found = df_affli_found[flag]
						
						affi_exist_in_hal = True
						best_affil_dict = df_affli_found.iloc[0].to_dict()

				return affi_exist_in_hal, best_affil_dict
			

			def return_callback_func(affi_exist_in_hal=False, best_affil_dict={}, affil_name=''):					
				# # Final check: The affiliation name should not be too different from the original name.
				# if affi_exist_in_hal:
				# 	result_name = unidecode(best_affil_dict['label_s']).lower()
				# 	affil_name = unidecode(affil_name).lower()
				# 	result_words = result_name.split()
				# 	affil_words = affil_name.split()
				# 	difference = abs(len(result_words) - len(affil_words))

				# 	if difference > 3 and not '[{}]'.format(affil_name) in result_name:
				# 		affi_exist_in_hal=False
				# 		best_affil_dict={}
					
										
				# Return the callback function
				return affi_exist_in_hal, best_affil_dict
			

			# End of subfunction definition. Start execution.

			if search_result[0] > 0:
				# Create a dataframe to get all the found affliations.
				for i in range(len(search_result[1])):
					if i == 0:
						df_affli_found = pd.DataFrame([search_result[1][i]])
					else:
						df_affli_found = pd.concat([df_affli_found, pd.DataFrame([search_result[1][i]])], ignore_index=True)

				# If used for invalid affiliations.
				# Only check if it is an exact match.
				if invalide_affil:
					df_exact = df_affli_found[df_affli_found['label_s'].str.lower()==affil_name.lower()]

					if not df_exact.empty:
						return return_callback_func(affi_exist_in_hal=True, best_affil_dict=df_exact.iloc[0].to_dict())
					else:
						return return_callback_func()			
					

				# If the current parent affil list is not empty:
				if len(parent_affil_id) > 0:
					# If we have already some parent affils, we need to first screen the candidate results to remove 
					# those with different parent affil ids.
					if 'parentDocid_i' in df_affli_found.columns:
						# Filter rows based on the condition (including NaN values and handling comma-separated values)
						tmp_df_1 = df_affli_found[pd.isna(df_affli_found['parentDocid_i'])]
						tmp_df_1[tmp_df_1['label_s'].apply(unidecode).str.lower()==unidecode(affil_name).lower()]
						tmp_df_2 = df_affli_found[pd.notna(df_affli_found['parentDocid_i'])]
						tmp_df_2 = tmp_df_2[tmp_df_2['parentDocid_i'].apply(lambda x: any(item in parent_affil_id for item in x))]
						df_affli_found = pd.concat([tmp_df_1, tmp_df_2])
						
						# If after the operation, no affiliation left: Return directly.
						if df_affli_found.empty:
							return return_callback_func()

				# Search logic: We first identify the affiliation name with the pattern Name + [Location].
				# If not found, we use the one with the shortest name.
										
				# Sort by name lengh.
				df_affli_found = sort_by_name_length(df=df_affli_found)

				# Take maximal 40 records.
				if len(df_affli_found) > 30:
					df_affli_found = df_affli_found.iloc[:40, :]
					# return return_callback_func()

				# Check if the input affil name is an acronym.
				# If yes, only consider the items that contain the full name.
				if len(affil_name.split(' ')) == 1:
					flag = df_affli_found['label_s'].str.lower().str.contains('[{}]'.format(affil_name.lower()), regex=False)
					if any(flag):
						df_affli_found = df_affli_found[flag]

				# Remove the child affiliations in the list.
				df_affli_found = check_university_group(df_affli_found)

				# If in the remaining affiliations, the author has published before: Select the first one.
				affi_exist_in_hal, best_affil_dict = check_published_before(df_affli_found, aut)
				if affi_exist_in_hal:				
					return return_callback_func(affi_exist_in_hal, best_affil_dict, affil_name)
				
				# # Keep only the affiliations that starts with the required name:
				# df_without_accent = df_affli_found['label_s'].apply(unidecode).str.lower()
				# df_affli_found = df_affli_found[df_without_accent.str.startswith(
				# 	unidecode(affil_name[0].lower()))]
							
				# The affiliation country needs to match.
				if affil_country:
					try:
						df_affli_found = df_affli_found[df_affli_found['country_s']==affil_country]
					except:
						pass					
				
				# If the affiliation name ends with [Location], pick the one that matches the actual location.
				df_affli_found = check_affil_city(df_affli_found, affil_city)
				if df_affli_found.empty:	
					return return_callback_func()
				
				# If there is exact matched affil name:
				df_exact = df_affli_found[df_affli_found['label_s'].str.lower()==affil_name.lower()]
				# affil name [XXX]
				pattern = re.compile(r'{} \[.*\]'.format(affil_name.lower()))
				df_exact = pd.concat([
					df_exact,
					df_affli_found[[element is not None for element in df_affli_found['label_s'].str.lower().apply(pattern.match)]]
				])
				# affil name [City name]
				if pd.notna(affil_city):
					df_exact = pd.concat([
							df_exact,
							df_affli_found[df_affli_found['label_s'].str.lower()=='{} [{}]'.format(affil_name.lower(), affil_city.lower())],	  
						])
							
				if not df_exact.empty:
					return return_callback_func(True, df_exact.iloc[0].to_dict(), affil_name)
				
				# If less than three affiliation remains, take it. Otherwise, return not found.
				if len(df_affli_found) <= 3:
					affi_exist_in_hal = True
					best_affil_dict = df_affli_found.iloc[0].to_dict()

					return return_callback_func(affi_exist_in_hal, best_affil_dict, affil_name)
				else:
					return return_callback_func()	
			else:
				return return_callback_func()


		def parse_authors():
			''' Parse authors element.
			'''
			eAnalytic = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic', ns)
			#___CHANGE  sourceDesc / biblStruct / analytics / authors			
			author = root.find(biblStructPath+'/tei:analytic/tei:author', ns)
			eAnalytic.remove(author)

			# Locate the back section of the xml file.
			eListOrg = root.find('tei:text/tei:back/tei:listOrg', ns)
			eOrg = root.find('tei:text/tei:back/tei:listOrg/tei:org', ns)
			eListOrg.remove(eOrg)

			## Sub-function definitions for handling affiliations.
					
			# Define a subfuntion to add a new affiliation.
			def add_new_affiliation(new_affiliation_idx, new_affliation, aut_affil):
				'''
				This is a subfunction that create a new affiliation. First it will check if the affiliation already exists as a local structure.
				If yes, it will directly refer to that. If no, it will create a new one.

				Parameters:
				- new_affiliation_idx (int): The index of the new affiliation.
				- new_affliation (list): The list of new affiliations.
				- aut_affil (str): The affiliation of the author.

				Returns:
				- new_affiliation_idx (int): The index of the new affiliation.
				- new_affliation (list): The list of new affiliations.		

				'''

				# Dealing with special characters:
				aut_affil = re.sub(r'&amp;', '& ', aut_affil)

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

				return new_affiliation_idx, new_affliation
			

			# Sub-functions supporting parsing affiliations.
			def add_affiliation_by_affil_id(eAuth, affil_id):
				''' 
				If affiliation_id is provided in authDB: Use them directly to create a section for affiliation in the tei-xml tree.

				Parameters: 
				- eAuth (ET.Element): The element to which the 'affiliation' element will be added. 
				- affil_id (str): The id of the affiliation to be added. 

				Returns: None
				'''

				# Define a subfunction for adding the affiliation element in the xml tree.
				def add_subelement_for_affil_id(eAuth, affil_id):
					eAffiliation_i = ET.SubElement(eAuth, 'affiliation')
					eAffiliation_i.set('ref', '#struct-' + affil_id)

					# For debugging onle: Print also affiliation name.
					# Remove this after debugging!						
					if self.debug_mode and not self.upload_to_hal:
						try:
							search_result = self.reqHalRef(ref_name='structure', 
										value='(docid:{})'.format(affil_id), 
										return_field='&fl=label_s&wt=json')
							eAffiliation_i.set('name', search_result[1][0]['label_s'])
						except:
							pass
					

				# Check if 'affiliation' subelement exists
				existing_affiliations = eAuth.findall('affiliation')

				if existing_affiliations:
					# 'affiliation' subelement exists
					found_matching_affiliation = False

					# Check if any existing 'affiliation' has the same affil_id
					for affiliation in existing_affiliations:
						if 'ref' in affiliation.attrib and affiliation.attrib['ref'] == '#struct-' + affil_id:
							found_matching_affiliation = True
							# print(f"Matching 'affiliation' found with affil_id {affil_id}: {affiliation}")
							break

					if not found_matching_affiliation:
						# No matching 'affiliation' found, create a new one
						add_subelement_for_affil_id(eAuth, affil_id)
						# print(f"New 'affiliation' created with affil_id {affil_id}: {eAffiliation_i}")
				else:
					# 'affiliation' subelement does not exist, create a new one
					add_subelement_for_affil_id(eAuth, affil_id)
					# print(f"New 'affiliation' created with affil_id {affil_id}: {eAffiliation_i}")


			# Define a function to check if the matched affiliation has parent affiliation.
			def add_affil_and_parent_affil(affil_dict, eAuth):
				affil_ids = []
				affil_ids.append(affil_dict['docid'])
				if 'parentValid_s' in affil_dict and 'parentDocid_i' in affil_dict:
					try:
						for idx, parent_id in enumerate(affil_dict['parentDocid_i']):
							if affil_dict['parentValid_s'][idx]=='VALID':
								affil_ids.append(parent_id)
					except:
						pass

				# Create a new 'affiliation' element under the 'eAuth' element
				for affil_id in affil_ids:
					add_affiliation_by_affil_id(eAuth=eAuth, affil_id=affil_id)							
			

			# Subfunction to transform a country name to its abbreviation.
			def generate_abbreviation(country_name):
					country = None
					if country_name:
						try:
							country = pycountry.countries.search_fuzzy(country_name)[0]
							country = country.alpha_2.lower()						
						except LookupError:
							pass
						
					return country
					
			
			# Defuzzy affiliation names.
			def defuzzy_affil_name(aut_affils, index):
				affil_name = aut_affils[index]

				replacements = [
					('electricite de france', 'edf'),
					('mines paristech', 'mines paris - psl'),
					('ecole ', ''),
					('randd', 'r d')
					# Add more replacement pairs as needed
				]

				# Apply the replacements
				output_string = unidecode(affil_name).lower()
				for old_str, new_str in replacements:
					output_string = output_string.replace(old_str, new_str)

				aut_affils[index] = output_string

				return output_string
			

			def enrich_affil_name(aut_affils, index, affil_country):
				'''
				If some criteria are met, generate another item based on the current affiliation name.
				Examples:
				- If the affiliation name contains 'university' and it is a french institute, add 'universite'.
				- If the affiliation name contains an acronym in the format of (acronym), add the acronym.

				Parameters:
				- aut_affils (list): A list of author affiliations.
				- index (int): The index of the current affiliation.
				- affil_country (str): The country of the current affiliation.

				Returns:
				- aut_affil (str): The new affiliation name.

				'''
				aut_affil = aut_affils[index]
				if affil_country == 'fr' or affil_country == '':
					if 'university' in aut_affil.lower():
						index_university = aut_affil.lower().find('university')
						index_comma = aut_affil.lower().find(',', index_university)
						old_aut_affil = aut_affil.lower()[index_university:index_comma].strip()
						new_aut_affil = old_aut_affil.replace('university', 'universite')
						new_aut_affil = new_aut_affil.replace('of', '')
						aut_affils[index] += ', ' + new_aut_affil

				# If aut_affil contains acronym, extract the acronym.
				# Define a regular expression pattern to match "(XXX)"
				pattern = r'\((\w+)\)'
				# Use re.search to find the pattern in the string
				match = re.search(pattern, aut_affil)
				# Check if the pattern is found
				if match:
					# Extract the content inside the parentheses
					affi_acronym = match.group(1)
					aut_affils[index] = aut_affils[index].replace(' ({})'.format(affi_acronym), '')
					aut_affils[index] += ', ' + affi_acronym

				return aut_affil
			
				
			# Start handling the affiliations.

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
					
				# if affili_id is provided in authDB: Use them directly.
				if aut['affil_id']:
					affil_ids = aut['affil_id'].split(', ') 			
					# Create an 'affiliation' element for each id
					for affil_id in affil_ids:
						add_affiliation_by_affil_id(eAuth=eAuth, affil_id=affil_id)						
				else:
					# Extract the affiliation name from the search results.
					aut_affils = aut['affil']
					if aut_affils[0] == None:
						aut_affils = ['Unknown']
					affil_countries = aut['affil_country']
					affli_cities = aut['affil_city']
					author_name = {'forename': aut['forename'], 'surname': aut['surname']}

					aut_affils_ori = copy.deepcopy(aut_affils)
					# For french affiliations: Create a new affilation by replacing "university" to "universite"
					for index in range(len(aut_affils)):												
						affil_country = generate_abbreviation(affil_countries[index])
						affil_city = affli_cities[index]						
						
						# Defuzzy affili_unit.
						aut_affil = defuzzy_affil_name(aut_affils, index)
						# Enrich the affiliation name.
						aut_affil = enrich_affil_name(aut_affils, index, affil_country)
						

					# Loop for all the affliations from one author.						
					for index, aut_affil in enumerate(aut_affils):
						# Initially set to be not existed.
						affi_exist_in_hal = False
						affil_country = generate_abbreviation(affil_countries[index])
						affil_city = affli_cities[index]

						# Remove the ';' at the end of the affiliation. 
						if aut_affil.endswith('; '):
							aut_affil = aut_affil.rstrip('; ')

						# If the affliation is like department XXX, University XXX.
						# If so, extract the department and then university name.
						aut_affil_list = aut_affil.split(', ')

						# Rearrange the order of the parts.
						keywords_to_move_last = ['university', 'universite']
						for keyword in keywords_to_move_last:
							for part in aut_affil_list:
								if keyword in part.lower():
									aut_affil_list.remove(part)
									aut_affil_list.append(part)
						
						# In case "department of law, order, and XXX", this will generate too many items.
						if len(aut_affil_list)>=6:
							aut_affil_list = aut_affil_list[-1:]

						# Start to search from the right-most unit (largest):
						parent_affil_id = [] # Store all the parent affiliations. Use to exclude child affilation with the same name.
						for affil_unit in reversed(aut_affil_list):						            											
							affi_unit_exist_in_hal = False

							# Search for the valid affliations in HAL.
							try:
								search_result = self.reqHalRef(ref_name='structure', 
											value='(text:({}) valid_s:"VALID")'.format(affil_unit), 
											return_field='&fl=docid,label_s,address_s,country_s,parentName_s,parentDocid_i,parentValid_s&wt=json&rows=100')
							except:
								search_result = [0]
								pass							
							# Get the best-matched one and add it to the xml-tree.
							affi_unit_exist_in_hal, affil_dict = pick_affiliation_in_hal(search_result, affil_country, affil_city, aut=author_name, affil_name=affil_unit, parent_affil_id=parent_affil_id)
							# If found, add to the xml tree.
							if affi_unit_exist_in_hal:
								parent_affil_id.append(affil_dict['docid'])
								if not affil_country:
									affil_country = affil_dict['country_s']
								add_affil_and_parent_affil(eAuth=eAuth, affil_dict=affil_dict)
								affi_exist_in_hal = True						
						
						# If the affiliation does not exist in HAL, add the affiliation manually.
						# If the affiliation is France, do not create new affiliation as HAL is used for evaluating affiliations, 
						# so there is a stricker rule regarding creating affiliations.
						if not affi_exist_in_hal and affil_country:
							if affil_country.lower() != 'fr' and affil_country != '':
								# Before adding new affiliation, check if the affiliation exists in HAL but not VALID
								# Search for the valid affliations in HAL.
								try:
									# Here we don't require that the affiliation in HAL is valid.
									aut_affil = aut_affils_ori[index]
									search_result = self.reqHalRef(ref_name='structure', 
												value='(text:"{}")'.format(aut_affil), 
												return_field='&fl=docid,label_s,address_s,country_s,parentName_s,parentDocid_i,parentValid_s&wt=json&rows=100')
								except:
									search_result = [0]
									pass
								affi_exist_in_hal, affil_dict = pick_affiliation_in_hal(search_result, affil_name=aut_affil, invalide_affil=True)
								if not affi_exist_in_hal:
									new_affiliation_idx, new_affliation = add_new_affiliation(new_affiliation_idx, new_affliation, aut_affil) 
								else: # If invalid affiliation exist in HAL.
									add_affiliation_by_affil_id(eAuth=eAuth, affil_id=affil_dict['docid'])						
							

			# In the end, if no new affiliations are added, remove the 'eBack' element.
			if new_affiliation_idx == 0:
				eBack_Parent = root.find('tei:text', ns)
				eBack = root.find('tei:text/tei:back', ns)
				eBack_Parent.remove(eBack)

		
		def parse_bib_info():
			''' Parse bib info like journal, page, keywords, etc.
			'''
			## ADD SourceDesc / bibliStruct / monogr : isbn
			eMonogr = root.find(biblStructPath+'/tei:monogr', ns)
			idx_item = 0

			## ne pas coller l'ISBN si c'est un doctype COMM sinon cela créée une erreur (2021-01)
			if dataTei['isbn']  and not dataTei['doctype'] == 'COMM':  
				eIsbn = ET.Element('idno', {'type':'isbn'})
				eIsbn.text = dataTei["isbn"]
				eMonogr.insert(idx_item, eIsbn)
				idx_item += 1

			## ADD SourceDesc / bibliStruct / monogr : issn
			# if journal is in Hal
			if dataTei['journalId'] :
				eHalJid = ET.Element('idno', {'type':'halJournalId'})
				eHalJid.text = dataTei['journalId']
				eHalJid.tail = '\n'+'\t'*8
				eMonogr.insert(idx_item, eHalJid)
				idx_item += 1

			# if journal not in hal : paste issn
			if not dataTei['doctype'] == 'COMM':
				if not dataTei['journalId'] and dataTei["issn"] :
					eIdIssn = ET.Element('idno', {'type':'issn'})
					eIdIssn.text = dataTei['issn']
					eIdIssn.tail = '\n'+'\t'*8
					eMonogr.insert(idx_item, eIdIssn)
					idx_item += 1

			# if journal not in hal and doctype is ART then paste journal title
			if not dataTei['journalId'] and dataTei['doctype'] == "ART" : 
				eTitleJ = ET.Element('title', {'level':'j'})
				eTitleJ.text =  pub_name
				eTitleJ.tail = '\n'+'\t'*8
				eMonogr.insert(idx_item, eTitleJ)
				idx_item += 1

			# if it is COUV or OUV paste book title
			if dataTei['doctype'] == "COUV" or dataTei['doctype'] == "OUV" :
				eTitleOuv = ET.Element('title', {'level':'m'})
				eTitleOuv.text = pub_name
				eTitleOuv.tail = '\n'+'\t'*8
				eMonogr.insert(idx_item, eTitleOuv)
				idx_item += 1

			## ADD SourceDesc / bibliStruct / monogr / meeting : meeting
			if dataTei['doctype'] == 'COMM' : 
				#conf title
				eMeeting = ET.Element('meeting')
				eMonogr.insert(idx_item, eMeeting)
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
					if issue: 
						if isinstance(issue, str):
							e.text = issue 
						else:
							if not math.isnan(issue):
								e.text = str(int(issue))
				if e.get('unit') == 'volume' : 
					if volume: 
						if isinstance(volume, str):
							e.text = volume 
						else:
							if not math.isnan(volume):
								str(int(volume))
				if e.get('unit') == 'pp' : 
					if page_range and isinstance(page_range, str): e.text = page_range 
				if e.tag.endswith('date') and isinstance(cover_date, str): e.text = cover_date
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


		# Prepare differe parts of the tree.		
		parse_funder()
		parse_stamp()
		parse_title()
		parse_authors()
		parse_bib_info()			

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

		base_path = './data/outputs/TEI/'
		# Check if the directory exists
		if not os.path.exists(base_path):
			# If it doesn't exist, create the directory
			os.makedirs(base_path)
		
		xml_path = base_path + docId['eid'] + ".xml"
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

		Returns: None
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


def generate_search_query(da_path):
	'''
	Generates a search query for the HAL API.

	Parameters:
	- da_path (str): path to the database.

	Returns:
	str: Search query.

	'''


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
            search_query_author += 'AUTHOR-NAME({}, {}) OR '.format(row['Family name'], row['First name'][0])
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
	

