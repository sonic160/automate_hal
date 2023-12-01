
# Introduction of this repository

This repository aims at uploading selected papers from Scopus to HAL automatically. More specifically, it iterates over all the papers in a csv file, which is output from s search in Scopus, extract key information related to a paper, export them into a TEI-xml file required by HAL-api, and upload the papers in HAL to create the corresponding notices. 

This repository benefits a lot from the work in the github repository [HAL_imports](https://anvilproject.org/guides/content/creating-links), and we greately appreciate the efforts from the authors.

# Organization of the repository

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
|   ├── hal_upload_from_scopus.py
|   ├── supports.py
├── requirement.txt
└── README.md

```

Below you can find a detailed explaination for each folder:
- data/: This folder contains the data used for the program, including the inputs data that the user needs to provide, and the output data generated by the program.
    - input/: The user needs to provde them.
        - `auth_db.csv`: This csv file provides information regarding authors. It is used to map the author names in the paper to the author ids in HAL. It is not required. If there is no information in this Table, the program can still run, but the author names will not be mapped to their idHAL. This csv file should contain the following keys:
            - key: The key used to relate the author to the Scopus result. It is defined as the last name of the author + Initial of the first name. E.g., Zeng Z. __Attention: Don't forget the point after the initials.__
            - forename: The first name of the author (by default Scopus only gives initials).
            - affil_id: The ids of affiliations in HAL. Need to be given as strings. If multiple, seperate by comma, e.g., 'XXX, XXX'. __Attention: Don't forget the quatation mark ' '.__
            - idHAL: The idHAL of the author.
        - `path_and_perso_data.json`: This json file provides some credentials needed for uploading the papers, including:
            - "perso_login_hal" : HAL Login
	        - "perso_mdp_hal" : HAL password
	        - "perso_scopusApikey" : Scopus API key, not required, but recommended if you want more precise information about authors and their affiliations. 
            - "perso_scopusInstToken": Scopus InstToken. It allows you to access scopus API outside your institution ip. It is not required, but recommended if you want more precise information about authors and their affiliations.
        - `scopus_results.csv`: The search results from Scopus. Please select "export to csv" in Scopus, and save the results to this file. Please export all the fields from Scopus.        
    - output/: 
        - TEI/: This folder contains the TEI-xml files generated for each paper in scopus_results.csv.
        - log.csv: System log.
    - data/matchLanguage_scopus2hal.json, data/tei_modele.xml are two auxilary data that are needed in the processing. You don't need to change them.
- scripts/: contains the python scripts used to process the data
    - `hal_upload_from_scopus.py`: The main script that iterates over the csv file and calls the other scripts to process each paper, create the TEI-xml files, and upload the papers to HAL.
    - `supports.py`: Supporting functions. All the needed function is embedded in a class named automate_hal. The class is used in the main script to realize the automated uploading of papers.
- README.md: this file summarizes this repository and how to use it.
- requirements.txt: the python packages required to run the scripts. You can install them by running `pip install -r requirements.txt` or `conda install --file requirements.txt` in the terminal, depending on which environment you are using.

# How to use

1. Clone the repository or download it as a zip file.
2. Prepare the input data:
    - Go to [Scopus](https://www.scopus.com/) and run your search there. Please select "export to csv" in Scopus, and save the results to `data/scopus_results.csv`. Please export all the fields from Scopus.
    - Prepare the `data/auth_db.csv` file. If you don't have information about the authors in your database, you can skip this step. Otherwise, you need to provide the information in this file. The format of this file should be the following:

    ![](/screenshots/demo_auth_db.png)

    - Notes:
        - The key used to relate the author to the Scopus result is defined as the last name of the author + Initial of the first name. E.g., Zeng Z.
        - The affil_id and idHAL will be used to map the author names and affiliations in HAL. You can search them from [aurehal.](https://aurehal.archives-ouvertes.fr/)
    
    - Prepare the `data/path_and_perso_data.json` file. This file contains the credentials needed for uploading the papers, including:
        - "perso_login_hal" : HAL Login
        - "perso_mdp_hal" : HAL password
        - "perso_scopusApikey" : Scopus API key, not required. You can create your own API key from [Elsevier Developer Portal](https://dev.elsevier.com/).

    ![](/screenshots/demo_api_scopus.png)
        

3. Run `hal_upload_from_scopus.py`. You can edit the stamps you want to give to the papers you uploaded. To do this, you just need to modify the values of stamps. Please inputs the correct stamp name. You can find the stamp names for the collections that you are the administrator. To do so, you need to go to the HAL interface, and click on the "My Collection" button on the top right corner. Then, you can find the stamp name as the following.

![](/screenshots/find_stamp_name.png)

__Please note that the type of stamp should be a list, i.e., even though you have only one stamp, you need to put it like `stamp=['XXX']`.__

4. You can monitor the progress of the uploading process in the terminal. The log is saved in the `data/log.csv` file. For each paper in `scopus_results.csv`, the program will:
    - Check if this paper already exists in HAL. If yes, the program will skip this paper, and you will see `already in hal` in the log.
    - If not existed, the program will generate a TEI-xml file for this paper. If succeeded, you will see `TEI generated` in the log.
    - Then, the TEI-xml file will be uploaded to HAL. If succeeded, you will see `HAL upload: Success` in the log.

# A quick demo
In this section, you will find a step-by-step demo to show you how to use the scripts. Let us assume you already download the codes and install all the necessary dependencies.

Suppose to prepare the next HCERES evaluation, we need to make sure that all the papers for a research team 'LGI-SR' published between 2020 - 2024 are uploaded in HAL, and the stamps are 'LGI-SR'. 

## Step 1: Search Scopus for the paper metadata

First, we need to search Scopus for the paper metadata. In this research team, there are three permenant researchers and each of them has their own Scopus-id. So we can easiliy get the required metadata through the following Scopus query:

```
AU-ID(55659850100) OR AU-ID(55348807500) OR AU-ID(7102745133) AND PUBYEAR > 2019 AND PUBYEAR < 2025
```

Then, we output the results to `data/inputs/scopus_results.csv`: Please select "all" and then "export to csv" as follows.

<img src='screenshots/scopus_search.gif' width='1200'>

## Step 2: Prepare the `data/auth_db.csv` file

The `data/auth_db.csv` file is used to map each author to his/her full name (rather than initials), affiliations id in HAL, and idHAL in HAL. If you don't have the information about the authors in your database, you can skip this step. Otherwise, you need to provide the information in this file. The first column is the author key, it should match the author name field in the Scopus records. 

__Please note that if an author has different ways of spelling its initials in the Scopus record, you need add multiple entries in this table, each one corresponding to one way of spelling__ An example of auth_db.csv can be found [here.](data/inputs/auth_db.csv)


## Step 3: Prepare the `data/path_and_perso_data.json` file. 

Provide your HAL user names, passwords, and Scopus API key in this file. The format of this file should be the following:

```json
{
    "perso_login_hal": "your_hal_login",
    "perso_mdp_hal": "your_hal_password",
    "perso_scopusApikey": "your_scopus_apikey"
    "perso_scopusInstToken": "your_scopus_insttoken"
}
```

## Step 4: Change the stamps for the teams.

In this example, we want to upload the papers to HAL with the stamp 'LGI-SR' and 'CHAIRE-RRSC'. So we need to modify the `stamp` variable in the `hal_upload_from_scopus.py` file. 
You should modify the stamps according to your needs. 

```python 
line 11: stamps = ['your_stamp_1']
```

## Step 5: Run `hal_upload_from_scopus.py`

Finally, we can run the `hal_upload_from_scopus.py` script. If everything goes well, you will see the following output in the terminal:



# Further information

This repository is built based on the APIs from HAL and Scopus. If you would like to have some basic knowledge about how to use these APIs, please refer to the following links:
- Official document for [HAL API](https://api.archives-ouvertes.fr/docs)
- Get the ids of authors and affiliations already existed in HAL from [aureHAL](https://aurehal.archives-ouvertes.fr/)
- Official document for [Scopus API](https://dev.elsevier.com/guides/Scopus%20API%20Guide_V1_20230907.pdf)

There some other works on automating the uploading process of papers to HAL:
