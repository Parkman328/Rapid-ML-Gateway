import os
import requests
import pandas as pd
from io import StringIO

def score_model(dataset: pd.DataFrame, url,  headers):
  data_json = dataset.to_dict(orient='split')
  response = requests.request(method='POST', headers=headers, url=url, json=data_json)
  if response.status_code != 200:
    raise Exception(f'Request failed with status {response.status_code}, {response.text}')
  return response.json()

def convert_to_df(string, metadata):
  data_string = metadata + '\n' + string 
  #logging.debug(data_string)
  data = StringIO(data_string)
  df = pd.read_csv(data, sep=",")
  return df