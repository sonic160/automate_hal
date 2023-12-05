
This repository aims at searching and uploading selected papers from Scopus to HAL automatically. The script also allows you to define and add stamps of collections to your uploaded files, which could be a helpful feature if you have to manage some collections in HAL. If the co-authors of the papers you uploaded have their orcid id in the Socpus results, or if you provided their HAL-id in a supporting file `data/inputs/auth_db.csv`, you uploaded papers will be included automatically to their profiles in HAL.

More specifically, it has two modes of use:
- `search_query` mode: In this mode, you just need to define a search query in Scopus, and the script will automatically search the papers in Scopus, extract key information related to a paper, export them into a TEI-xml file required by HAL-api, and upload the papers in HAL to create the corresponding notices. 
- `csv` mode: In this mode, you need to search Scopus database manually and save the results in a csv file. Then, the script will iterate over all the papers in a csv file and upload them to HAL.

# Table of contents

- [How to use](#item-2)
- [Organization of the repository](#item-3)
- [Background knowledge and references](#item-4)
- [Similar work and why do we need this project](#item-5)
- [Credits](#item-6)

# How to use <a id="item-2"></a>

- Clone the repository or download the source code.
- Install the necessary dependencies from the terminal: `pip install -r requirements.txt`
- Prepare your Scopus API key and institution token (optional) if you plan to use the script outside your institutional ip address. For details, refer to [here](documents/demo_search_scopus_from_api_and_upload.md#item-Scopus-api).
- If you want to use the `search_query` mode, follow the steps defined in `scripts/test_search_query.py`. You can have a step-by-step tutorial [here](documents/demo_search_scopus_from_api_and_upload.md).
- If you want to use the `csv` mode, follow the steps defined in `scripts/test_csv.py`. You can have a step-by-step tutorial [here](documents/demo_upload_from_a_csv_file.md).

# Organization of the repository <a id="item-3"></a>

The repository is organized as follows (we only list the main parts related to the functionality of the program):

```
├── data
|   ├── input
|       ├── auth_db.csv
|       ├── path_and_perso_data.json
|       ├── scopus_results.csv
|   ├── output
|       ├── TEI
|       ├── log.csv
|   ├── tei_modele.xml
|   ├── matchLanguage_scopus2hal.json
├── scripts
|   ├── test_search_scopus_and_upload.py
|   ├── test_upload_from_csv.py
|   ├── supports.py
├── requirements.txt
└── README.md

```

Below you can find a detailed explaination for each folder:
- data/: This folder contains the data used for the program, including the inputs data that the user needs to provide, and the output data generated by the program.
    - input/: The user needs to provde them.
        - `auth_db.csv`: This csv file provides information regarding authors. It is used to map the author names in the paper to the author ids in HAL. It is not required. If there is no information in this Table, the program can still run, but the author names will not be mapped to their idHAL. This csv file should contain the following keys:
            - key: The key used to relate the author to the Scopus result. It is defined as the last name of the author + Initial of the first name. E.g., Zeng Z. __Attention: Don't forget the point after the initials.__
            - forename: The first name of the author.
            - affil_id: The ids of affiliations in HAL. Need to be given as strings. If multiple, seperate by comma, e.g., 'XXX, XXX'. __Attention: Don't forget the quatation mark ' '.__
            - idHAL: The idHAL of the author.
            - __Note: If an author might have different ways of spelling first names/initials, create multiple records in this csv file.__
        - `path_and_perso_data.json`: This json file provides some credentials needed for uploading the papers, including:
            - "perso_login_hal" : HAL Login
	        - "perso_mdp_hal" : HAL password	        
        - `scopus_results.csv`: The search results from Scopus. Please select "export to csv" in Scopus, and save the results to this file. Please export all the fields from Scopus. It is only needed for the `csv` mode.        
    - output/: This folder contains files that will be generated by the script.
        - TEI/: This folder contains the TEI-xml files generated for each paper in scopus_results.csv.
        - log.csv: System log.
        - scopus_results.csv: If you choose the `search_query` mode, this file will be generated, containing the results from Scopus using your search query.
    - data/matchLanguage_scopus2hal.json, data/tei_modele.xml are two auxilary data that are needed in the processing. You don't need to change them.
- scripts/: contains the python scripts used to process the data
    - `test_search_scopus_and_upload.py`: The main script for the `search_query` mode.
    - `test_upload_from_csv.py`: The main script for the `csv` mode.
    - `supports.py`: Supporting functions. All the needed function is embedded in a class named automate_hal. The class is used in the main script to realize the automated uploading of papers.
- README.md: this file summarizes this repository and how to use it.
- requirements.txt: the python packages required to run the scripts. You can install them by running `pip install -r requirements.txt` in the terminal.

# Background knowledge <a id="item-4"></a>

This repository is built based on the APIs from HAL and Scopus. If you would like to have some basic knowledge about how to use these APIs, please refer to the following links:
- Official document for [HAL API](https://api.archives-ouvertes.fr/docs)
- Get the ids of authors and affiliations already existed in HAL from [aureHAL](https://aurehal.archives-ouvertes.fr/)
- Official document for [Scopus API](https://dev.elsevier.com/guides/Scopus%20API%20Guide_V1_20230907.pdf)
- For the format of the xml-tei file required for HAL API, you can refer to [this tutorial](https://aramis.resinfo.org/lib/exe/fetch.php?media=ateliers:aramis-hal-v3-le-format-tei_25_02_2015.pdf). You can find examples for each category of paper from this [github repository](https://github.com/CCSDForge/HAL/tree/master/Sword).

# Similar work and why do we need this project ? <a id="item-5"></a>

There some other efforts to make HAL easier for researchers although still a looooong way to go... For a summary of these similar works, you can refer to this [web collection.](https://wiki.ccsd.cnrs.fr/wikis/hal/index.php/Outils_et_services_d%C3%A9velopp%C3%A9s_localement_pour_am%C3%A9liorer_ou_faciliter_l%27utilisation_de_HAL). 

Among them, the following tools are particularly relervant to this project:

- [HAL imports](https://github.com/ml4rrieu/HAL_imports): It is a open-source repository in Github that automatically upload papers to HAL from a Scopus search results. Our project is built on this one, but we made the following improvements:
    - We add the `search_query` mode.    
    - We re-design the code to be in object-oriented programming, and use pybliometric to improve the interaction with HAL.
    - We change the way of searching for affiliation of each author.
    - We change the code of generating the xml-tei file, so that the affiliations of each author are added, and new affiations can be created in HAL if it does not exist in HAL already.
    - We added the option to upload the papers to HAL with user-defined stamps.
    - The original code is designed for USQV. We made more generic so that it is easier to be implemented elsewhere.
    - We fix some bugs.
    
    
- [X2HAL](https://x2hal.inria.fr/): This is a website run by Inria that allows you to upload xml-tei or bibtext files of your reference, and it will create the notice in HAL for you. However, you have to generate xml-tei file by yourself, which is not an easy task. Also, you need to upload the files in this website manually.
- [OverHAL](https://halur1.univ-rennes1.fr/OverHAL.php): modified version of the CouvertureHAL program, adapted by Olivier Troccaz and Laurent Jonchère (University of Rennes 1). OverHAL allows you to compare HAL and publication lists (WoS, Scopus, Zotero, Pubmed, etc.). Objectives: identify publications missing from HAL, create a TEI file adapted to X2HAL, generate emails requesting post-prints from the corresponding authors. It is very similar to what we want to do, but again it is a web-based service.

## Particular reason for me

There is a common problem for all these existing tools: Altought they are all great, but all the documents are provided in French >_< I know HAL is mainly used in France but I believe there are many foreign researchers working in France but do not yet master well french (like myself). I believe this project could make their life much easier.

# Credits <a id="item-5"></a>

In this repository, we
- reuses parts of the codes from the github repository [HAL_imports](https://anvilproject.org/guides/content/creating-links).
- use the open-source python package pybliometrics ([Github link](https://github.com/pybliometrics-dev/pybliometrics/tree/master) and [PyPI link](https://pypi.org/project/pybliometrics/)) to interact with Scopus API.

We greately appreciate the efforts from the oriinal authors.
