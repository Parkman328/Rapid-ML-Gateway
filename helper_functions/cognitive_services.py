import json, uuid
import logging
import logging.config
import os, sys, inspect, time
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PARENT_DIR, 'helper_functions'))
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

def authenticate_client(key, endpoint):
    ta_credential = AzureKeyCredential(key)
    text_analytics_client = TextAnalyticsClient(
            endpoint=endpoint, 
            credential=ta_credential) 
    return text_analytics_client

def translate(key, region, endpoint):
    headers = {
         'Ocp-Apim-Subscription-Key': key,
         'Ocp-Apim-Subscription-Region': region,
         'Content-type': 'application/json',
         'X-ClientTraceId': str(uuid.uuid4())   
        }
    path = '/translate?api-version=3.0'
    constructed_url = endpoint + path 
    return headers, constructed_url

def language_detection(client, documents):
    print(documents)
    try:
        #documents = ["Ce document est rédigé en Français."]
        print("Inside Try")
        response = client.detect_language(documents = documents, country_hint = 'us')[0]
        print("Language: ", response.primary_language.name)
    except Exception as err:
        print("Encountered exception. {}".format(err))
    return response.primary_language.name

def key_phrase_extraction(client, documents):

    try:
        response = client.extract_key_phrases(documents = documents)[0]
        ret_str = ""
        delim=", "
        if not response.is_error:
            temp = list(map(str, response.key_phrases)) 
            ret_str = delim.join(temp)
        else:
            print(response.id, response.error)
    except Exception as err:
        print("Encountered exception. {}".format(err))
    return ret_str, response


def sentiment_analysis(client, documents):

    #documents = ["I had the best day of my life. I wish you were there with me."]
    response = client.analyze_sentiment(documents = documents)[0]
    print("Document Sentiment: {}".format(response.sentiment))
    print("Overall scores: positive={0:.2f}; neutral={1:.2f}; negative={2:.2f} \n".format(
        response.confidence_scores.positive,
        response.confidence_scores.neutral,
        response.confidence_scores.negative,
    ))
    for idx, sentence in enumerate(response.sentences):
        print("Sentence: {}".format(sentence.text))
        print("Sentence {} sentiment: {}".format(idx+1, sentence.sentiment))
        print("Sentence score:\nPositive={0:.2f}\nNeutral={1:.2f}\nNegative={2:.2f}\n".format(
            sentence.confidence_scores.positive,
            sentence.confidence_scores.neutral,
            sentence.confidence_scores.negative,
        ))
    return response  

def annmaly_detection(url):
    return 0