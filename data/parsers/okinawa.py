import sys
import requests
import csv
import io
from datetime import datetime

import simplejson
import json
import pandas as pd
import numpy as np
import collections

from collections import defaultdict
from .utils import store_data, stoi

# ------------------------------------------------------------------------
# Globals
cols = ['time', 'cases', 'deaths', 'hospitalized', 'icu', 'recovered']
url = 'https://raw.githubusercontent.com/Code-for-OKINAWA/covid19/development/data/data.json'

# ------------------------------------------------------------------------
# Main point of entry

def parse():

    #import data from github in json format
    r = requests.get(url)
    if not r.ok:
        print(f"Failed to fetch {url}", file=sys.stderr)
        exit(1)
    
    r.status_code
    raw_data=r.json()
    
    #conversion from json to pandas dataframe
    data_string = json.dumps(raw_data)
    data_decoded = json.loads(data_string)
    patients_data=data_decoded["patients"]["data"]
    patients_dataframe = pd.DataFrame(patients_data)
    
    #translation from japanese to english
    dictionary_keys={'年代': 'age','性別': 'gender','備考': 'notes','居住地':'residence','退院':'discharge'}
    dictionary_discharged={'退院': 'recovered', '入院調整中': 'hospital','入院': 'hospital', '確認中': 'checking'}
    patients_dataframe=patients_dataframe.rename(columns=dictionary_keys)
    patients_dataframe['discharge'] = patients_dataframe['discharge'].astype('str')
    patients_dataframe=patients_dataframe.replace(dictionary_discharged)
    
    #check states modification at the source
    discharged_to_check = ['recovered', 'hospital', 'icu', 'None','deaths']
    discharged_actual = patients_dataframe.discharge.unique()
    added_states=(set(discharged_actual).difference(discharged_to_check))
    removed_states=(set(discharged_to_check).difference(discharged_actual))
    if len(removed_states) != 0:
        print("Attention! Patient(s) state(s) absent in the source: ", (removed_states), file=sys.stderr)
    
    if len(added_states) != 0:
        print("Attention! Patient(s) state(s) added in the source: ", (added_states), file=sys.stderr) 
        exit(1)
    
    
    #conversion
    if 'deaths' not in patients_dataframe:
    	patients_dataframe['deaths']=0
    
    if 'icu' not in patients_dataframe:
    	patients_dataframe['icu']=0
    
    dummy=pd.get_dummies(patients_dataframe['discharge'])
    patients_dataframe=pd.concat([patients_dataframe,dummy],axis=1)
    patients_dataframe['cases'] = patients_dataframe['recovered'] + patients_dataframe['hospital']+ patients_dataframe['icu']+ patients_dataframe['deaths']
        
    #range of dates till now
    first_date=patients_dataframe['date'].iloc[0]
    last_date=patients_dataframe['date'].iloc[-1]
    dates_list = pd.date_range(first_date, last_date)
    
    #group by date
    patients_dataframe = patients_dataframe.set_index('date') 
    grouped_patients_dataframe=patients_dataframe[['cases', 'deaths', 'hospital', 'icu', 'recovered']].copy()
    grouped_patients_dataframe=patients_dataframe.groupby("date").sum()
    
    #add missing days
    grouped_patients_dataframe.index = pd.DatetimeIndex(grouped_patients_dataframe.index)
    grouped_patients_dataframe = grouped_patients_dataframe.reindex(dates_list, fill_value=0)
    grouped_patients_dataframe = grouped_patients_dataframe.rename_axis('date')
    
    #cummulative sum
    grouped_patients_dataframe=grouped_patients_dataframe.cumsum()
    
    #output
    output_patients_dataframe=grouped_patients_dataframe[['cases', 'deaths', 'hospital', 'icu', 'recovered']].copy()
    output_patients_dataframe= output_patients_dataframe.reset_index()
    output_patients_dataframe['date'] = output_patients_dataframe['date'].astype('str')
    date_patientstates =[] 
    for index, rows in output_patients_dataframe.iterrows():
        my_list =[rows.date, rows.cases, rows.deaths, rows.hospital, rows.icu, rows.recovered]
        date_patientstates.append(my_list)
    
    
    region_tables = {}
    region_tables={'JP-Okinawa':date_patientstates}
