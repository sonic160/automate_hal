from typing import Any
from pybliometrics.scopus import AuthorRetrieval, AbstractRetrieval, ScopusSearch
import csv, json, requests, os, re, math, copy, json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from unidecode  import unidecode 
import pycountry as pycountry


class AutomateHal:
	'''
	Base class for the HAL Automator. Using its method process_one_paper, it does the following tasks:
	- retrieve the needed information for uploading the paper to HAL;
	- for each author affiliation, check if it exists in HAL and get the docid of the existed affiliations;
	- generate the Tei file for each paper;
	- upload the Tei file to HAL;
	- generate the report file.

	Attributes:
	- `additional_logs`: Additional logs stored as a list.
	- `affil_db_path`: Path to the affiliation database file.
	- `affiliation_db`: Pandas DataFrame representing the affiliation database.
	- `affiliation_db_exist`: Boolean indicating whether the affiliation database exists.
	- `allow_create_new_affiliation`: Boolean indicating whether to allow creating a new affiliation.
	- `AuthDB`: A dictionary that stores user-defined data to refine the search results.
	- `debug_log_file`: List to store debug log file paths.
	- `debug_affiliation_search`: Boolean indicating whether to run in debug mode. If True, not verifying if existed in HAL.
	- `hal_pswd`: HAL password for authentication.
	- `hal_user_name`: HAL username for authentication.
	- `ite`: Index of the current literature.
	- `log_file`: List to store log file paths.
	- `mode`: Mode of operation, either 'search_query' or 'csv'.
	- `output_path`: Path for storing output data.
	- `report_entry`: A dictionary template for report entries.
	- `report_file`: List to store report file paths.
	- `stamps (list)`: A list of stamps to be used in the Tei files. Example: ['stamp_1', 'stamp_2']
	- `debug_hal_upload`: Boolean indicating whether to upload the document reference to the HAL repository.
	- `auths` (list): A list of dictionaries to store information about the authors. Each element is a dictionary containing the following keys:
		- 'surname': Author's surname,
		- 'initial': Author's initials,
		- 'forename': Author's forename,
		- 'scopusId': Scopus ID of the author,
		- 'orcid': ORCID identifier of the author,
		- 'mail': Boolean indicating email presence,
		- 'corresp': Boolean indicating corresponding author status,
		- 'affil': List of author affiliations,
		- 'affil_city': List of cities associated with author affiliations,
		- 'affil_country': List of countries associated with author affiliations,
		- 'affil_address': List of addresses associated with author affiliations,
		- 'affil_postalcode': List of postal codes associated with author affiliations,
		- 'affil_id': Author's affiliation ID,
		- 'affil_id_invalid': Invalid affiliation ID,
		- 'affil_status': List of affiliation status,
		- 'affil_not_found_in_hal': List of affiliations not found in HAL,
		- 'idHAL': Author's HAL identifier.
	- `doc_data` (dict): A dictionary to store information about the current document with the following keys:
		- 'eid': Document's EID (Electronic Identifier),
		- 'doi': Document's DOI (Digital Object Identifier),
		- 'doctype': Document's type,
		- 'title': Document's title,
		- 'funding': Document's funding status,
		- 'funding_text': Textual description of document's funding,
		- 'language': Document's language,
		- 'isbn': Document's ISBN (International Standard Book Number),
		- 'confname': Conference name if applicable,
		- 'confdate': Conference date if applicable,
		- 'conflocation': Conference location if applicable,
		- 'startingPage': Document's starting page,
		- 'endingPage': Document's ending page,
		- 'publisher': Document's publisher.
   
	Methods:

	'''

	def __init__(self, perso_data_path='', author_db_path='', affil_db_path='',
			  AuthDB='', mode='search_query', stamps=[], 
			  debug_affiliation_search=False, debug_hal_upload=True, allow_create_new_affiliation=False, 
			  report_file=[], log_file=[], debug_log_file=[], auths=None, doc_data=None, report_entry=None,
			  affiliation_db=None):
		
		''' ### Description

		Initialize the AutomateHal object with HAL credentials, stamps, and loads valid authors' data.

		### Parameters:
		- `perso_data_path` (path): Path to the JSON file containing the personal data of the authors. If provided, the personal data will be loaded from this file during initialization.
		- `author_db_path` (path): Path to the CSV file containing the validated author data. If provided, the validated author data will be loaded from this file during initialization.
		- `affil_db_path` (path): Path to the affiliation database file. This file is used to store and retrieve affiliation data.
		- `AuthDB` (object): A dictionary that stores user-defined data to refine the search results. This can include additional information or preferences that the user wants to use in the search process.
		- `mode` (str): Mode of operation, either 'search_query' or 'csv'. Determines how the AutomateHal object will process data.
		- `stamps` (list): A list of stamps to be used in the Tei files. Example: `['stamp_1', 'stamp_2']`. These stamps are applied to the Tei files generated during the process.
		- `debug_affiliation_search` (bool): Boolean indicating whether to run in debug mode. If True, the system will not verify if the data already exists in HAL.
		- `debug_hal_upload` (bool): Boolean indicating whether to upload the document reference to the HAL repository. If True, the system will upload relevant information to the HAL repository.
		- `allow_create_new_affiliation` (bool): Boolean indicating whether to allow creating a new affiliation. If True, the system can create a new affiliation if needed.
		- `report_file` (list): List to store report file paths. Each report file contains information about the processed data and outcomes.
		- `log_file` (list): List to store log file paths. Log files contain general information and events during the execution of the AutomateHal object.
		- `debug_log_file` (list): List to store debug log file paths. Debug log files contain detailed debugging information for troubleshooting.
		- `affiliation_db` (pd.DataFrame): Pandas DataFrame representing the affiliation database with specified columns:
			- 'affil_name', 'status', 'valid_ids', 'affil_names_valid', 'invalid_ids', 'affil_names_invalid'. This DataFrame stores information about affiliations.
		- `auths` (list): A list of dictionaries to store information about the authors.
		- `doc_data` (dict): A dictionary to store information about the current document.


		### Defaults:

		- `perso_data_path=''`
		- `author_db_path=''`
		- `affil_db_path=''`
		- `AuthDB=''`
		- `mode='search_query'`
		- `stamps=[]`
		- `debug_affiliation_search=False`
		- `debug_hal_upload=True`
		- `allow_create_new_affiliation=False`
		- `report_file=[]`
		- `log_file=[]`
		- `debug_log_file=[]`
		- `affiliation_db=pd.DataFrame(columns=['affil_name', 'status', 'valid_ids', 'affil_names_valid', 'invalid_ids', 'affil_names_invalid'])`
		- `auths=None`
		- `doc_data=None`
		'''

		# Initialize the attributes.
		self.hal_user_name = '' # HAL username
		self.hal_pswd = '' # HAL password
		self.AuthDB = AuthDB # A dictionary that stores user-defined data to refine the search results.
		self.mode = mode # Mode of operation: search_query or csv
		self.ite = -1 # Index of the current iterature.
		self.stamps = stamps # List of stamps to be used in the Tei files.
		self.debug_affiliation_search = debug_affiliation_search # Whether to run in debug mode. If True, not verifying if existed in HAL.
		self.debug_hal_upload = debug_hal_upload # Whether to upload the documet reference to the HAL repository.
		self.output_path = './data/outputs/'
		self.report_file = report_file
		self.log_file = log_file
		self.debug_log_file = debug_log_file
		self.additional_logs = []
		self.affiliation_db_exist = False
		self.affil_db_path = affil_db_path
		self.allow_create_new_affiliation = allow_create_new_affiliation

		# auths: A list of dictionaries to store information about the authors.
		if not auths==None:
			self.auths = auths
		else:
			self.auths = []

		# doc_data: A dictionary to store information about the current document.
		if not doc_data==None:
			self.doc_data = doc_data
		else:			
			self.doc_data = {
				'eid': '', 
				'doi': '', 
				'doctype': '', 
				'title': '',
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
			}

		if report_entry == None:
			self.report_entry = {
				'eid': '',
				'doi': '',			
				'doctype': '',
				'title': '',
				'authors': '', 
				'exit_state': '',
				'hal_id': '',
				'hal_url': '',
				'emails_auths': ''
			}
		else:
			self.report_entry = report_entry

		if isinstance(affiliation_db, pd.DataFrame):
			self.affiliation_db = affiliation_db
		else:
			self.affiliation_db = pd.DataFrame(columns=
				['affil_name', 'status', 'valid_ids', 'affil_names_valid', 'invalid_ids', 'affil_names_invalid', 'eid', 'author', 'affil_city'])
					
		# Check mode:
		if mode != 'search_query' and mode != 'csv':
			raise ValueError('mode must be either "search_query" or "csv".')

		# Load the personal credentials and author database.
		self.load_data_and_initialize(perso_data_path, author_db_path, affil_db_path)



	def load_data_and_initialize(self, perso_data_path, author_db_path, affil_db_path):
		""" ### Description
		Loads local data, HAL credentials, and valid authors database.
		Initializes CSV output for system log.

		### Parameters:
		- `perso_data_path` (str): Path to the personal data file.
		- `author_db_path` (str): Path to the valid authors database file.
		- `affil_db_path` (str): Path to the affiliation database file.
		"""
		# Load local data: path and personal data
		if not perso_data_path == '':
			with open(perso_data_path) as fh:
				local_data = json.load(fh)

			# Get HAL credentials
			self.hal_user_name = local_data.get("perso_login_hal")
			self.hal_pswd = local_data.get("perso_mdp_hal")

		# Load valid authors database
		if not author_db_path == '':
			with open(author_db_path, 'r', encoding="utf-8") as auth_fh:
				reader = csv.DictReader(auth_fh)
				self.AuthDB = {row['key']: row for row in reader}

		# Load affiliation valid hal ids from past searches.
		if not affil_db_path == '':
			if '.json' in affil_db_path:
				# Read the JSON file and create a DataFrame
				self.affiliation_db = pd.read_json(affil_db_path, lines=True)
				self.affiliation_db_exist = True
			elif '.csv' in affil_db_path:
				# Read from csv.
				self.affiliation_db = pd.read_csv(affil_db_path)
				self.affiliation_db_exist = True				

		# Check if the output directory exists
		if not os.path.exists(self.output_path):
			# If it doesn't exist, create it
			os.makedirs(self.output_path)


	def hal_upload(self, filepath):
		"""
		Uploads TEI XML file to HAL using SWORD protocol.

		Parameters:
		- filepath (str): Path to the TEI XML file.

		Returns: None
		"""

		url = 'https://api.archives-ouvertes.fr/sword/hal'

		if self.debug_hal_upload:
			# If debug mode, add X-test header: Only test for correctness without actually uploading.
			head = {
				'Packaging': 'http://purl.org/net/sword-types/AOfr',
				'Content-Type': 'text/xml',
				'X-Allow-Completion': None,
				'X-test': '1'
			}
		else:
			# If no debug, upload.
			head = {
				'Packaging': 'http://purl.org/net/sword-types/AOfr',
				'Content-Type': 'text/xml',
				'X-Allow-Completion': None
			}

		# If pdf: Content-Type: application/zip

		xmlfh = open(filepath, 'r', encoding='utf-8')
		xmlcontent = xmlfh.read()  # The XML must be read, otherwise import time is very long
		xmlcontent = xmlcontent.encode('UTF-8')

		# if len(xmlcontent) < 10:
		# 	self.addRow(doc_id, "HAL upload: Success", '', 'File not loaded', '', '')
		# 	quit()

		response = requests.post(url, headers=head, data=xmlcontent, auth=(self.hal_user_name, self.hal_pswd))
		if response.status_code == 202:
			# Get the hal id and urls of the uploaded file.
			hal_id, hal_url = self.process_hal_upload_response(response=response)
			
			print("Process finished: HAL upload: Success")
			self.add_an_entry_to_log_file(self.log_file, "Process finished: HAL upload: Success")
			self.update_dictionary_fields(self.report_entry, fields=['exit_state', 'hal_id', 'hal_url'], values=['Added to HAL', hal_id, hal_url])
		else:
			# self.addRow(doc_id, "HAL upload: Error", '', response.text, '', '')
			print("HAL upload: Error")
			print(response.text)
			self.add_an_entry_to_log_file(self.log_file, "HAL upload fails!")
			self.add_an_entry_to_log_file(self.log_file, response.text)

		xmlfh.close()


	def preprocess_affil_name(self, affil_name):
		''' ### Description
		Preprocess the input affiliation name. Preprocessing includes:
		- Remove accents and other special characters in french.
		- Remove special characters like "#&-".
		- Remove "of" and "the" in the affiliation name.
		- Change into lower cases.
		- Correct some common typos.
		
		### Parameters:
		- affil_name (str): Affiliation name to preprocess.
		
		### Returns:
		- affil_name (str): Preprocessed affiliation name.
		'''
		replacements = [
				('electricite de france', 'edf'),
				('mines paristech', 'mines paris - psl'),
				('ecole ', ''),
				('randd', 'r d'),
				('centralesupelec universite', 'centralesupelec, universite'),
				('centralesupelec/universite', 'centralesupelec, universite')
				# Add more replacement pairs as needed
			]

		# Remove french special characters and change into lower cases.
		output_string = unidecode(affil_name).lower()

		# Replace common typos.
		for old_str, new_str in replacements:
			output_string = output_string.replace(old_str, new_str)

		# Remove "of" and "de":
		output_string = re.sub(r'\b(de |of )\b', '', output_string)
		
		# Use the re.sub function to remove "&" and "-" symbols
		output_string = re.sub(r'\s*[&-]\s*', ' ', output_string)

		# Remove the extra space between the words.
		words = output_string.split()

		# Join the words back together with a single space between them
		output_string = ' '.join(words)


		return output_string


	def process_hal_upload_response(self, response):
		''' ### Description
		Get from the response of hal upload the id and url of the uploaded files.

		### Parameters:
		- response (str): Response of the HAL API.

		### Returns:
		- hal_id (str): HAL id of the uploaded file.
		- url_in_hal (str): URL of the uploaded file in HAL.
		
		'''
		# Your XML content
		xml_content = response._content

		# Parse the XML content
		root = ET.fromstring(xml_content)

		# Extract the <id> field
		hal_id = root.find(".//{http://www.w3.org/2005/Atom}id").text

		# Extract strings after href=
		url_in_hal = [link.attrib.get('href', '') for link in root.findall(".//{http://www.w3.org/2005/Atom}link")]

		return hal_id, url_in_hal


	def reqHal(self, search_category='search', field='text', value='', search_query='',
			suffix='&fl=uri_s,title_s&wt=json'):
		"""
		Performs a request to the HAL API based on the specified field and value.

		Parameters:
		- field (str): Field to search in (e.g., 'title_t', 'doiId_id').
		- value (str): Value to search for (default: "").

		Returns:
		list: List containing the number of items found and a list of HAL documents.
			Example: [2, [{'uri_s': 'uri1', 'title_s': 'Title 1'}, {'uri_s': 'uri2', 'title_s': 'Title 2'}]]
		"""

		hal_api_entry_url = 'https://api.archives-ouvertes.fr/'
		prefix = hal_api_entry_url + search_category + '/?&q='

		if not search_query=='':
			req = prefix + search_query + suffix
		else:
			req = prefix + field + ':' + str(value) + suffix

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
	

	def reqWithIds(self, doi):
		"""
		Searches in HAL to check if the DOI is already present.

		Parameters:
		- doi (str): Document DOI.

		Returns:
		list: List containing the number of items found and a list of HAL URIs.
			Example: [2, [url, docid]]
		"""

		idInHal = [0, []]  # Number of items, list of URIs

		# Check if doi is empty:
		if doi == '':
			return idInHal

		# Perform a HAL request to find documents by DOI
		suffix='&fl=uri_s,docid&wt=json'
		reqId = self.reqHal(field='doiId_id', value=doi, suffix=suffix)

		return reqId


	def reqWithTitle(self, title):
		"""
		Searches in HAL to check if a record with the same title exists.

		Parameters:
		- titles (list): List of titles to search for.

		Returns:
		list: List containing the number of items found and a list of HAL URIs.
			Example: [2, ['uri1', 'uri2']]
		"""

		title = re.sub(r'&amp;', ' ', title)
		title = re.sub(r'[^a-zA-Z0-9 ]', '', title)		

		# Perform a HAL request to find documents by title
		search_query = 'title_t:('+ title + ')'
		suffix='&fl=uri_s,docid&wt=json'
		reqTitle = self.reqHal(search_query=search_query, suffix=suffix)

		
		return reqTitle
	

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


	def reqHalRef(self, ref_name, search_query="", return_field="&fl=docid,label_s&wt=json"):
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

		# Encode the value to deal with special symbols like &
		search_query = re.sub(r'&amp;', '& ', search_query)
		search_query = re.sub(r'&', ' ', search_query)

		[num, docs] = self.reqHal(search_category='ref/{}'.format(ref_name), 
							search_query=search_query, suffix=return_field)

		return [num, docs]	


	def update_dictionary_fields(self, input_dict, fields=[], values=[], reset_value=False):
		''' ### Description
		Given an input dictionary, this function will update some fields with given values.

		### Parameters: 
		- `input_dict` (dict): Dictionary to be updated.
		- `fields` (list): List of fields to be updated.
		- `values` (list): List of values to be added to the fields.				
		- `reset_value` (bool): If True, the value of the field will be reset to an empty string. (default: False).)
		'''

		# Get all the filed names.
		keys = input_dict.keys()

		# If the field name matches keys, save the value.
		# Otherwise, raise an error.
		if not reset_value:
			for key in fields:
				if key in keys:
					input_dict[key] = values.pop(0)
				else:
					raise ValueError('Error when writing to fields to a dictionary. field_name={} not found! \n Existing keys:{}'.format(key, keys))
		else:
			for key in keys:
				input_dict[key] = ''



	def add_an_entry_to_log_file(self, log_file, log_entry):
		''' ### Description
		Add an entry to the log files. The log files need to be a list, while the log_entry must be a dictionary. 

		### Parameters: 
		- `log_file` (list): pointers to the log_file: Must be a list. Choose from the following:
			- self.log_file, 
			- self.debug_log_file
			- self.report_file
		- `log_entry` (dict): Log entry to be added to the log file.
		'''
		if isinstance(log_file, list):
			log_file.append(log_entry)
		else:
			raise ValueError('Error while adding log entry: log_file must be a list!')
		

	def dump_log_files(self, additional_logs=[], names_for_additional_logs=[]):
		''' ### Description
		Saves the logs to the output directory.

		### Parameters: 
		- `additional_logs` (list): List of log files to be saved.
		- `names_for_additional_logs` (list): Names for additional logs (including path).
		'''

		def save_as_json_file(data, json_file_path):
			'''
			Dump data to a json file.
			'''

			# If outputing affiliation_db, first check if existing database exist.
			if 'affiliation_db' in json_file_path:
				if self.affiliation_db_exist:
					json_file_path = self.affil_db_path

			# Check if the path exists, if not, create it
			if not os.path.exists(os.path.dirname(json_file_path)):
				try:
					os.makedirs(os.path.dirname(json_file_path))
				except OSError as e:
					print(f"Error creating directory: {e}")

			if isinstance(data, pd.DataFrame):
				# data.to_json(json_file_path, orient='records', lines=True)
				
				# Save to csv.
				data.to_csv(json_file_path, index=False)
			else:
				json_output = json.dumps(data, indent=4)

				# Write the JSON string to the file
				with open(json_file_path, 'w') as json_file:
					json_file.write(json_output)


		# Define log files to be saved.
		output_file_name = ['log.json', 'treatment_report.json', 'affiliation_db.csv']
		logs = [self.log_file, self.report_file, self.affiliation_db]
	
		for idx, log in enumerate(logs):
			json_file_path = '{}{}'.format(self.output_path, output_file_name[idx])
			save_as_json_file(log, json_file_path)
			
		for idx, additional_log in enumerate(additional_logs):
			save_as_json_file(additional_log, names_for_additional_logs[idx])

	
	def process_papers(self, df_result, row_range=[0, 200]):
		''' ### Description
		This is the entry point of the main function. It iterates over all the papers in the scopus search results, 
		extract information, and upload it to HAL.

		### Parameters: 
		- `df_result` (DataFrame): DataFrame containing the search results from Scopus.		
		- `row_range` (list): List of the range of rows to be processed. Default: [0, 200].
		'''

		# Address the record in the scopus dataset one by one.
		n = len(df_result)
		for i, doc in df_result.iterrows():
			if 'row_range' in locals():
				# For debugging: Limit to first rowRange records.
				if i < min(row_range) : continue
				elif i > max(row_range) : break
			
			# Update the iteration index.
			self.ite = i
			print('{}/{} iterations: {}'.format(i+1, n, doc['eid']))
			self.add_an_entry_to_log_file(self.log_file, 
				'{}/{} iterations: {}'.format(i+1, n, doc['eid']))
			# Process the corresponding paper.
			try:
				self.process_one_paper(doc)
			except Exception as error:
				print('Error processing paper: {}. Log saved.'.format(doc['eid']))
				self.add_an_entry_to_log_file(self.log_file, 
				'Error is: {}'.format(error))

				# Save the log files.
				if self.debug_affiliation_search:
					self.dump_log_files(additional_logs=[self.additional_logs], 
						names_for_additional_logs=['./data/outputs/debug_logs/step_by_step_log.json'])
				else:
					self.dump_log_files()
			# Log the report entry for the current paper.
			self.add_an_entry_to_log_file(self.report_file, copy.deepcopy(self.report_entry))
			self.update_dictionary_fields(input_dict=self.report_entry, reset_value=True)


		# Save the log files.
		if self.debug_affiliation_search:
			self.dump_log_files(additional_logs=[self.additional_logs], 
				names_for_additional_logs=['./data/outputs/debug_logs/step_by_step_log.json'])
		else:
			self.dump_log_files()


	def process_one_paper(self, doc):
		""" ### Description
		Process each paper.
		- Parse data, get the needed information.
		- Check for each author affiliation, if it exists in HAL already.
		- Generate TEI-XML file.
		- Upload to HAL.
		- Create a report of the papers treated.

		### Parameters:
		- `doc`: a dictionary of the paper data from Scopus search.
		"""

		# Create a paper information treator.
		paper_info_handler = TreatPaperInformation(
			mode=self.mode, debug_affiliation_search=self.debug_affiliation_search, AuthDB=self.AuthDB,
			log_file=self.log_file, debug_log_file=self.debug_log_file, report_entry=self.report_entry)

		# Get the docids and document type.
		paper_info_handler.extract_docids_and_doc_type(doc)
		# Write to the report
		self.update_dictionary_fields(self.report_entry, fields=['eid', 'doi', 'doctype', 'title', 'authors',],
			values=[paper_info_handler.doc_data['eid'], paper_info_handler.doc_data['doi'], paper_info_handler.doc_data['doctype'], 
			paper_info_handler.doc_data['title'], doc['author_names']])

		# Verify if the paper is already in HAL.
		if not self.debug_affiliation_search and not self.debug_hal_upload:
			# Check if the paper is already in HAL.
			if paper_info_handler.verify_if_existed_in_hal(doc):
				self.add_an_entry_to_log_file(self.log_file, 'Process finished: Already exist in HAL.')
				self.report_entry['exit_state'] = 'Already in HAL'
				return
		# If debug_affiliation_search is True, skip the hal existance check:
		else:
			self.add_an_entry_to_log_file(self.log_file, 'Debug mode: Skip check existing in Hal.')
			
		# Extract & enrich authors data
		ab = paper_info_handler.extract_author_infomation()

		# from auth_db.csv get the author's affiliation structure_id in HAL.
		paper_info_handler.enrich_with_AuthDB()
		
		# Complement the paper data based on the Abstract Retrival API.
		paper_info_handler.extract_complementary_paper_information(ab)

		# Write author emails to the report, if there are any.	
		emails = [elem["mail"] for elem in paper_info_handler.auths if elem["mail"]]
		self.report_entry['emails_auths'] = ", ".join(emails)

		# Search the affiliations in HAL and get the ids.

		# Create an affiliation search object.
		affiliation_finder_hal = SearchAffilFromHal(auths=paper_info_handler.auths, doc_data=paper_info_handler.doc_data,
			mode=paper_info_handler.mode, debug_affiliation_search=paper_info_handler.debug_affiliation_search, 
			log_file=paper_info_handler.log_file, debug_log_file=paper_info_handler.debug_log_file,
			affiliation_db=self.affiliation_db)
		
		# If not in debug mode, search the affiliations in HAL.
		if not self.debug_affiliation_search:
			affiliation_finder_hal.extract_author_affiliation_in_hal()
		else: # If in debug_affiliation_search, output step-by-step results in the search process.
			affiliation_finder_hal.debug_show_search_steps = True
			affiliation_finder_hal.extract_author_affiliation_in_hal()
			self.additional_logs.append(affiliation_finder_hal.log_for_affil_unit)
			affiliation_finder_hal.log_for_affil_unit = []

			# paper_info_handler.debug_affiliation_hal()

		# Create a TEI-XML file.
		
		# Create a TEI-XML producer.
		tei_producer = GenerateXMLTree(doc=doc, auths=paper_info_handler.auths, doc_data=paper_info_handler.doc_data,
			debug_affiliation_search=paper_info_handler.debug_affiliation_search, mode=paper_info_handler.mode, debug_hal_upload=self.debug_hal_upload, stamps=self.stamps, allow_create_new_affiliation=self.allow_create_new_affiliation)	
		
		# Generate the xml tree.
		tei_producer.generate_tree()

		# Output the tree to the given dictionary.
		tei_producer.export_tei_tree()

		self.add_an_entry_to_log_file(self.log_file, 'TEI-XML file generated.')		

		# Upload to HAL.
		if not self.debug_affiliation_search:
			self.hal_upload(filepath=tei_producer.xml_path)
		else:
			self.add_an_entry_to_log_file(self.log_file, 'Skip Hal uploading because we are in debug affiliation search mode.')
			self.update_dictionary_fields(self.report_entry, fields=['exit_state'], values=['TEI-XML file generated but HAL uploading skip as we are in debug affiliation mode.'])



class TreatPaperInformation(AutomateHal):
	''' ### Description
	This Subclass extracts information of each paper from its original scopus record for creating the tei-xml file. It also checks if the paper is already in HAL.
	
	It is a child class of AutomateHal. It inherent the attributes and methods from AutomateHal.

	### Attributes
	All the attributes are inherent from parents
	
	'''
	def __init__(self, mode='search_query', debug_affiliation_search=False, AuthDB=[], log_file=[], debug_log_file=[], report_entry=[]):
		'''
		### `__init__` Method
		#### Description:
		Initialize an object with specific attributes for handling author and document data.

		#### Parameters:
		- `mode` (str): Mode of operation, either 'search_query' or 'csv'. Determines how the object will process data.
		- `debug_affiliation_search` (bool): Boolean indicating whether to run in debug mode. If True, additional debugging information will be available.
		- `AuthDB` (list): A list of dictionaries that stores user-defined data to refine the search results. Each dictionary may contain additional information or preferences for the search process.
		- `log_file` (list): List to store log file paths. Log files contain general information and events during the execution of the object.
		- `debug_log_file` (list): List to store debug log file paths. Debug log files contain detailed debugging information for troubleshooting.	

		#### Defaults:
		- `mode='search_query'`
		- `debug_affiliation_search=False`
		- `AuthDB=[]`
		- `log_file=[]`
		- `debug_log_file=[]`
		'''
		super().__init__(mode=mode, debug_affiliation_search=debug_affiliation_search, AuthDB=AuthDB, log_file=log_file, debug_log_file=debug_log_file, report_entry=report_entry)		 
	

	def debug_affiliation_hal(self):
		'''
		This function is used for debugging the function of extracting valid author information from HAL.
		For each paper treated, it will log the related debugging information into "debug_affil.csv".

		'''
		auths = self.auths
		doc_data = self.doc_data
		
		log = [{'eid': doc_data['eid'], 'Paper title': doc_data['title']}]	

		for auth in auths:
			# print('Author name: {}'.format(auth['surname']))
			# print('Original affiliations: {}'.format(auth['affil']))
			
			affil_ids = auth['affil_id'].split(', ')			
			found_affil = ''
			for affil_id in affil_ids:
				if not affil_id == '':
					search_result = self.reqHalRef(ref_name='structure', 
								search_query='(docid:{})'.format(affil_id), 
								return_field='&fl=label_s&wt=json')
					if search_result[0]>0:				
						found_affil += '{} - {}, '.format(affil_id, search_result[1][0]['label_s'])
			found_affil = found_affil.strip(', ')
			# print('found ids: {}'.format(found_affil))

			affil_ids = auth['affil_id_invalid'].split(', ')
			found_affil_invalid = ''
			for affil_id in affil_ids:
				if not affil_id == '':
					search_result = self.reqHalRef(ref_name='structure', 
								search_query='(docid:{})'.format(affil_id), 
								return_field='&fl=label_s&wt=json')				
					found_affil_invalid += '{} - {}, '.format(affil_id, search_result[1][0]['label_s'])						
			found_affil_invalid = found_affil_invalid.strip(', ')
			
			log_entry = {
				'Author name': '{} {}'.format(auth['forename'], auth['surname']),
				'Affiliations from Scopus': str(auth['affil']),
				'affil_status': '{}'.format(auth['affil_status']),
				'affil_not_found_in_hal': '{}'.format(auth['affil_not_found_in_hal']),
				'ID valid': '{}'.format(found_affil),
				'ID invalid': '{}'.format(found_affil_invalid)
			}
			log.append(log_entry)	
		
		self.add_an_entry_to_log_file(self.debug_log_file, log)


	def extract_complementary_paper_information(self, ab):
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
		fileds = ['funding', 'funding_text', 'language', 'isbn', 'confname', 'confdate', 'conflocation', 'startingPage', 'endingPage', 'publisher']
		values = [ab.funding, ab.funding_text, ab.language, ab.isbn, ab.confname, confdate, ab.conflocation, ab.startingPage, ab.endingPage, ab.publisher]
		self.update_doc_data(field_names=fileds, values=values)


	def enrich_with_AuthDB(self):
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


	def extract_author_infomation(self):
		"""
		Extracts author information for the authors in a give paper, and then update the information in self.auths.

		Parameters: None.

		Returns: 
		- ab: An object containging the paper details from the Abstract Retrival API.
		"""      

		# Get details for each paper using AbstractRetrieval API.
		ab = AbstractRetrieval(self.doc_data['eid'], view='FULL')
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
					'affil_id_invalid': '',
					'affil_status': [],
					'affil_not_found_in_hal': [],
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


	def update_doc_data(self, field_names, values):
		'''
		### Description
		Update given fields in self.doc_data.
		
		### Parameters:
		- field_names (list): A list of fields to be updated.
		- values (list): A list of values to be updated.
		'''
		doc_data = self.doc_data

		self.update_dictionary_fields(doc_data, field_names, values)
		
		
	def extract_docids_and_doc_type(self, doc):
		'''
		Extract the document ID and document type from the input data.
		'''
		# Get the ids of each paper.
		field_names = ['eid', 'doi', 'doctype', 'title']
		if self.mode == 'search_query':
			doc_type_supported, doc_type = self.is_doctype_supported(doc['aggregationType'])
			if not doc_type_supported:
				raise ValueError('Document type not supported! doc_type={}'.format(doc_type))
			values = [doc['eid'], doc['doi'], doc_type, doc['title']]
			self.update_doc_data(field_names=field_names, values=values)			
		elif self.mode =='csv':
			doc_type_supported, doc_type = self.is_doctype_supported(doc['Document Type'])
			if not doc_type_supported:
				raise('Document type not supported! doc_type={}'.format(doc_type))
			values = [doc['EID'], doc['DOI'], doc_type, doc['Title']]
			self.update_doc_data(field_names=field_names, values=values)
		else: 
			raise ValueError('Please choose teh correct mode! Has to be "search_query" or "csv".')


	def is_doctype_supported(self, doctype):
		"""
		Matches Scopus document types to HAL document types, and update the self.doc_data['doctype'] dictionary.

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
			doctype = doctype_scopus2hal[doctype]
			return True, doctype
		else:			
			return False, doctype


	def verify_if_existed_in_hal(self, doc):
		"""
		Verify if the document is already in HAL.

		Parameters:
		- doc (dict): Document information.
		
		Returns: True if the document is already in HAL; False otherwise.

		"""

		# Verify if the publication existed in HAL.
		# First check by doi:
		idInHal = self.reqWithIds(self.doc_data['doi'])	
		
		if idInHal[0] > 0:
			print(f"already in HAL")
			self.report_entry['hal_url'] = idInHal[1][0]['uri_s']
			self.report_entry['hal_id'] = idInHal[1][0]['docid']

			return True
		else: # Then, check with title
			if self.mode == 'search_query':
				titleInHal = self.reqWithTitle(doc['title'])
			elif self.mode == 'csv':
				titleInHal = self.reqWithTitle(doc['Title'])
			else:
				ValueError("'mode' must be either 'search_query' or 'csv'!")
			if titleInHal[0] > 0:
				print(f"already in HAL")
				self.report_entry['hal_url'] = titleInHal[1][0]['uri_s']
				self.report_entry['hal_id'] = titleInHal[1][0]['docid']

				return True
			
		return False


class SearchAffilFromHal(AutomateHal):
	''' ### Description
	This Subclass searches if an affiliation exists in HAL. Based on the results, it save the HAL ids in self.auths.
	
	It is a child class of AutomateHal. It inherent the attributes and methods from AutomateHal.

	### Attributes
	It inherents all the attributes from AutomateHal.

	#### Private attributes
	- `debug_show_search_steps` (bool): A flag variable indicating whether to show the results after each filter step.
	- `log_for_affil_unit` (list): A log file for logging the results of the debugging process related to affiliation units.
	- `aut_affils_after_preprocess` (list): Affiliations after pre-processing in a single iteration.
	- `aut_affils_before_preprocess` (list): Original affiliations before pre-processing in a single iteration.
	- `current_author_name` (str): Current author name being processed.
	- `current_author_idx` (int): Index of the current author being processed.
	- `current_affil_idx` (int): Index of the current affiliation being processed.
	- `current_affil_country` (str): Affiliation country of the current affiliation being processed.
	- `current_affil_city` (str): Affiliation city of the current affiliation being processed.
	- `hal_ids_current_affil` (list): HAL IDs of the current affiliation that exists.
	- `hal_name_current_affil` (list): Associated names for the affiliations that exist in HAL.
	- `hal_ids_current_affil_invalid` (list): HAL IDs of the current affiliation that exists but is invalid.
	- `hal_name_current_affil_invalid` (list): Associated names for the affiliations that exist in HAL but are invalid.
	'''


	def __init__(self, auths=None, doc_data=None,
			  mode='search_query', debug_affiliation_search=False, log_file =[], 
			  debug_log_file=[], affiliation_db=None):
		'''
		### `__init__` Method

		#### Description:
		Initialize an object with specific attributes for handling author and document data, as well as variables used in a single iteration for searching and identifying affiliations.

		#### Parameters:
		- `auths` (list): A list of dictionaries containing information about authors. Each dictionary represents an author and may include keys such as 'surname', 'initial', 'forename', 'scopusId', 'orcid', etc.
		- `doc_data` (dict): A dictionary containing information about the current document, including keys such as 'eid', 'doi', 'doctype', 'title', 'funding', 'language', 'isbn', 'confname', 'confdate', 'conflocation', 'startingPage', 'endingPage', and 'publisher'.
		- `mode` (str): Mode of operation, either 'search_query' or 'csv'. Determines how the object will process data.
		- `debug_affiliation_search` (bool): Boolean indicating whether to run in debug mode. If True, additional debugging information will be availabl		
		- `log_file` (list): List to store log file paths. Log files contain general information and events during the execution of the object.
		- `debug_log_file` (list): List to store debug log file paths. Debug log files contain detailed debugging information for troubleshooting.
		- `affiliation_db` (object): An optional parameter representing an affiliation database. It is used to store and retrieve affiliation data.

		Defaults:
		- `auths=[]`
		- `doc_data={}`
		- `mode='search_query'`
		- `debug_affiliation_search=False`
		- `AuthDB=[]`
		- `log_file=[]`
		- `debug_log_file=[]`
		- `affiliation_db=None`
		'''

		super().__init__(mode=mode, debug_affiliation_search=debug_affiliation_search, log_file=log_file, 
				   debug_log_file=debug_log_file, affiliation_db=affiliation_db, auths=auths, doc_data=doc_data)
		
		# Private attributes
		self.debug_show_search_steps = False # A flag variable whether to show the results after each filter step.
		self.log_for_affil_unit = [] # A log file for logging the results of the debugging process.
		# Variables used in a single iteration for searching and identifying each affiliation:
		self.aut_affils_after_preprocess = [] # aut_affils: After pre-processing.
		self.aut_affils_before_preprocess = [] # aut_affils: Original value.
		self.current_author_name = '' # Current author name.
		self.current_author_idx = 0 # Current author index.
		self.current_affil_idx = 0 # Current author index.
		self.current_affil_country = '' # Affiliation country.
		self.current_affil_city = '' # Affiliation city.
		self.hal_ids_current_affil = [] # HAL ids of the current affiliation that exists.
		self.hal_name_current_affil = [] # Associated names for the affiliations exist in HAL.
		self.hal_ids_current_affil_invalid = [] # HAL ids of the current affiliation that exists but invalid.
		self.hal_name_current_affil_invalid = [] # Associated names for the affiliations exist in HAL.


	def add_parent_affil_ids(self, auth_idx, affil_dict):
		'''
		Given a valid affiliation id, add its parent docid if existed.
		'''
		
		parent_ids = []
		parent_names = []
		if 'parentValid_s' in affil_dict and 'parentDocid_i' in affil_dict:
			try:
				if not isinstance(pd.isna(affil_dict['parentDocid_i']), np.ndarray):
					if pd.isna(affil_dict['parentDocid_i']):
						return parent_ids, parent_names
					
				for idx, parent_id in enumerate(affil_dict['parentDocid_i']):					
					if affil_dict['parentValid_s'][idx]=='VALID' and pd.notna(parent_id):
						self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
							field_name='affil_id', field_value=parent_id)
						# Save parent id.
						parent_ids.append(parent_id)

						# Run a search to get parent name.
						search_result = self.reqHalRef(ref_name='structure', 
								search_query='(docid:{})'.format(parent_id), 
								return_field='&fl=label_s&wt=json')
						if search_result[0]>0:				
							parent_names.append(search_result[1][0]['label_s'])

			except:
				pass

		return parent_ids, parent_names


	def get_hal_ids_for_current_affil(self, old_ids, new_ids):
		set_A = set(old_ids.split(', '))
		set_B = set(new_ids.split(', '))
		# Find the added elements in B
		added_elements = set_B - set_A
		# Convert the result back to a string
		added_elements_string = ', '.join(added_elements)

		return added_elements_string
	

	def update_historical_database(self):
		'''
		Add the results from the current iteration to the historical database.
		'''

		# Get the database and affiliation name
		df_affiliation_db = self.affiliation_db
		affil_idx = self.current_affil_idx
		affil_name = self.aut_affils_before_preprocess[affil_idx]

		# Get the results after the current iteration. Read from self.auths, which is just updated.
		auth_idx = self.current_author_idx
		auth = self.auths[auth_idx]
		eid = self.doc_data['eid']
		affil_city = self.current_affil_city
		auth_name = '{} {}'.format(self.current_author_name['forename'], self.current_author_name['surname'])

		if len(auth['affil_status'])>0:
			new_row = {
				'affil_name': affil_name,
				'status': auth['affil_status'][affil_idx],
				'valid_ids': self.hal_ids_current_affil,
				'affil_names_valid': self.hal_name_current_affil,
				'invalid_ids': self.hal_ids_current_affil_invalid,
				'affil_names_invalid': self.hal_name_current_affil_invalid,
				'eid': eid,
				'author': auth_name, 
				'affil_city': affil_city
			}

			df_affiliation_db.loc[len(df_affiliation_db)] = new_row


	def search_from_historical_database(self):
		'''
		Search if the current affiliation name is in the historical database: self.affiliation_db.
		If so, copy the status directly.
		'''

		# Get affli name and search history.
		affil_name = self.aut_affils_before_preprocess[self.current_affil_idx]
		df_search_history = self.affiliation_db
		auth_idx = self.current_author_idx

		# Find in the history.
		if isinstance(affil_name, str): 
			df_result = df_search_history[df_search_history['affil_name'].str.lower() == affil_name.lower()]
		else: # If affili_name is not a string, return directly.
			return False
		
		# Verification conditions.
		eid = self.doc_data['eid']
		affil_city = self.current_affil_city
		auth_name = '{} {}'.format(self.current_author_name['forename'], self.current_author_name['surname'])

		df_eid = df_result[df_result['eid']==eid]
		df_city = df_result[df_result['affil_city']==affil_city]
		df_auth = df_result[df_result['author']==auth_name]

		if len(df_auth)>0:
			df_result = df_auth
		elif len(df_eid)>0:
			df_result = df_eid
		else:
			df_result = df_city

		# If found, get the status.
		if len(df_result)==0:
			return False
		else:
			status = df_result.iloc[0]['status']
		
		# Log the "affil_status".
		self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
			field_name='affil_status', field_value=status)

		# If exists in hal: Log the HAL ids.
		if status == 'In HAL (Valid)':
			ids_in_hal = df_result.iloc[0]['valid_ids']
			self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
				field_name='affil_id', field_value=ids_in_hal)
		
		# If exists in hal but invalid: Log the HAL ids.
		if status == 'In HAL (Not valid)':
			ids_in_hal_invalid = df_result.iloc[0]['invalid_ids']
			self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
				field_name='affil_id_invalid', field_value=ids_in_hal_invalid)
		
		# If not exists in hal: Log the affiliation name.
		if status == 'Not in HAL':
			self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
				field_name='affil_not_found_in_hal', field_value=affil_name)

		return True				


	def search_hal_and_filter_results(self):
		'''
		This function search in HAL for valid affiliation based on a given affiliation unit name. 
		Then, it performs a series of filters to make sure that only the correct match is used.
		If not found in HAL, it will launch another round of search but looking for invalid affiliation as well.
		If not found yet, depending on the user's choice, it will either skip the affiliation unit but mark it in a given field in self.auths.
		'''
		# Retrieve parameters.
		aut_affils = self.aut_affils_after_preprocess
		affil_idx = self.current_affil_idx
		auth_idx = self.current_author_idx
		author_name = self.current_author_name
		affil_country = self.current_affil_country
		affil_city = self.current_affil_city

		# Preprocess each auth affiliation.
		aut_affil = self.preprocess_affiliation_name(aut_affils, affil_idx, affil_country)									

		# Initially set to be not existed.
		affi_exist_in_hal = False				
		parent_affil_id = [] # Store all the parent affiliations. Use to exclude child affilation with the same name.
		
		self.hal_ids_current_affil = []
		self.hal_ids_current_affil_invalid = []
		self.hal_name_current_affil = []
		self.hal_name_current_affil_invalid = []

		# Generate affiliation list.
		if aut_affil == None: # If aut_affil is None, return with default value.
			return
		else:
			aut_affil_list = self.generate_affil_list(aut_affil)

		# Start to search from the right-most unit (largest):
		for affil_unit in reversed(aut_affil_list):						            											
			affi_unit_exist_in_hal = False										

			# Search for the valid affliations in HAL.
			try:				
				search_result = self.reqHalRef(ref_name='structure', 
							search_query='(text:({}) valid_s:"VALID")'.format(affil_unit), 
							return_field='&fl=docid,label_s,address_s,country_s,parentName_s,parentDocid_i,parentValid_s&wt=json&rows=100')
			except:
				# If problems, remove the symbols in affil_unit and try again.
				affil_unit = re.sub(r'[^a-zA-Z0-9\s]', '', affil_unit)
				try:				
					search_result = self.reqHalRef(ref_name='structure', 
							search_query='(text:({}) valid_s:"VALID")'.format(affil_unit), 
							return_field='&fl=docid,label_s,address_s,country_s,parentName_s,parentDocid_i,parentValid_s&wt=json&rows=100')
				except:	
					search_result = [0]
					pass

			# Get the best-matched one and add it to the xml-tree.
			affi_unit_exist_in_hal, affil_dict = self.pick_affiliation_from_search_results(search_result, affil_country, affil_city, aut=author_name, affil_name=affil_unit, parent_affil_id=parent_affil_id)
			# If found, add to the xml tree.
			if affi_unit_exist_in_hal:
				affi_exist_in_hal = True
				# Update teh parent_affil_id for future search.
				parent_affil_id.append(affil_dict['docid'])
				if not affil_country:
					affil_country = affil_dict['country_s']

				# Save the results to self.auths.
				self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
									field_name='affil_id', field_value=affil_dict['docid'])
				# Add parent id as well.
				parent_ids, parent_names = self.add_parent_affil_ids(auth_idx, affil_dict)

				# Save the current ids and names.
				self.hal_ids_current_affil.append(affil_dict['docid'])
				self.hal_name_current_affil.append(affil_dict['label_s_ori'])
				if isinstance(parent_ids, list):
					self.hal_ids_current_affil.extend(parent_ids)
					self.hal_name_current_affil.extend(parent_names)
				else:
					self.hal_ids_current_affil.append(parent_ids)
					self.hal_name_current_affil.append(parent_names)
				
		# If the affiliation does not exist in HAL, add the affiliation manually.
		# If the affiliation is France, do not create new affiliation as HAL is used for evaluating affiliations, 
		# so there is a stricker rule regarding creating affiliations.
		if affi_exist_in_hal:			
			self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
					field_name='affil_status', field_value='In HAL (Valid)')			
		elif affil_country:
			if affil_country.lower() != 'fr' and affil_country != '':
				# Before adding new affiliation, check if the affiliation exists in HAL but not VALID
				# Search for the valid affliations in HAL.
				try:
					# Here we don't require that the affiliation in HAL is valid.
					aut_affil = self.aut_affils_after_preprocess[affil_idx]
					search_result = self.reqHalRef(ref_name='structure', 
								search_query='(text:"{}")'.format(aut_affil), 
								return_field='&fl=docid,label_s,address_s,country_s,parentName_s,parentDocid_i,parentValid_s&wt=json&rows=100')
				except:
					search_result = [0]
					pass
				affi_exist_in_hal, affil_dict = self.pick_affiliation_from_search_results(search_result, affil_country, affil_city, aut=author_name, affil_name=affil_unit, invalid_affil=True)
				
				# If exist in HAL but not valid.
				if affi_exist_in_hal:
					self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
									field_name='affil_id_invalid', field_value=affil_dict['docid'])
					self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
						field_name='affil_status', field_value='In HAL (Not valid)')
					self.hal_ids_current_affil_invalid.append(affil_dict['docid'])
					self.hal_name_current_affil_invalid.append(affil_dict['label_s'])
	
		# If after checking invalid affiliations, still not found:
		if not affi_exist_in_hal:
			self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
				field_name='affil_status', field_value='Not in HAL')
			self.update_auths_fields_affil_from_hal(auth_idx=auth_idx, 
				field_name='affil_not_found_in_hal', field_value=self.aut_affils_before_preprocess[affil_idx])
		
		# Remove the redundant elements:
		self.hal_ids_current_affil = ', '.join(set(self.hal_ids_current_affil))
		self.hal_ids_current_affil_invalid = ', '.join(set(self.hal_ids_current_affil_invalid))
		self.hal_name_current_affil = ' | '.join(set(self.hal_name_current_affil))
		self.hal_name_current_affil_invalid = ' | '.join(set(self.hal_name_current_affil_invalid))


	def extract_author_affiliation_in_hal(self):
		'''
		This function check for each author in self.auths, and check if its affiliation exists in HAL and is an valid affiliation.
		There are three possibilities:
			- If yes, add the docid from HAL to `self.auths['affil_id']` and put the corresponding element in `self.auths['exist_in_hal']` to be `['Valid']`
			- If existed in Hal, but not valid, add the docid from HAL to self.auths['affil_id_invalid'] and put the corresponding element in self.auths['exist_in_hal'] to be ['Invalid']
			- If not existed in Hal, add it to self.auths['affil_not_in_hal'] and put the corresponding element in self.auths['exist_in_hal'] to be ['No']

		'''

		# Start searching the affiliation in HAL.
		auths = self.auths
		for auth_idx, aut in enumerate(auths):
			# If there are affiliations defined in AuthDB, skip this author.
			# Only extract for those not defined in AuthDB.
			if not aut['affil_id']:
				# Extract the affiliation name from the search results.
				self.aut_affils_before_preprocess = copy.deepcopy(aut['affil'])

				aut_affils = copy.deepcopy(aut['affil'])
				self.aut_affils_after_preprocess = aut_affils
				if aut_affils[0] == None:
					aut_affils = ['Unknown']

				affil_countries = aut['affil_country']
				affli_cities = aut['affil_city']
				self.current_author_name = {'forename': aut['forename'], 'surname': aut['surname']}
				self.current_author_idx = auth_idx

				for affil_idx in range(len(aut_affils)):
					self.current_affil_idx = affil_idx												
					# Get country and city of the affiliation.
					self.current_affil_country = self.generate_abbreviation(affil_countries[affil_idx])
					self.current_affil_city = affli_cities[affil_idx]

					# Check if the current affiliatio name exists in the historical database.
					# If true, update the related files and continue with the next affiliation.
					if self.search_from_historical_database():
						continue
					else:
						# Search HAL and find for the given affiliation.
						self.search_hal_and_filter_results()
												
						# Update the affiliation_db database.
						self.update_historical_database()
					


	# If too many candidates with parents, we drop this item as we are not sure to achieve confident extraction.
	# We count the number of parent institutions. If too many, this indicates that it is better to look at parent affiliations.
	def filter_by_affil_city(self, df_affli_found, affil_city, exact_filter=False):
		'''
		Given an input DataFrame of possible affiliations, find the best match for the specified pattern. 

		Parameters:
			- df_affli_found (pd.DataFrame): The DataFrame of possible affiliations.
			- affil_city (str): The city of the affiliation to be added. 
			- exact_filter (bool): If True, only return the matched ones. If false (default), return also the nans.

		Return:
			- df_affli_found (pd.DataFrame): The DataFrame of possible affiliations.
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

				# Condition 4: XXX [system]
				pattern = "[system]"				
				condition_4 = df_affli_found['label_s'].str.lower().str.contains(pattern, regex=False)

				if not exact_filter:
					df_affli_found = df_affli_found[condition_1 | condition_2 | condition_3 | condition_4]
				else:
					df_affli_found = df_affli_found[condition_1 | condition_2 | condition_4]
			else:
				df_affli_found = pd.DataFrame()
			
		return df_affli_found
	

	def filter_by_acronym_pattern(self, df_affli_found, affil_name):
		'''
		If affili_name is an acronym, we remove the candidates that do not contain patterns [affili_name].

		'''
		if not df_affli_found.empty:
			if len(affil_name.split(' ')) == 1:
				# Check for pattern [XXX]
				flag = df_affli_found['label_s'].str.contains('[{}]'.format(affil_name), regex=False)
				df_affli_found_1 = df_affli_found[flag]

				# Check for exact match
				df_affli_found_2 = df_affli_found[df_affli_found['label_s']==affil_name]

				# Remove repetitive rows.
				df_affli_found = pd.concat([df_affli_found_1, df_affli_found_2])
				df_affli_found = df_affli_found.drop_duplicates(subset='label_s', keep='first')

		return df_affli_found



	def filter_by_university_group(self, df_affli_found):
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
	

	def filter_by_prev_publications(self, df_affli_found, aut):
		affi_exist_in_hal = False
		best_affil_dict = {}

		if not df_affli_found.empty:
			# Check in the remaining candidates, if the authors appeared in HAL with the candidate affiliation before.
			flag = []
			for i in range(len(df_affli_found)):
				search_query = 'structId_i:{}&fq=auth_t:"{} {}"'.format(df_affli_found.iloc[i]['docid'], aut['forename'], aut['surname'])
				num, _ = self.reqHal(search_query=search_query)
				flag.append(num>0)
			if any(flag):
				df_affli_found = df_affli_found[flag]
				
				affi_exist_in_hal = True
				best_affil_dict = df_affli_found.iloc[0].to_dict()

		return affi_exist_in_hal, best_affil_dict
	

	def filter_by_country(self, df_affli_found, affil_country):
		if not df_affli_found.empty:		
			if 'country_s' in df_affli_found.columns:
				# Keep the rows that do not have parent affil ids.
				tmp_df_1 = df_affli_found[pd.isna(df_affli_found['country_s'])]
				
				# Keep the rows that have parent affil ids and the parent affil ids are in parent_affil_id.
				tmp_df_2 = df_affli_found[pd.notna(df_affli_found['country_s'])]
				tmp_df_2 = tmp_df_2[tmp_df_2['country_s']==affil_country]
				
				# Output the final results.
				df_affli_found = pd.concat([tmp_df_1, tmp_df_2])

		return df_affli_found


	def filter_by_parent_affil(self, df_affli_found, parent_affil_id):
		'''
		Filter based on the parent affiliation. If parent affiliations exist in parent_affil_id, remove the candidate affiliations 
		whose parent affiliations exist but not contained in parent_affil_id.

		Parameters:
			- df_affli_found (pd.DataFrame): The DataFrame of possible affiliations.
			- parent_affil_id (str): The id of the parent affiliation. 

		Return:
			- df_affli_found (pd.DataFrame): The DataFrame after filtering.
		'''
		if not df_affli_found.empty:
			if len(parent_affil_id) > 0:
				# If we have already some parent affils, we need to first screen the candidate results to remove 
				# those with different parent affil ids.
				if 'parentDocid_i' in df_affli_found.columns:
					# Keep the rows that do not have parent affil ids.
					tmp_df_1 = df_affli_found[pd.isna(df_affli_found['parentDocid_i'])]
					# tmp_df_1[tmp_df_1['label_s'].apply(unidecode).str.lower()==unidecode(affil_name).lower()]
					
					# Keep the rows that have parent affil ids and the parent affil ids are in parent_affil_id.
					tmp_df_2 = df_affli_found[pd.notna(df_affli_found['parentDocid_i'])]
					tmp_df_2 = tmp_df_2[tmp_df_2['parentDocid_i'].apply(lambda x: any(item in parent_affil_id for item in x))]
					
					# Output the final results.
					df_affli_found = pd.concat([tmp_df_1, tmp_df_2])
		
		return df_affli_found	
	

	def find_exact_match(self, df_affli_found, affil_name, affil_city):
		'''
		Find the exact match of the affiliation name. There are three ways: Exactly the same, affili_name + [Acronym], affil_name + [Location].

		Parameters:
			- df_affli_found (pd.DataFrame): The DataFrame of possible affiliations.
			- affil_name (str): The affiliation name to be added. 

		Return:

		'''
		if not df_affli_found.empty:
			# Define similar patterns.
			column_to_compare = df_affli_found['label_s']			
			
			# If there is exact matched affil name:
			df_exact = df_affli_found.loc[column_to_compare==affil_name, :]
			
			# # affil name [XXX]
			# pattern = re.compile(r'{} \[.*\]'.format(affil_name))
			# df_exact = pd.concat([
			# 	df_exact,
			# 	df_affli_found[[element is not None for element in column_to_compare.apply(pattern.match)]]
			# ])

			# affil name [City name]
			if pd.notna(affil_city):
				df_exact = pd.concat([
						df_exact,
						df_affli_found.reset_index()[column_to_compare=='{} [{}]'.format(affil_name.lower(), affil_city.lower())],	  
					])

			# if there is no affilation city, find all the matches in format of XXX [XXX], except for XXX [Location]
			pattern = re.compile(r'{} \[(.*?)\]'.format(affil_name.lower()))
			flag = []
			for idx, element in enumerate(column_to_compare.apply(pattern.match)):
				if element is not None and 'cleaned address_s' in df_affli_found.columns:
					if isinstance(df_affli_found.iloc[idx]['cleaned address_s'], str):
						if element.group(1) not in df_affli_found.iloc[idx]['cleaned address_s']:
							flag.append(True)
							continue
				flag.append(False)
			
			df_exact = pd.concat([
					df_exact,
					df_affli_found.reset_index()[flag],	  
				])
				
			# Check for duplicated values in the specified column
			# Keep only the rows where the 'label_s' column has unique values
			df_exact = df_exact.drop_duplicates(subset='label_s', keep='first')
		else:
			df_exact = df_affli_found
			
		return df_exact
	

	# Subfunction to transform a country name to its abbreviation.
	def generate_abbreviation(self, country_name):
		country = None
		if country_name:
			try:
				country = pycountry.countries.search_fuzzy(country_name)[0]
				country = country.alpha_2.lower()						
			except LookupError:
				pass
			
		return country
	
	
	def log_filter_steps_for_affil_unit(self, df_affil_found, aut, affil_name, filter_step):
		'''
		If debug_show_search_steps is True, log the results after each filter.
		'''
		if self.debug_show_search_steps:
			if isinstance(df_affil_found, dict):
				df_affil_found = pd.DataFrame([df_affil_found])
			
			log_entry = {
				'eid': self.doc_data['eid'],
				'title': self.doc_data['title'],
				'author': '{} {}'.format(aut['forename'], aut['surname']),
				'affiliation_name': affil_name,
				'affiliation_country': self.current_affil_country,
				'affiliation_city': self.current_affil_city,
				'filter step': filter_step,
				'df_affil_found': df_affil_found.to_json(orient='records', lines=True),
				'len(df_affil_found)': len(df_affil_found)
			}
			
			self.log_for_affil_unit.append(log_entry)
			


	# Generate affiliation list.
	def generate_affil_list(self, aut_affil):
		# Seperate the different terms by ",".
		aut_affil_list = aut_affil.split(', ')

		# Rearrange the order of the parts.
		keywords_to_move_last = ['university', 'universite']
		for keyword in keywords_to_move_last:
			for part in aut_affil_list:
				if keyword in part.lower():
					aut_affil_list.remove(part)
					aut_affil_list.append(part)
		
		# # In case "department of law, order, and XXX", this will generate too many items.
		# # If too many sub items, only take the first one.
		# if len(aut_affil_list)>=6:
		# 	aut_affil_list = aut_affil_list[-1:]

		return aut_affil_list
	

	# Define a function to sort df_affli_found based on the number of words in the affliation name.
	def sort_by_name_length(self, df):																			
		# Function to calculate the number of words in a string
		def count_words(text):
			return len(text.split())

		if df.empty:
			return df
		else:										
			# Add a new column 'word_count' with the number of words in 'label_s'
			df['word_count'] = df['label_s'].apply(count_words)
			# Sort the DataFrame based on the 'word_count' column
			df_sorted = df.sort_values(by='word_count').reset_index(drop=True)
			# Drop the 'word_count' column if you don't need it in the final result
			df_sorted = df_sorted.drop(columns='word_count')

		return df_sorted
	

	def return_callback_func(self, affi_exist_in_hal=False, best_affil_dict={}):													
		# Return the callback function
		return affi_exist_in_hal, best_affil_dict
	

	def update_auths_fields_affil_from_hal(self, auth_idx, field_name, field_value):
		'''
		Based on whether affiliations exist in HAL, update the related fields in self.auths.
		'''
		def update_affil_id_field(auth_idx, field_name, field_value):
			# Save the results to self.auths.
			if self.auths[auth_idx][field_name] == '':
				self.auths[auth_idx][field_name] = str(field_value)
			else:
				# Check if the docid is in the list already.
				existing_string = self.auths[auth_idx][field_name]				
				if field_value not in existing_string.split(', '):
					self.auths[auth_idx][field_name] += ', {}'.format(field_value)		

		def update_list_field(auth_idx, field_name, field_value):
			self.auths[auth_idx][field_name].append(field_value)


		if field_name=='affil_id' or field_name=='affil_id_invalid':
			update_affil_id_field(auth_idx, field_name, field_value)
		else:
			update_list_field(auth_idx, field_name, field_value)		
	

	def pick_affiliation_from_search_results(self, search_result, affil_country='', affil_city='', affil_name='', aut='', parent_affil_id='', invalid_affil=False):
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

		# Check if a very short string yields too many results.
		# If yes, it might be a parse error due to "departement of law, just, and human"...
		if search_result[0] > 40 and len(affil_name.split())<=2:
			self.log_filter_steps_for_affil_unit(pd.DataFrame(), aut, affil_name, 'Suspected parse error. Please check if your affilation name is parsed correclty!')
			return self.return_callback_func()
		
		# If no match found: Return directly.
		if search_result[0] == 0:
			self.log_filter_steps_for_affil_unit(pd.DataFrame(), aut, affil_name, 'No match found!')
			return self.return_callback_func()

		
		# Create a dataframe to store all the found affliations.
		# Apply preprocessing on the "label_s" column.
		# Sort by the length of the affiliation name.
		affil_name, df_affli_found = self.prepare_df_affil_found(search_result, affil_name)
		self.log_filter_steps_for_affil_unit(df_affli_found, aut, affil_name, 'Original results after preprocessing')

		# If used for invalid affiliations.
		# Only check if it is an exact match.
		if invalid_affil:
			df_exact = df_affli_found[df_affli_found['label_s']==affil_name]
			self.log_filter_steps_for_affil_unit(df_exact, aut, affil_name, 'Invalid affiliation id search')

			if not df_exact.empty:
				return self.return_callback_func(affi_exist_in_hal=True, best_affil_dict=df_exact.iloc[0].to_dict())
			else:
				return self.return_callback_func()

		# Apply exact search. If there is only one exact match found, return this one.
		# If no exact match, or multiple exact match found, continue to filter the results.
		df_exact = self.find_exact_match(df_affli_found, affil_name, affil_city)
		self.log_filter_steps_for_affil_unit(df_exact, aut, affil_name, 'find_exact_match')
		# If there is only one exact match, take it.			
		if len(df_exact)==1:
			return self.return_callback_func(True, df_exact.iloc[0].to_dict())
		# If there are multiple exact matches (or zero), continue to filter.
		if len(df_exact)>1:
			df_affli_found = df_exact

		# If the current parent affil list is not empty: Filter based on parent affiliations.
		df_affli_found = self.filter_by_parent_affil(df_affli_found, parent_affil_id)
		self.log_filter_steps_for_affil_unit(df_affli_found, aut, affil_name, 'filter_by_parent_affil')											
		
		# Take maximal 30 records.
		n_max = 30
		if len(df_affli_found) > n_max:
			if len(affil_name.split())>2:
				df_affli_found = df_affli_found.iloc[:n_max, :]
			else:
				return self.return_callback_func()

		# Check if the input affil name is an acronym.
		# If yes, only consider the items that contain the [Acronym].
		df_affli_found = self.filter_by_acronym_pattern(df_affli_found, affil_name)
		self.log_filter_steps_for_affil_unit(df_affli_found, aut, affil_name, 'filter_by_acronym_pattern')

		# Remove the child affiliations in the list.
		df_affli_found = self.filter_by_university_group(df_affli_found)
		self.log_filter_steps_for_affil_unit(df_affli_found, aut, affil_name, 'filter_by_university_group')

		# If in the remaining affiliations, the author has published before: Select the first one.
		affi_exist_in_hal, best_affil_dict = self.filter_by_prev_publications(df_affli_found, aut)
		if affi_exist_in_hal:
			self.log_filter_steps_for_affil_unit(best_affil_dict, aut, affil_name, 'filter_by_prev_publications')				
			return self.return_callback_func(affi_exist_in_hal, best_affil_dict)
		
		# # Keep only the affiliations that starts with the required name:
		# df_without_accent = df_affli_found['label_s'].apply(unidecode).str.lower()
		# df_affli_found = df_affli_found[df_without_accent.str.startswith(
		# 	unidecode(affil_name[0].lower()))]
					
		# Remove the rows when affil_country exists but do not match.
		if affil_country:
			df_affli_found = self.filter_by_country(df_affli_found, affil_country)
			self.log_filter_steps_for_affil_unit(df_affli_found, aut, affil_name, 'filter_by_country')					
		
		# Remove the rows when affil_city exists but do not match.
		df_affli_found = self.filter_by_affil_city(df_affli_found, affil_city)
		self.log_filter_steps_for_affil_unit(df_affli_found, aut, affil_name, 'filter_by_affil_city')

		# Final evaluation:	
		# If less than three affiliation remains, go for a final evalution. Otherwise, return not found.
		if len(df_affli_found) <= 3 and not df_affli_found.empty:
			# Check the affiliation city is an exact match but not nan.
			if affil_city:
				df_affli_found = self.filter_by_affil_city(df_affli_found, affil_city, exact_filter=True)

			# Check if the search string appears in a parent affiliatin name:
			# Example: Institute of XXX [Universite Paris Saclay]
			if len(affil_name.split(' ')) > 1 and not df_affli_found.empty:
				affil_pattern = '.*?'.join(affil_name.split())
				# Define the pattern with affil_name
				pattern = fr'\[{affil_pattern}\]'
				# Remove the rows when the affiliation name is contained in [].
				mask = ~ df_affli_found['label_s'].str.contains(pattern, case=False)
				df_affli_found = df_affli_found[mask]

			# Check if the search string appears in a parent affiliatin name by looking at if it is like "XXX, Universite Paris Saclay"
			if len(affil_name.split(' ')) > 1 and not df_affli_found.empty:
				# Define the pattern with an optional comma before the first word
				affil_pattern = '.*?'.join(affil_name.split())
				pattern = fr',?\s*\[{affil_pattern}\]'
				mask = ~ df_affli_found['label_s'].str.contains(pattern, case=False)
				df_affli_found = df_affli_found[mask]

			if not df_affli_found.empty:
				affi_exist_in_hal = True
				best_affil_dict = df_affli_found.iloc[0].to_dict()
				
				# If there are still multiple choices, we prefer the affiliation with parents identical to existing affiliations.
				if 'parentName_s' in df_affli_found.columns:
					for i in range(len(df_affli_found)):
						if isinstance(df_affli_found.iloc[i]['parentName_s'], str) or isinstance(df_affli_found.iloc[i]['parentName_s'], list):
							best_affil_dict = df_affli_found.iloc[i].to_dict()
							break
								
				return self.return_callback_func(affi_exist_in_hal, best_affil_dict)
			else:
				self.log_filter_steps_for_affil_unit(df_affli_found, aut, affil_name, 'Enter the final evaluation but No match found.')
				return self.return_callback_func()
		else:
			self.log_filter_steps_for_affil_unit(df_affli_found, aut, affil_name, 'Exit before final choice: No match found.')
			return self.return_callback_func()	


	def prepare_df_affil_found(self, search_result, affil_name):
		''' ### Desrption
		Create a dataframe for the affiliation search results.
		Apply self.preprocess_affil_name on the label_s column, as well as affil_name.		
		'''
		# Create the dataframe
		for i in range(len(search_result[1])):
			if i == 0:
				df_affli_found = pd.DataFrame([search_result[1][i]])
			else:
				df_affli_found = pd.concat([df_affli_found, pd.DataFrame([search_result[1][i]])], ignore_index=True)

		# Preprocess df_affli_found['label_s'] and affil_name: Lower case and french words -> english words.
		df_affli_found['label_s_ori'] = df_affli_found['label_s']
		df_affli_found['label_s'] = df_affli_found['label_s'].apply(self.preprocess_affil_name)
		affil_name = self.preprocess_affil_name(affil_name)

		# Sort by name lengh.
		df_affli_found = self.sort_by_name_length(df=df_affli_found)
		
		return affil_name, df_affli_found

		

	def preprocess_affiliation_name(self, aut_affils, index, affil_country):
		'''
		This function preprocess a given affiliation name.
		Examples of preprocessing:
			- For french affiliations: Create a new affilation by replacing "university" to "universite"
			- Extract acronyms in the format of [XXX] and add it to the affiliation name explicitly.
	
		'''

		######### Subfunction definition

		# Defuzzy affiliation names.
		def defuzzy_affil_name(aut_affils, index):
			affil_name = aut_affils[index]
			output_string = self.preprocess_affil_name(affil_name)
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

			# If aut_affil contains acronym, extract the acronym.
			# Define a regular expression pattern to match "(XXX)"
			pattern = r'\((.*?)\)'
			# Use re.search to find the pattern in the string
			match = re.search(pattern, aut_affil)
			# Check if the pattern is found
			if match:
				# Extract the content inside the parentheses
				affi_acronym = match.group(1)
				
				# Add the acronym to the end of the string
				if 'fondation' not in aut_affil: # Exception: If "fondation edf..."
					# Remove acronym from the original string.
					aut_affil = aut_affil.replace(' ({})'.format(affi_acronym), '')
					aut_affil += ', ' + affi_acronym

			replacements = [
				('university', 'universite'),
				('technology', 'technologie'),
				('technological', 'technologie')
				# Add more replacement pairs as needed
			]
			if affil_country == 'fr' or affil_country == '' or affil_country == 'be':
				if 'university' in aut_affil.lower():
					index_university = aut_affil.lower().find('university')
					idx_begin = aut_affil.lower().find(',', 0, index_university)
					idx_end = aut_affil.lower().find(',', index_university)

					# Replace the english words with french ones.
					new_aut_affil = aut_affil.lower()[idx_begin+1:idx_end].strip() if idx_end != -1 else aut_affil.lower()[idx_begin+1:].strip()
					for old_str, new_str in replacements:
						new_aut_affil = new_aut_affil.replace(old_str, new_str)
					
					aut_affil += ', ' + new_aut_affil

			aut_affils[index] = aut_affil					

			return aut_affils[index]
		
		##############

		# Start of the main operation.
		aut_affil = aut_affils[index]
		if not isinstance(aut_affil, str):
			return aut_affil
		
		# Remove the ';' at the end of the affiliation. 
		if aut_affil.endswith('; '):
			aut_affil = aut_affil.rstrip('; ')

		# Defuzzy affili_unit.
		aut_affil = defuzzy_affil_name(aut_affils, index)
	
		# Enrich the affiliation name.
		aut_affil = enrich_affil_name(aut_affils, index, affil_country)

		return aut_affil



class GenerateXMLTree(AutomateHal):
	def __init__(self, doc, auths=None, doc_data=None, debug_affiliation_search=False, debug_hal_upload=False, mode='search query', stamps=[], allow_create_new_affiliation=False):
		super().__init__(mode=mode, debug_affiliation_search=debug_affiliation_search, debug_hal_upload=debug_hal_upload, stamps=stamps, 
				   auths=auths, doc_data=doc_data, allow_create_new_affiliation=allow_create_new_affiliation)

		self.doc_data_for_tei = {
			'title': '', 
			'pub_name': '', 
			'issue': '', 
			'volume': '', 
			'page_range': '', 
			'cover_date': '', 
			'kw_list': '',
			'doctype': None, 
			'funders': None, 
			'journalId': None, 
			'issn': None, 
			'domain': None, 
			'language': None, 
			'abstract': None, 
			'isbn': None
		}

		self.xml_tree = None # The produced xml tree.
		self.xmi_tree_root = None # Root of the tree.
		self.xml_path = '' # Path of the generated tree.
		self.biblFullPath = 'tei:text/tei:body/tei:listBibl/tei:biblFull' # Path in the xml tree related to biblfull section.
		self.biblStructPath = self.biblFullPath+'/tei:sourceDesc/tei:biblStruct' # Path in the xml tree related to biblstructure section.
		self.xml_tree_name_space = {'tei':'http://www.tei-c.org/ns/1.0'} # Name space of the xml-tree
		self.new_affiliation_idx = 0 # Index for the manually added affiliations.
		self.new_affiliation = [] # List of all the existing manually added affiliations.


		self.prepare_data_for_tei_tree(doc)
		

	# Sub-functions supporting parsing affiliations.
	def add_affiliation_by_affil_id(self, eAuth, affil_id):
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
			if self.debug_affiliation_search:
				try:
					search_result = self.reqHalRef(ref_name='structure', 
								search_query='(docid:{})'.format(affil_id), 
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


	def add_new_affiliations(self, eListOrg, eAuth):
		aut = self.current_auth
		# Get all the affiliation
		aut_affils = aut['affil']
		# Get the ones that need to be added manually.
		aut_affils_need_treatment = aut['affil_not_found_in_hal']
		# Loop over each affil:
		for aut_affil in aut_affils_need_treatment:
			# Get the affiliation country.
			idx_country = -1
			for i, element in enumerate(aut_affils):
				if element == aut_affil:
					idx_country = i
					break
			# If no affiliation country, skip.
			if idx_country == -1:
				continue
			else:
				affil_country = aut['affil_country'][idx_country]

				if affil_country:
					if affil_country.lower() != 'fr' and affil_country != '' and affil_country.lower() != 'france':
						self.add_new_affiliation(aut_affil, eListOrg=eListOrg, eAuth=eAuth) 	



	def add_new_affiliation(self, aut_affil, eListOrg, eAuth):
		'''
		This is a subfunction that create a new affiliation. First it will check if the affiliation already exists as a local structure.
		If yes, it will directly refer to that. If no, it will create a new one.

		Parameters:
		- aut_affil (str): The affiliation of the author.

		'''

		# Dealing with special characters:
		aut_affil = re.sub(r'&amp;', '& ', aut_affil)

		# If it is the first new affiliation, create directly.
		if self.new_affiliation_idx == 0:
			self.new_affiliation_idx += 1 # Update the index.
			# Create the new organization.
			eBackOrg_i = ET.SubElement(eListOrg, 'org')
			eBackOrg_i.set('type', 'institution')
			eBackOrg_i.set('xml:id', 'localStruct-' + str(self.new_affiliation_idx))
			eBackOrg_i_name = ET.SubElement(eBackOrg_i, 'orgName')
			eBackOrg_i_name.text = aut_affil
			self.new_affliation.append(aut_affil)
			# Make reference to the created affliation.
			eAffiliation_manual = ET.SubElement(eAuth, 'affiliation')				
			eAffiliation_manual.set('ref', 'localStruct-' + str(self.new_affiliation_idx))
		else: # If it is not the first new affiliation, search if it has been created by us before.
			try:
				idx = self.new_affliation.index(aut_affil)
				# If it has been created, make reference to it.
				eAffiliation_manual = ET.SubElement(eAuth, 'affiliation')				
				eAffiliation_manual.set('ref', 'localStruct-' + str(idx+1))	
			except ValueError: # If not created, create a new one.
				# Update the index.
				self.new_affiliation_idx += 1
				# Create the new organization.
				eBackOrg_i = ET.SubElement(eListOrg, 'org')
				eBackOrg_i.set('type', 'institution')
				eBackOrg_i.set('xml:id', 'localStruct-' + str(self.new_affiliation_idx))
				eBackOrg_i_name = ET.SubElement(eBackOrg_i, 'orgName')
				eBackOrg_i_name.text = aut_affil
				self.new_affliation.append(aut_affil)	
				# Make reference to the created affliation.
				eAffiliation_manual = ET.SubElement(eAuth, 'affiliation')				
				eAffiliation_manual.set('ref', 'localStruct-' + str(self.new_affiliation_idx))



	def prepare_data_for_tei_tree(self, doc):
		# Prepare input data for the TEI-xml tree.

		doc_data_for_tei = self.doc_data_for_tei
		
		if self.mode == 'search_query':			
			doc_data_for_tei['title'] = doc['title']
			doc_data_for_tei['pub_name'] = doc["publicationName"]
			doc_data_for_tei['issue'] = doc['issueIdentifier'] 
			doc_data_for_tei['volume'] = doc['volume']
			doc_data_for_tei['page_range'] = doc['pageRange']
			doc_data_for_tei['cover_date'] = doc['coverDate']
			if isinstance(doc['authkeywords'], str):
				doc_data_for_tei['kw_list'] = doc['authkeywords'].split(" | ")
			else:
				doc_data_for_tei['kw_list'] = ''
			abstract = doc['description']
		elif self.mode =='csv':
			doc_data_for_tei['title'] = doc['Title']
			doc_data_for_tei['pub_name'] = doc["Source title"]
			doc_data_for_tei['issue'] = doc['Issue'] 
			doc_data_for_tei['volume'] = doc['Volume']
			if doc['Page start'] and doc['Page end'] :
				doc_data_for_tei['page_range'] = doc['Page start']+ "-"+doc['Page end']
			else : 
				doc_data_for_tei['page_range'] = ""
			doc_data_for_tei['cover_date'] = doc['Year']
			if isinstance(doc['authkeywords'], str):
				doc_data_for_tei['kw_list'] = doc['Author Keywords'].split(" ; ")
			else:
				doc_data_for_tei['kw_list'] = ''
			abstract = doc['Abstract']
		else: 
			ValueError('Mode value error!')

		doc_data_for_tei['doctype'] = self.doc_data['doctype']
		if isinstance(abstract, str):
			doc_data_for_tei['abstract'] = False if abstract.startswith('[No abstr') else abstract[: abstract.find('©') - 1]
		else:
			doc_data_for_tei['abstract'] = False

		# Match language
		if isinstance(self.doc_data['language'], str):
			scopus_lang = self.doc_data['language'].split(";")[0]
		else:
			scopus_lang = 'und'
		with open("./data/matchLanguage_scopus2hal.json") as fh:
			matchlang = json.load(fh)
			doc_data_for_tei["language"] = matchlang.get(scopus_lang, "und")


		self.get_funding_for_tei_tree(doc)
		self.get_journal_info_for_tei_tree(doc)	


	def get_funding_for_tei_tree(self, doc):
		"""
		Prepares data in the format expected by TEI (Text Encoding Initiative).

		Parameters:
		- doc (dict): Document information.

		Returns:
		dict: Data in the TEI format.
		"""

		# Read the existing data strcutre for tei.
		doc_data_for_tei = self.doc_data_for_tei

		# Extract funding data
		doc_data_for_tei['funders'] = []
		if self.mode == 'search_query':
			if doc['fund_acr']:
				if not doc['fund_no']:
					doc_data_for_tei['funders'].append(doc['fund_acr'])
				else:
					doc_data_for_tei['funders'].append('Funder: {}, Grant NO: {}'.format(doc['fund_acr'], doc['fund_no']))
		elif self.mode =='csv':
			if doc['Funding Details']:
				doc_data_for_tei['funders'].append(doc['Funding Details'])
		else: 
			ValueError('Mode value error!')

		if self.doc_data['funding_text'] and isinstance(self.doc_data['funding_text'], str):
			doc_data_for_tei['funders'].append(self.doc_data['funding_text'])


	def search_domain_from_journal_id(self, doc):
		'''
		Search the domain of a journal based on its journal id.
		'''
		# Read the existing data strcutre for tei.
		doc_data_for_tei = self.doc_data_for_tei

		# api_hal = HaLAPISupports()

		# Find HAL domain
		doc_data_for_tei['domain'] = None 

		# Query HAL with journalId to retrieve domain
		if doc_data_for_tei['journalId']:
			prefix = 'http://api.archives-ouvertes.fr/search/?rows=0'
			suffix = '&facet=true&facet.field=domainAllCode_s&facet.sort=count&facet.limit=2'
			req = requests.get(prefix + '&q=journalId_i:' + doc_data_for_tei['journalId'] + suffix)
			try:
				req = req.json()
				if req["response"]["numFound"] > 9:  # Retrieve domain from journal if there are more than 9 occurrences
					doc_data_for_tei['domain'] = req['facet_counts']['facet_fields']['domainAllCode_s'][0]
			except:
				print('\t Warning: HAL API did not work for retrieving domain with journal')
				self.add_an_entry_to_log_file(self.log_file, 'Warning: HAL API did not work for retrieving domain with journal')
				pass

		if not doc_data_for_tei['domain']:
			doc_data_for_tei['domain'] = 'spi' # Default: Engineering / physics
			print('\t Warning: Domain not found: Defaulted to "sdi". Please verify its relevance.')
			self.add_an_entry_to_log_file(self.log_file, 'Warning: Domain not found: Defaulted to "sdi". Please verify its relevance.')


	def search_journal_in_hal(self, doc):
		'''
		Search if a journal exists in HAL by its issn.
		'''

		# Read the existing data strcutre for tei.
		doc_data_for_tei = self.doc_data_for_tei

		# Get HAL journalId and ISSN
		doc_data_for_tei['journalId'], doc_data_for_tei['issn'] = False, False
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
			reqIssn = self.reqHalRef(ref_name='journal', 
						search_query='(text:({}) valid_s:"VALID")'.format(issn))

			# prefix = 'http://api.archives-ouvertes.fr/ref/journal/?'
			# suffix = '&fl=docid,valid_s,label_s'
			# req = requests.get(prefix + 'q=issn_s:' + issn + suffix)
			# req = req.json()
			# reqIssn = [req['response']['numFound'], req['response']['docs']]
			
			# If journals found, get the first journalId
			if reqIssn[0] > 0:
				doc_data_for_tei['journalId'] = str(reqIssn[1][0]['docid'])

			# If no journal found, store the ISSN
			if reqIssn[0] == 0:
				doc_data_for_tei['issn'] = issn

		# If multiple issn: 
		if doc_issn and not isinstance(doc_issn, str):
			pass


	def get_journal_info_for_tei_tree(self, doc):
		"""
		Prepares data in the format expected by TEI (Text Encoding Initiative).

		Parameters:
		- doc (dict): Document information.

		Returns:
		dict: Data in the TEI format.
		"""

		# Read the existing data strcutre for tei.
		doc_data_for_tei = self.doc_data_for_tei

		# Set the filed of issn, and search for journal id by issn.
		self.search_journal_in_hal(doc)

		# Set the field of domain by searching hal.
		self.search_domain_from_journal_id(doc)
		
		# Extract ISBN
		if self.doc_data['isbn']:
			doc_data_for_tei['isbn'] = ''

			if isinstance(self.doc_data['isbn'], list) or isinstance(self.doc_data['isbn'], tuple):
				doc_data_for_tei["isbn"] = self.doc_data['isbn'][0]
				
			if isinstance(self.doc_data['isbn'], str):
				doc_data_for_tei["isbn"] = self.doc_data['isbn']

			if ';' in doc_data_for_tei["isbn"]:
				# If multiple ISBNs, take the first one only
				doc_data_for_tei["isbn"] = doc_data_for_tei["isbn"][:doc_data_for_tei["isbn"].index(';')]		
		else:
			doc_data_for_tei['isbn'] = ''


	def export_tei_tree(self):
		''' ### Description
		Export the xml tree to a file.
		'''
		# Load data.
		doc_id = self.doc_data['eid']
		tree = self.xml_tree
		root = tree.getroot()

		# Add name space and header.
		ET.register_namespace('', "http://www.tei-c.org/ns/1.0")
		root.attrib["xmlns:hal"] = "http://hal.archives-ouvertes.fr/"

		base_path = './data/outputs/TEI/'
		# Check if the directory exists
		if not os.path.exists(base_path):
			# If it doesn't exist, create the directory
			os.makedirs(base_path)
		
		# Generate the name of the tree.
		xml_path = base_path + doc_id + ".xml"
		
		# Export the tree.
		ET.indent(tree, space="\t", level=0)
		tree.write(xml_path,
				xml_declaration=True,
				encoding="utf-8",
				short_empty_elements=False)
		
		self.xml_path = xml_path


	def generate_tree(self):
		'''
		This function generates the TEI XML tree for the given paper. It will directly operate on self.xml_tei_tree.
		'''

		# Load the sample tree and get the root node.
		try:
			self.xml_tree = ET.parse('./data/tei_modele.xml')			
		except:
			raise ValueError('Error: XML file not found!')

		self.xmi_tree_root = self.xml_tree.getroot()

		# Register name space.
		ET.register_namespace('',"http://www.tei-c.org/ns/1.0")
		
		# Generate different part of the tree: 
		# - Identify the related part.
		# - Remove the contents in the sample.
		# - Check in self.doc_data_for_tei to add the content.
		
		# Generate the funding part.		
		self.parse_funder()
		
		# Add stamps if there are any.
		self.parse_stamp()

		# Add title.
		self.parse_title()
		self.parse_authors()
		self.parse_bib_info()


	def parse_bib_info(self):
		''' Parse bib info like journal, page, keywords, etc.
		'''

		# Load parameters.
		root = self.xmi_tree_root
		biblFullPath = self.biblFullPath
		ns = self.xml_tree_name_space
		
		biblStructPath = self.biblStructPath

		## ADD SourceDesc / bibliStruct / monogr : isbn
		eMonogr = root.find(biblStructPath+'/tei:monogr', ns)
		idx_item = 0

		## ne pas coller l'ISBN si c'est un doctype COMM sinon cela créée une erreur (2021-01)
		if self.doc_data_for_tei['isbn']  and not self.doc_data_for_tei['doctype'] == 'COMM':  
			eIsbn = ET.Element('idno', {'type':'isbn'})
			eIsbn.text = self.doc_data_for_tei["isbn"]
			eMonogr.insert(idx_item, eIsbn)
			idx_item += 1

		## ADD SourceDesc / bibliStruct / monogr : issn
		# if journal is in Hal
		if self.doc_data_for_tei['journalId'] :
			eHalJid = ET.Element('idno', {'type':'halJournalId'})
			eHalJid.text = self.doc_data_for_tei['journalId']
			eHalJid.tail = '\n'+'\t'*8
			eMonogr.insert(idx_item, eHalJid)
			idx_item += 1

		# if journal not in hal : paste issn
		if not self.doc_data_for_tei['doctype'] == 'COMM':
			if not self.doc_data_for_tei['journalId'] and self.doc_data_for_tei["issn"] :
				eIdIssn = ET.Element('idno', {'type':'issn'})
				eIdIssn.text = self.doc_data_for_tei['issn']
				eIdIssn.tail = '\n'+'\t'*8
				eMonogr.insert(idx_item, eIdIssn)
				idx_item += 1

		# if journal not in hal and doctype is ART then paste journal title
		if not self.doc_data_for_tei['journalId'] and self.doc_data_for_tei['doctype'] == "ART" : 
			eTitleJ = ET.Element('title', {'level':'j'})
			eTitleJ.text =  self.doc_data_for_tei['pub_name']
			eTitleJ.tail = '\n'+'\t'*8
			eMonogr.insert(idx_item, eTitleJ)
			idx_item += 1

		# if it is COUV or OUV paste book title
		if self.doc_data_for_tei['doctype'] == "COUV" or self.doc_data_for_tei['doctype'] == "OUV" :
			eTitleOuv = ET.Element('title', {'level':'m'})
			eTitleOuv.text = self.doc_data_for_tei['pub_name']
			eTitleOuv.tail = '\n'+'\t'*8
			eMonogr.insert(idx_item, eTitleOuv)
			idx_item += 1

		## ADD SourceDesc / bibliStruct / monogr / meeting : meeting
		if self.doc_data_for_tei['doctype'] == 'COMM' : 
			#conf title
			eMeeting = ET.Element('meeting')
			eMonogr.insert(idx_item, eMeeting)
			eTitle = ET.SubElement(eMeeting, 'title')
			eTitle.text = self.doc_data['confname']
					
			#meeting date
			eDate = ET.SubElement(eMeeting, 'date', {'type':'start'}) 
			eDate.text = self.doc_data['confdate']
					
			#settlement
			eSettlement = ET.SubElement(eMeeting, 'settlement')
			eSettlement.text = self.doc_data['conflocation'] if self.doc_data['conflocation'] else 'unknown'

			#country
			eSettlement = ET.SubElement(eMeeting, 'country', {'key':'fr'})

		#___ CHANGE  sourceDesc / monogr / imprint :  vol, issue, page, pubyear, publisher
		eImprint = root.find(biblStructPath+'/tei:monogr/tei:imprint', ns)
		for e in list(eImprint):
			if e.get('unit') == 'issue': 
				if self.doc_data_for_tei['issue']: 
					if isinstance(self.doc_data_for_tei['issue'], str):
						e.text = self.doc_data_for_tei['issue'] 
					else:
						if not math.isnan(self.doc_data_for_tei['issue']):
							e.text = str(int(self.doc_data_for_tei['issue']))
			if e.get('unit') == 'volume' : 
				if self.doc_data_for_tei['volume']: 
					if isinstance(self.doc_data_for_tei['volume'], str):
						e.text = self.doc_data_for_tei['volume'] 
					else:
						if not math.isnan(self.doc_data_for_tei['volume']):
							str(int(self.doc_data_for_tei['volume']))
			if e.get('unit') == 'pp' : 
				page_range = self.doc_data_for_tei['page_range']
				if page_range and isinstance(page_range, str): e.text = page_range
			cover_date = self.doc_data_for_tei['cover_date'] 
			if e.tag.endswith('date') and isinstance(cover_date, str): e.text = cover_date
			if e.tag.endswith('publisher') : e.text = self.doc_data_for_tei['publisher']

		#_____ADD  sourceDesc / biblStruct : DOI & Pubmed
		eBiblStruct = root.find(biblStructPath, ns)
		doi = self.doc_data['doi']
		if doi and not self.debug_hal_upload: 
			eDoi = ET.SubElement(eBiblStruct, 'idno', {'type':'doi'} )
			eDoi.text = doi

		#___CHANGE  profileDesc / langUsage / language
		eLanguage = root.find(biblFullPath+'/tei:profileDesc/tei:langUsage/tei:language', ns)
		eLanguage.attrib['ident'] = self.doc_data_for_tei["language"]

		#___CHANGE  profileDesc / textClass / keywords/ term
		eKeywords = root.find(biblFullPath+'/tei:profileDesc/tei:textClass/tei:keywords', ns)
		eKeywords.clear()
		eKeywords.set('scheme', 'author')
		keywords_list = self.doc_data_for_tei['kw_list']
		for i in range(0, len(keywords_list)):
			eTerm_i = ET.SubElement(eKeywords, 'term')
			eTerm_i.set('xml:lang', self.doc_data_for_tei['language'])
			eTerm_i.text = keywords_list[i]

		#___CHANGE  profileDesc / textClass / classCode : hal domaine & hal doctype
		eTextClass = root.find(biblFullPath+'/tei:profileDesc/tei:textClass', ns)
		for e in list(eTextClass):
			if e.tag.endswith('classCode') : 
				if e.attrib['scheme'] == 'halDomain': e.attrib['n'] = self.doc_data_for_tei['domain']
				if e.attrib['scheme'] == 'halTypology': e.attrib['n'] = self.doc_data_for_tei['doctype']

		#___CHANGE  profileDesc / abstract 
		eAbstract = root.find(biblFullPath+'/tei:profileDesc/tei:abstract', ns)
		eAbstract.text = self.doc_data_for_tei['abstract']


	# Define private sub-function to parse differet part of the xml tree.
	def parse_funder(self):
		''' 
		Parse funder element. 
		'''

		# Load parameters.
		root = self.xmi_tree_root
		biblFullPath = self.biblFullPath
		ns = self.xml_tree_name_space

		#___CHANGE titlesStmt : suppr and add funder	
		#clear titlesStmt elements ( boz redundant info)
		eTitleStmt = root.find(biblFullPath+'/tei:titleStmt', ns)
		eTitleStmt.clear()

		# if applicable add funders	
		if len(self.doc_data_for_tei['funders']) > 0 : 
			for fund in self.doc_data_for_tei['funders']: 
				eFunder = ET.SubElement(eTitleStmt, 'funder')
				eFunder.text = fund.replace('\n', ' ').replace('\r', ' ')


	def parse_stamp(self):
		''' Parse stamp element.
		'''

		# Load parameters.
		root = self.xmi_tree_root
		biblFullPath = self.biblFullPath
		ns = self.xml_tree_name_space
		stamps = self.stamps

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

	
	def parse_title(self):
		''' Parse title element.
		'''

		# Load parameters.
		root = self.xmi_tree_root
		biblFullPath = self.biblFullPath
		ns = self.xml_tree_name_space

		#___CHANGE  sourceDesc / title
		eAnalytic = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic', ns)
		eTitle = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic/tei:title', ns)
		eAnalytic.remove(eTitle) 
				
		eTitle = ET.Element('title', {'xml:lang': self.doc_data_for_tei["language"] })

		if not self.debug_hal_upload:
			eTitle.text = self.doc_data_for_tei['title']
		else:
			eTitle.text = self.doc_data_for_tei['title'] + ' - test'
		
		eAnalytic.insert(0, eTitle)


	def parse_author(self):
		'''
		Add author information for one author.
		'''
		
		# Load parameters.
		root = self.xmi_tree_root
		biblFullPath = self.biblFullPath
		ns = self.xml_tree_name_space

		# Get the current author that needs processing.
		aut = self.current_auth
		eAnalytic = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic', ns)

		# Set author role: Author or Corresponding author.
		role  = 'aut' if not aut['corresp'] else 'crp' #correspond ou non
		# Find the section and add the information.		
		eAuth = ET.SubElement(eAnalytic, 'author', {'role':role}) 
		
		# Add personal information: Name, Surname, Email, Orcid, and others.
		ePers = ET.SubElement(eAuth, 'persName')

		# Name
		eForename = ET.SubElement(ePers, 'forename', {'type':"first"})
		if not aut['forename'] : eForename.text = aut['initial']
		else : eForename.text = aut['forename']

		# Surname
		eSurname = ET.SubElement(ePers, 'surname')
		eSurname.text = aut['surname']	

		# if applicable  add email 
		if aut['mail'] :
			eMail = ET.SubElement(eAuth, 'email')
			eMail.text = aut['mail'] 

		# if applicable add orcid
		if aut['orcid'] : 
			orcid = ET.SubElement(eAuth,'idno', {'type':'https://orcid.org/'})
			orcid.text = aut['orcid']
		
		# if applicable add idHAL
		if aut['idHAL'] : 
			idHAL = ET.SubElement(eAuth,'idno', {'type':'idhal'})
			idHAL.text = aut['idHAL']

		# Add affiliations.
		# Add the valid affiliations by their id hals directly.
		if aut['affil_id']:
			# Get the valid affiliation ids.
			affil_ids = aut['affil_id'].split(', ')			
			# Create an 'affiliation' element for each id
			for affil_id in affil_ids:
				self.add_affiliation_by_affil_id(eAuth=eAuth, affil_id=affil_id)

		return eAuth
		
		

	def parse_authors(self):
		'''
		Add the author information for a list of authors.
		'''

		# Load parameters.
		root = self.xmi_tree_root
		biblFullPath = self.biblFullPath
		biblStructPath = self.biblStructPath
		ns = self.xml_tree_name_space		

		eAnalytic = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic', ns)
		#___CHANGE  sourceDesc / biblStruct / analytics / authors			
		author = root.find(biblStructPath+'/tei:analytic/tei:author', ns)
		eAnalytic.remove(author)

		# Locate the back section of the xml file.
		eListOrg = root.find('tei:text/tei:back/tei:listOrg', ns)
		eOrg = root.find('tei:text/tei:back/tei:listOrg/tei:org', ns)
		eListOrg.remove(eOrg)	
	
		# Start processing author by author:			

		# Reset new affiliation index and list.
		self.new_affiliation_idx = 0
		self.new_affliation = []

		# For each author, write author information to the xml tree.
		for aut in self.auths: 
			# Add valid information.
			self.current_auth = aut
			eAuth = self.parse_author()

			# If allow to create new affiliations, add them.
			if self.allow_create_new_affiliation:
				self.add_new_affiliations(eListOrg, eAuth)
						

		# In the end, if no new affiliations are added, remove the 'eBack' element.
		if not self.allow_create_new_affiliation or self.new_affiliation_idx == 0:
			eBack_Parent = root.find('tei:text', ns)
			eBack = root.find('tei:text/tei:back', ns)
			eBack_Parent.remove(eBack)


# Testing here:
if __name__ == '__main__':
	# Define search query.
	# search_query = 'AU-ID(55659850100) OR AU-ID(55348807500) OR AU-ID(7102745133) AND PUBYEAR > 2017 AND PUBYEAR < 2025 AND AFFIL (centralesupelec)'
	# search_query = 'AU-ID(55348807500) AND PUBYEAR > 2016 AND PUBYEAR < 2025' # Zhiguo Zeng
	# search_query = 'AU-ID(7005289082) AND PUBYEAR > 2000  AND PUBYEAR < 2025 AND (AFFIL (centralesupelec) OR AFFIL (Supelec))' # Enrico Zio
	# search_query = 'AU-ID(7005289082) AND PUBYEAR > 2000  AND PUBYEAR < 2025' # Enrico Zio
	# search_query = 'AU-ID(6602469780) AND PUBYEAR > 2000 AND PUBYEAR < 2025 AND AFFIL (centralesupelec)' # Bernard Yannou
	# search_query = 'AU-ID(56609542700) AND PUBYEAR > 2000 AND PUBYEAR < 2025 AND (AFFIL (centralesupelec) OR AFFIL (Supelec))' # Yanfu Li
	# search_query = 'AU-ID(14049106600) AND PUBYEAR > 2000  AND PUBYEAR < 2025 AND (AFFIL (centralesupelec) OR AFFIL (Supelec))' # Nicola Pedroni
	# search_query = 'AU-ID(7102745133) AND PUBYEAR > 2000 AND PUBYEAR < 2025' # Anne Barros
	# search_query = 'EID (2-s2.0-85107087996)'
	search_query = 'AU-ID(7801563868) AND PUBYEAR > 2000 AND PUBYEAR < 2025' # Nabil Anwer

	results = ScopusSearch(search_query, view='COMPLETE', refresh=True)
	df_result = pd.DataFrame(results.results)
	# df_result.to_csv('./data/outputs/scopus_search_results.csv', index=False)

	# df_result = pd.read_csv('./data/outputs/scopus_search_results_lgi.csv')
	# df_result.fillna(value='', inplace=True)

	# Define paths for the input data.
	perso_data_path = './data/inputs/path_and_perso_data.json'
	author_db_path = './data/inputs/auth_db.csv'
	# affil_db_path = './data/inputs/affiliation_db.csv'
	affil_db_path = ''

	# Define the stamps you want to add to the paper.
	# If you don't want to add stamp: stamps = []
	# stamps = ['LGI-SR', 'CHAIRE-RRSC']
	stamps = [] # Add your stamps here

	# Load the scopus dataset.
	auto_hal = AutomateHal(perso_data_path=perso_data_path, affil_db_path=affil_db_path,
				author_db_path=author_db_path, stamps=stamps)

	# For debugging: Only upload the first rowRange records.
	# Comment this line if you want to upload all the records.
	row_range=[0, 140]

	auto_hal.debug_affiliation_search = True
	auto_hal.debug_hal_upload = True
	auto_hal.allow_create_new_affiliation = False

	auto_hal.process_papers(df_result=df_result, row_range=row_range)