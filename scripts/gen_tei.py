import json, requests
import xml.etree.ElementTree as ET
from supports import addRow
import requests


def prepareData(doc, auths, docType):
	''' structure data has expected by the TEI'''	
	dataTei = {}
	dataTei['doctype'] = docType 

	#_______ extract funding data	
	dataTei['funders'] = []	
	if doc['Funding Details']: dataTei['funders'].append(doc['Funding Details'])
	temp = [doc['Funding Text '+str(i)] for i in range(1,10) if doc.get('Funding Text '+str(i))]
	dataTei['funders'].extend(temp)


	#_______ get hal journalId
	dataTei['journalId'], dataTei['issn'] = False, False

	if doc['ISSN']:
		#si moins de 8 carac on rempli de 0
		zeroMissed = 8 - len(doc['ISSN'])
		issn = ("0"* zeroMissed + doc['ISSN']) if zeroMissed > 0 else doc['ISSN']
		issn = issn[0:4]+'-'+issn[4:]

		prefix = 'http://api.archives-ouvertes.fr/ref/journal/?'
		suffix = '&fl=docid,valid_s,label_s'
		req = requests.get(prefix +'q=issn_s:'+issn+suffix)
		req = req.json()
		reqIssn = [req['response']['numFound'], req['response']['docs']]
		
		# if journals finded get the first journalId
		if reqIssn[0] > 0 : 
			dataTei['journalId'] = str(reqIssn[1][0]['docid'])

		## if no journal fouded
		if reqIssn[0] == 0 : 
			dataTei['issn'] = issn

	#_______ find hal domain
	dataTei['domain'] = 'phys.qphy'

	# with journal issn
	if dataTei['journalId'] : 
		prefix = 'http://api.archives-ouvertes.fr/search/?rows=0'
		suffix = '&facet=true&facet.field=domainAllCode_s&facet.sort=count&facet.limit=2'
		req = requests.get( prefix + '&q=journalId_i:'+dataTei['journalId']+suffix )
		try:
			req = req.json()
			if req["response"]["numFound"] > 9 : # retrieve domain from journal if there is more than 9 occurences
				dataTei['domain'] = req['facet_counts']['facet_fields']['domainAllCode_s'][0]
		except : 
			print('\tHAL API not worked for retrieve domain with journal')
			pass
		
	if not dataTei['domain'] : 
		dataTei['domain'] = 'sdv'
		print('\t!! domain non trouve : sdv renseigne par default : verifier la pertinence')

	#_______ Match language
	scopus_lang = doc['Language of Original Document'].split(";")
	scopus_lang = scopus_lang[0]

	with open("./data/matchLanguage_scopus2hal.json") as fh : 
		matchlang = json.load(fh)

		if not matchlang.get(scopus_lang) : 
			dataTei["language"] = "und"
			print("!! language non trouve : *und* a ete indique")
		else : 
			dataTei["language"] = matchlang[scopus_lang]

	#_______ Abstract
	abstract = doc['Abstract']
	dataTei['abstract'] = False if abstract.startswith('[No abstr') else abstract[: abstract.find('©')-1]

	#________ extract ISBN
	if ';' in doc['ISBN'] :
		# si plusieurs isbn prendre le premier seulement
		dataTei["isbn"]  =  doc['ISBN'][:doc['ISBN'].index(';')] 
	else : 
		dataTei["isbn"] = doc['ISBN'] 
	
	return dataTei


def produceTeiTree(doc, auths, dataTei, titles) :	
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
			eFunder.tail='\n' + '\t'*6

	#___CHANGE editionStmt : suppr
	eBiblFull = root.find(biblFullPath, ns)
	eEdition = root.find(biblFullPath+'/tei:editionStmt', ns)
	eBiblFull.remove(eEdition)

	#___CHANGE seriesStmt
	eSeriesStmt = root.find(biblFullPath+'/tei:seriesStmt', ns)
	eSeriesStmt.clear()
	eSeriesIdno_1 = ET.SubElement(eSeriesStmt, 'idno')
	eSeriesIdno_1.set('n', 'CHAIRE-RRSC')
	eSeriesIdno_1.set('type', 'stamp')
	eSeriesIdno_2 = ET.SubElement(eSeriesStmt, 'idno')
	eSeriesIdno_2.set('n', 'LGI-SR')
	eSeriesIdno_2.set('type', 'stamp')

	# eSeriesIdno = root.find(biblFullPath+'/tei:seriesStmt/tei:idno', ns)
	# eSeriesIdno.set('n', 'LGI-SR')

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

	for aut in auths : 
		role  = 'aut' if not aut['corresp'] else 'crp' #correspond ou non
		eAuth = ET.SubElement(eAnalytic, 'author', {'role':role}) 
		eAuth.tail='\n\n' + '\t'*7
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

		#if applicable add structId
		if aut['affil_id'] : 
			# eAffiliation = ET.SubElement(eAuth, 'affiliation ')
			# eAffiliation.set('ref', '#struct-'+str(aut['affil_id']))
			
			# Split the comma-separated ids into a list
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


def exportTei(docId, docTei, auths) : 
	tree = docTei 
	root = tree.getroot()
	ET.register_namespace('',"http://www.tei-c.org/ns/1.0")
	root.attrib["xmlns:hal"] = "http://hal.archives-ouvertes.fr/"
	
	xml_path = './data/outputs/TEI/'+docId['eid']+".xml"
	tree.write(xml_path,
	xml_declaration=True,
	encoding="utf-8", 
	short_empty_elements=False)

	
	emails = [elem["mail"] for elem in auths if elem["mail"] ]

	addRow(docId, "TEI generated", '', '', '', ", ".join(emails) )

	return xml_path


def hal_upload(filepath):
	''' script python pour importer des notices via SWORD
		SWORD HAL documentation : https://api.archives-ouvertes.fr/docs/sword
	'''
	url = 'https://api.archives-ouvertes.fr/sword/hal'
	head = {
	'Packaging': 'http://purl.org/net/sword-types/AOfr',
   	'Content-Type': 'text/xml',
   	'X-Allow-Completion' :None
	}
	# si pdf  : Content-Type : application/zip 

	xmlfh = open(filepath, 'r', encoding='utf-8')
	xmlcontent = xmlfh.read() #le xml doit être lu, sinon temps d'import très long
	xmlcontent = xmlcontent.encode('UTF-8')

	if len(xmlcontent) < 10 : 
		print('file not loaded')
		quit()

	response = requests.post(url, headers = head, data = xmlcontent, auth=('ZZeng', 'ZENG12345678'))
	print(response.text)

	xmlfh.close()
