from pybliometrics.scopus import AuthorRetrieval, AbstractRetrieval, ScopusSearch
import csv, json, requests, os, re, math, copy
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from unidecode  import unidecode 
import pycountry as pycountry


class AutomateHal:
	'''
	Base class for the HAL Automator. 

	Attributes:
    
	Methods:

	'''

	def __init__(self, perso_data_path='', author_db_path='', stamps=[], mode='search_query'):
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
		self.AuthDB = '' # A dictionary that stores user-defined data to refine the search results.
		self.mode = mode # Mode of operation: search_query or csv
		self.ite = -1 # Index of the current iterature.
		self.stamps = stamps # List of stamps to be used in the Tei files.
		self.debug_mode = False # Whether to run in debug mode. If True, not verifying if existed in HAL.
		self.upload_to_hal = True # Whether to upload the documet reference to the HAL repository.
		self.output_path = './data/outputs/'
		self.report_entry = {
			'eid': '',
			'doi': '',			
			'doctype': '',
			'title': '', 
			'state': '',
			'hal_matches': '',
			'email_corr_auth': ''
		}
		self.report = []
		self.log = []

		# Check mode:
		if mode != 'search_query' and mode != 'csv':
			raise ValueError('mode must be either "search_query" or "csv".')

		# Load the personal credentials and author database.
		self.load_data_and_initialize(perso_data_path, author_db_path)


	def load_data_and_initialize(self, perso_data_path, author_db_path):
		"""
		Loads local data, HAL credentials, and valid authors database.
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

		# Check if the output directory exists
		if not os.path.exists(self.output_path):
			# If it doesn't exist, create it
			os.makedirs(self.output_path)


	def save_to_report(self, file_name='report.csv'):
		log_file = '{}{}'.format(self.output_path, file_name)
		log_info = self.status_report

		# Check if the file exists
		file_exists = True
		try:
			with open(log_file, 'r') as file:
				reader = csv.reader(file)
				file_exists = bool(next(reader, None))
		except FileNotFoundError:
			file_exists = False

		# Write the log entry to the CSV file	
		with open(log_file, 'w', newline='', encoding="utf8") as file:
			writer = csv.writer(file, delimiter=',')
			
			fieldnames = list(log_info.keys())
			writer = csv.DictWriter(file, fieldnames=fieldnames)

			# Write header if the file is empty
			if not file_exists:
				writer.writeheader()

			# Write log entry
			writer.writerow(log_info)


	def save_to_log(self, file_name='log.csv'):
		log_file = '{}{}'.format(self.output_path, file_name)


	
	def process_one_paper(self, doc):
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

		# Create a papaer information treator.
		paper_info_treator = PaperInformationTreater(mode=self.mode, AuthDB=self.AuthDB)

		# Get the docids and document type.
		paper_info_treator.extract_docids_and_doc_type(doc)

		# Verify if the paper is already in HAL.
		if not self.debug_mode and paper_info_treator.verify_if_existed_in_hal(doc):
			self.log.append('End of operation: The paper is already in HAL.')
			self.report_entry['state'] = 'Already in HAL'
			return
		
		# Extract & enrich authors data
		ab = paper_info_treator.extract_author_infomation()

		# from auth_db.csv get the author's affiliation structure_id in HAL.
		paper_info_treator.enrich_with_AuthDB()
		
		# Complement the paper data based on the Abstract Retrival API.
		paper_info_treator.extract_complementary_paper_information(ab)

		# Search the affiliations in HAL and get the ids.
		paper_info_treator.extract_author_affiliation_in_hal()

		print('End of operation: The paper has been processed.')
	
		for auth in paper_info_treator.auths:
			print('Author name: {}'.format(auth['surname']))
			print('affiliations: {}'.format(auth['affil']))
			print('found ids: {}'.format(auth['affil_id']))
			print('invalid ids: {}'.format(auth['affil_id_invalid']))
			print('affil_exist_in_hal: {}'.format(auth['affil_exist_in_hal']))
			print('affil_not_found_in_hal: {}'.format(auth['affil_not_found_in_hal']))
			print('\n')


class PaperInformationTreater(AutomateHal):
	'''
	This Subclass is in charge of treating and complementing information of each paper.

	'''
	def __init__(self, mode='search_query', AuthDB=[]):
		self.auths = [] # A dictionary to store author information.
		self.AuthDB = AuthDB
		self.docid = '' # Document ID: A dictionary in format of {'eid': '', 'doi': '', 'doctype': ''}
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
		self.mode = mode
	

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
					'affil_id_invalid': '',
					'affil_exist_in_hal': [],
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
	

	def pick_affiliation_in_hal(self, search_result, affil_country='', affil_city='', affil_name='', aut='', parent_affil_id='', invalid_affil=False):
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

		########################
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
					search_query = 'structId_i:{}&fq=auth_t:"{} {}"'.format(df_affli_found.iloc[i]['docid'], aut['forename'], aut['surname'])
					num, _ = HaLAPISupports().reqHal(search_query=search_query)
					flag.append(num>0)
				if any(flag):
					df_affli_found = df_affli_found[flag]
					
					affi_exist_in_hal = True
					best_affil_dict = df_affli_found.iloc[0].to_dict()

			return affi_exist_in_hal, best_affil_dict
		

		def return_callback_func(affi_exist_in_hal=False, best_affil_dict={}, affil_name=''):													
			# Return the callback function
			return affi_exist_in_hal, best_affil_dict
		

		###########################################
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
			if invalid_affil:
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
		
		##############

		# Start of the main operation.

		# Remove the ';' at the end of the affiliation.
		aut_affil = aut_affils[index] 
		if aut_affil.endswith('; '):
			aut_affil = aut_affil.rstrip('; ')

		# Defuzzy affili_unit.
		aut_affil = defuzzy_affil_name(aut_affils, index)
	
		# Enrich the affiliation name.
		aut_affil = enrich_affil_name(aut_affils, index, affil_country)

		return aut_affil



	def extract_author_affiliation_in_hal(self):
		'''
		This function check for each author in self.auths, and check if its affiliation exists in HAL and is an valid affiliation.
		There are three possibilities:
			- If yes, add the docid from HAL to `self.auths['affil_id']` and put the corresponding element in `self.auths['exist_in_hal']` to be `['Valid']`
			- If existed in Hal, but not valid, add the docid from HAL to self.auths['affil_id_invalid'] and put the corresponding element in self.auths['exist_in_hal'] to be ['Invalid']
			- If not existed in Hal, add it to self.auths['affil_not_in_hal'] and put the corresponding element in self.auths['exist_in_hal'] to be ['No']

		'''

		############ Sub function definition.
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
		
		# Generate affiliation list.
		def generate_affil_list(aut_affil):
			# Seperate the different terms by ",".
			aut_affil_list = aut_affil.split(', ')

			# Rearrange the order of the parts.
			keywords_to_move_last = ['university', 'universite']
			for keyword in keywords_to_move_last:
				for part in aut_affil_list:
					if keyword in part.lower():
						aut_affil_list.remove(part)
						aut_affil_list.append(part)
			
			# In case "department of law, order, and XXX", this will generate too many items.
			# If too many sub items, only take the first one.
			if len(aut_affil_list)>=6:
				aut_affil_list = aut_affil_list[-1:]

			return aut_affil_list


		############# 
		# Start of the main function.

		# Import HAL API supports.
		api_hal = HaLAPISupports()

		# Start searching the affiliation in HAL.
		auths = self.auths
		for auth_idx, aut in enumerate(auths):
			# If there are affiliations defined in AuthDB, skip this author.
			# Only extract for those not defined in AuthDB.
			if not aut['affil_id']:
				# Extract the affiliation name from the search results.
				aut_affils = copy.deepcopy(aut['affil'])
				if aut_affils[0] == None:
					aut_affils = ['Unknown']
				affil_countries = aut['affil_country']
				affli_cities = aut['affil_city']
				author_name = {'forename': aut['forename'], 'surname': aut['surname']}

				for affil_idx in range(len(aut_affils)):												
					# Get country and city of the affiliation.
					affil_country = generate_abbreviation(affil_countries[affil_idx])
					affil_city = affli_cities[affil_idx]
					
					# Preprocess each auth affiliation.
					aut_affil = self.preprocess_affiliation_name(aut_affils, affil_idx, affil_country)									

					# Generate affiliation list.
					aut_affil_list = generate_affil_list(aut_affil)

					# Initially set to be not existed.
					affi_exist_in_hal = False				
					parent_affil_id = [] # Store all the parent affiliations. Use to exclude child affilation with the same name.

					# Start to search from the right-most unit (largest):
					for affil_unit in reversed(aut_affil_list):						            											
						affi_unit_exist_in_hal = False

						# Search for the valid affliations in HAL.
						try:
							search_result = api_hal.reqHalRef(ref_name='structure', 
										search_query='(text:({}) valid_s:"VALID")'.format(affil_unit), 
										return_field='&fl=docid,label_s,address_s,country_s,parentName_s,parentDocid_i,parentValid_s&wt=json&rows=100')
						except:
							search_result = [0]
							pass

						# Get the best-matched one and add it to the xml-tree.
						affi_unit_exist_in_hal, affil_dict = self.pick_affiliation_in_hal(search_result, affil_country, affil_city, aut=author_name, affil_name=affil_unit, parent_affil_id=parent_affil_id)
						# If found, add to the xml tree.
						if affi_unit_exist_in_hal:
							affi_exist_in_hal = True
							# Update teh parent_affil_id for future search.
							parent_affil_id.append(affil_dict['docid'])
							if not affil_country:
								affil_country = affil_dict['country_s']

							# Save the results to self.auths.
							if self.auths[auth_idx]['affil_id'] == '':
								self.auths[auth_idx]['affil_id'] = str(affil_dict['docid'])
							else:
								self.auths[auth_idx]['affil_id'] += ', {}'.format(affil_dict['docid'])						
					
					# If the affiliation does not exist in HAL, add the affiliation manually.
					# If the affiliation is France, do not create new affiliation as HAL is used for evaluating affiliations, 
					# so there is a stricker rule regarding creating affiliations.
					if not affi_exist_in_hal and affil_country:
						if affil_country.lower() != 'fr' and affil_country != '':
							# Before adding new affiliation, check if the affiliation exists in HAL but not VALID
							# Search for the valid affliations in HAL.
							try:
								# Here we don't require that the affiliation in HAL is valid.
								aut_affil = aut['affil'][affil_idx]
								search_result = api_hal.reqHalRef(ref_name='structure', 
											search_query='(text:"{}")'.format(aut_affil), 
											return_field='&fl=docid,label_s,address_s,country_s,parentName_s,parentDocid_i,parentValid_s&wt=json&rows=100')
							except:
								search_result = [0]
								pass
							affi_exist_in_hal, affil_dict = self.pick_affiliation_in_hal(search_result, affil_name=aut_affil, invalid_affil=True)
							
							# If exist in HAL but not valid.
							if affi_exist_in_hal:
								if self.auths[auth_idx]['affil_id_invalid']:
									self.auths[auth_idx]['affil_id_invalid'] = str(affil_dict['docid'])
								else:
									self.auths[auth_idx]['affil_id_invalid'] += ', {}'.format(affil_dict['docid'])
								continue
						
					self.auths[auth_idx]['affil_exist_in_hal'].append(affi_exist_in_hal)
					if not affi_exist_in_hal:
						self.auths[auth_idx]['affil_not_found_in_hal'].append(aut_affil)

				
													

	def extract_docids_and_doc_type(self, doc):
		'''
		Extract the document ID and document type from the input data.
		'''
		# Get the ids of each paper.
		if self.mode == 'search_query':
			doc_type_supported, doc_type = self.is_doctype_supported(doc['aggregationType'])
			if not doc_type_supported:
				raise ValueError('Document type not supported! doc_type={}'.format(doc_type))
			self.docid = {'eid': doc['eid'], 'doi': doc['doi'], 'doctype': doc_type}
		elif self.mode =='csv':
			doc_type_supported, doc_type = self.is_doctype_supported(doc['Document Type'])
			if not doc_type_supported:
				raise('Document type not supported! doc_type={}'.format(doc_type))
			self.docid = {'eid': doc['EID'], 'doi': doc['DOI'], 'doctype': doc_type}
		else: 
			raise ValueError('Please choose teh correct mode! Has to be "search_query" or "csv".')


	def is_doctype_supported(self, doctype):
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

		api_hal = HaLAPISupports()

		# Verify if the publication existed in HAL.
		# First check by doi:
		idInHal = api_hal.reqWithIds(self.docid['doi'])	
		
		if idInHal[0] > 0:
			print(f"already in HAL")
			self.report_entry['state'] = 'already in hal'
			self.report_entry['hal_matches'] = idInHal[1]

			return True
		else: # Then, check with title
			if self.mode == 'search_query':
				titleInHal = api_hal.reqWithTitle(doc['title'])
			elif self.mode == 'csv':
				titleInHal = api_hal.reqWithTitle(doc['Title'])
			else:
				ValueError("'mode' must be either 'search_query' or 'csv'!")
			if titleInHal[0] > 0:
				print(f"already in HAL")
				self.report_entry['state'] = 'already in hal'
				self.report_entry['hal_matches'] = idInHal[1]

				return True
			
		return False


	
class HaLAPISupports:
	def __init__(self):
		self.hal_api_entry_url = 'https://api.archives-ouvertes.fr/'


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

		prefix = self.hal_api_entry_url + search_category + '/?&q='

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
			Example: [2, ['uri1', 'uri2']]
		"""

		idInHal = [0, []]  # Number of items, list of URIs

		# Check if doi is empty:
		if doi == '':
			return idInHal

		# Perform a HAL request to find documents by DOI
		suffix='&fl=uri_s,title_s&wt=json'
		reqId = self.reqHal(field='doiId_id', value=doi, suffix=suffix)
		idInHal[0] = reqId[0]

		# Append HAL URIs to the result list
		for i in reqId[1]:
			idInHal[1].append(i['uri_s'])

		return idInHal


	def reqWithTitle(self, title):
		"""
		Searches in HAL to check if a record with the same title exists.

		Parameters:
		- titles (list): List of titles to search for.

		Returns:
		list: List containing the number of items found and a list of HAL URIs.
			Example: [2, ['uri1', 'uri2']]
		"""
		titleInHal = [0, []]

		title = re.sub(r'&amp;', ' ', title)
		title = re.sub(r'[^a-zA-Z0-9 ]', '', title)		

		# Perform a HAL request to find documents by title
		search_query = 'title_t:(', title + ')'
		suffix='&fl=uri_s,title_s&wt=json'
		reqTitle = self.reqHal(search_query=search_query, suffix=suffix)

		# Append HAL URIs to the result list
		for i in reqTitle[1]:
			titleInHal[1].append(i['uri_s'])

		titleInHal[0] = reqTitle[0]

		# # Test with the second title
		
		return titleInHal
	

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
    search_query = 'EID (2-s2.0-85178664213)'

    results = ScopusSearch(search_query, view='COMPLETE', refresh=True)
    df_result = pd.DataFrame(results.results)
    # df_result.to_csv('./data/outputs/scopus_search_results.csv', index=False)

    # df_result = pd.read_csv('./data/outputs/scopus_search_results.csv')

    df_result.fillna(value='', inplace=True)

    # Define paths for the input data.
    perso_data_path = './data/inputs/path_and_perso_data.json'
    author_db_path = './data/inputs/auth_db.csv'

    # Define the stamps you want to add to the paper.
    # If you don't want to add stamp: stamps = []
    stamps = ['LGI-SR', 'CHAIRE-RRSC']
    # stamps = [] # Add your stamps here

    # Load the scopus dataset.
    auto_hal = AutomateHal(perso_data_path, author_db_path, stamps)

    # For debugging: Only upload the first rowRange records.
    # Comment this line if you want to upload all the records.
    # rowRange=[2, 200]
    auto_hal.debug_mode = True
    auto_hal.upload_to_hal = False

    # Address the record in the scopus dataset one by one.
    n = len(df_result)
    for i, doc in df_result.iterrows():
        # if 'rowRange' in locals():
            # # For debugging: Limit to first rowRange records.
            # if i < min(rowRange) : continue
            # elif i > max(rowRange) : break
        
        # Update the iteration index.
        auto_hal.ite = i
        print('{}/{} iterations: {}'.format(i+1, n, doc['eid']))
        # Process the corresponding paper.
        try:
            auto_hal.process_one_paper(doc)
        except Exception as error:
            print('Error processing paper: {}. Log saved.'.format(doc['eid']))
            print('Error is: {}'.format(error))