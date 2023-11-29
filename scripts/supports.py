import json, csv, io, requests


def loadBibliography(path):
	t = open(path, newline='', encoding='utf-8-sig')
	return csv.DictReader(t)


def extractAuthors(authors, authId):
	''' from table Extract surname and initial foremane and authid
	ex de liste de nom : 
	Taher Y., Haque R., AlShaer M., v. d. Heuvel W.J., Zeitouni K., Araujo R., Hacid M.-S., 
	il peut mm avoir des des virgules pour le nom d'un auteur doi.org/10.1002/rcm.8244
	'''
	## CODE PROBLEM WITH this data :   Scott R.T., Jr., de Ziegler D. : PRODUCE ERROR boz it sees 3 auths

	authors_cut = authors.split(',')
	authId_cut = authId[:-1].split(';')
	if not len(authors_cut) == len(authId_cut) : 
		print("pb : nb auth et nb authId ne correspondent pas ")
		quit()
	
	auths = []
	for auth_idx, auth in enumerate(authors_cut):
		
		if '.' not in auth : #escape les groupements d'auteur
			print(f"\tauteur échappé\t{auth}")
			continue
		
		auth = auth.strip() # le Nom P.
		elem = auth.split() 
		#le surname est le dernier élément qui ne finit pas par un point
		for i in reversed(range( len(elem))) : 
			if not elem[i].endswith('.'):
				idx = auth.index(elem[i]) + len(elem[i])
				surname = auth[: idx]
				initial = auth[idx:].strip()
				#print(surname,'\t', intial )
				break
				
		if len(surname) == 0 or len(initial) < 1 : 
			print('!! pb id name \t',auth)
			quit()			
		
		auths.append(
			{'surname': surname, 
			'initial': initial, 
			'forename': False,
			'scopusId': authId_cut[auth_idx],
			'orcid': False,
			'mail': False, 
			'corresp': False,
			'affil': '',
			'affil_id': ''
			})
		
	return auths

def extractCorrespEmail(auths, corresp):
	for item in auths : 
		for addr in corresp.split('\n')  : # Address Corresp can contains many lines, many emails
			if addr.startswith(item["surname"]) : 
				mail = [elem for elem in addr.split(" ") if "@" in elem]
				if mail : 
					item['mail'] = mail[0]
					item['corresp'] = True
					break
						
	return auths


def extractRawAffil(auths, rawAffils):	
	'''extract raw affil from scopus table'''
	#il faut partir du début, aller jusqu'au 2e nom, et cela délimite la 1er affil
	
	nbAuth = len(auths)
	i = 1
	while i <= nbAuth :
		preFullName = auths[i-1]['surname']+", "+auths[i-1]['initial']

		if i == nbAuth :
			aff = rawAffils[ rawAffils.index(preFullName) : ]    
		else :
			postFullName = auths[i]['surname']+", "+auths[i]['initial']
			aff = rawAffils[ rawAffils.index(preFullName) : rawAffils.index(postFullName)]

		#exclude name in affil
		nameLen = len(preFullName+', ')
		# affils.append(aff[nameLen: ])
		auths[i-1]['affil'] = aff[nameLen: ]
		i+=1       

	return auths


def loadTables_and_createOutpus(perso_data_path, author_db_path):
	# load local data : path and personal data
	global local_data
	with open(perso_data_path) as fh : 
		local_data = json.load(fh)
	
	global apikey, insttoken
	apikey = local_data.get("perso_scopusApikey")
	insttoken = local_data.get("perso_scopusInstToken")
	print("scopus api key loaded") if apikey else print("no scopus key loaded")

	# load valid authors db
	global AuthDB # a dictionnary with "NAME F."" as key for authors
	with open(author_db_path, 'r', encoding="utf-8") as auth_fh:
		reader = csv.DictReader(auth_fh)
		AuthDB = {row['key']: row for row in reader}

	# csv output for biblio analysed
	global docs_table
	docs_table = open('./data/outputs/doc_analysed.csv', 'w', newline='', encoding="utf8")
	global writeDoc
	writeDoc = csv.writer(docs_table, delimiter =',')
	writeDoc.writerow(['eid', 'doi', 'doctype', 'state', 'treat_info', 'hal_match', 'halUris', 'emails'])


def matchDocType(doctype):
	doctype_scopus2hal = {'Article': 'ART', 'Article in Press' : 'ART', 'Review':'ART', 'Business Article':'ART', "Data Paper":"ART", 'Conference Paper':'COMM',\
'Conference Review':'COMM', 'Book':'OUV', 'Book Chapter':'COUV'}
	
	if doctype in doctype_scopus2hal.keys() :
		return doctype_scopus2hal[doctype]
	else :
		return False


def addRow(docId, state, treat_info='', hal_match='', uris='', emails=''):
	print(f"added to csv: state = {state}")
	writeDoc.writerow([docId['eid'], docId['doi'], docId['doctype'],
	state, treat_info, hal_match, ', '.join(uris), emails ])
	

def reqWithIds(doi):
	"""recherche dans HAL si le DOI ou PUBMEDID est déjà présent """	
	idInHal = [0,[]] #nb of item, list of uris
	
	reqId = reqHal('doiId_id:', doi )
	idInHal[0] = reqId[0]	
	for i in reqId[1] : 
		idInHal[1].append(i['uri_s'])

	return idInHal


def reqWithTitle(titles):
	"""recherche dans HAL si une notice avec le mm titre existe """
	
	titleInHal = [0,[]] 

	reqTitle = reqHal('title_t:\"', titles+ '\"')
	for i in reqTitle[1] : 
		titleInHal[1].append(i['uri_s'])
	
	#test avec le 2nd titre
	if len(titles[1]) > 3: 
		reqTitle_bis = reqHal('title_t:\"', titles[1]+ '\"')
		reqTitle[0] += reqTitle_bis[0]
		
		for i in reqTitle_bis[1] : 
			titleInHal[1].append(i['uri_s'])
		
	titleInHal[0] = reqTitle[0] 
	return titleInHal


def reqHal(field, value = ""):
	prefix= 'https://api.archives-ouvertes.fr/search/?' #halId_s
	suffix = "&fl=uri_s,title_s&wt=json"
	req = prefix + '&q='+ field + value+ suffix
	found = False
	while not found : 
		req = requests.get(req)
		try : 
			fromHal = req.json()
			found = True
		except : 
			pass
	
	num = fromHal['response'].get('numFound')
	docs = fromHal['response'].get('docs', [])
	return [num, docs]


def retrieveScopusAuths(auths):
	if not apikey : 
		return auths
	""" from scopus get forename and orcid
	memo : si on pousse un orcid qui est attaché à un idHAL alors l'idHAL s'ajoute automatiquement """
	
	for item in auths :

		if item["forename"] and item["orcid"] : continue
		
		try:
			req = reqScopus('author?author_id='+ item['scopusId']+'&field=surname,given-name,orcid')
			try : 
				# a faire evoluer pour intégrer les alias eg 57216794169
				req = req['author-retrieval-response'][0]
			except : 
				pass

			#get forname
			if not item["forename"] and req.get("preferred-name"): 
				item["forename"] = req["preferred-name"].get('given-name')
			
			#get orcid 
			if not item["orcid"] and req.get("coredata") : 
				item['orcid'] = req['coredata'].get("orcid")
		except:
			pass

	return auths


def reqScopus(suffix):
	prefix = "https://api.elsevier.com/content/"	
	req = requests.get(prefix+suffix, 
		headers={'Accept':'application/json',
		'X-ELS-APIKey': apikey
		})	
	req = req.json()
	if req.get("service-error") : 
		print(f"\n\n!!probleme API scopus : \n\n{req}")
		quit()
	return req


def enrichWithAuthDB(auths):
	""" complete auth data w local file 'validUvsqAuth' """
	for item in auths:
		key = item['surname']+' '+item['initial']
		if key in AuthDB: 
			fields = ['forename', 'affil_id'] ##on ne prend pas le mail enregistré sur notre base local
			# if nothing from scopus but present in local db then add value
			for f in fields : 
				# if nothing is present then we enrich w uvsq auth db
				if not item[f] : item[f] = AuthDB[key][f]
	return auths


def getTitles(inScopus):
	"""extract titles from scopus table"""
	cutTitle = inScopus.split('[')
	if len(cutTitle) > 1:
		cutindex = inScopus.index('[')
		titleOne = inScopus[0: cutindex].rstrip()
		titleTwo = inScopus[cutindex+1: -1].rstrip()
	else:
		titleOne = inScopus
		titleTwo = ""
	return [titleOne, titleTwo]



def close_files(): 	
	docs_table.close()