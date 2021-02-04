from datetime import datetime
from dateutil import tz
import requests, json

def get_all_instructors(url):
    s = requests.get(url)
    result = json.loads(s.text)
    return_val = result["data"]
    return return_val 

def get_instructor(url, instructor_id):
    s = requests.get(url+"/"+instructor_id)
    result = json.loads(s.text)
    return_val = []
    instructor_list_elem = []
    id = result['id']
    name = result['name']
    fitness_disciplines =  ', '.join([str(elem) for elem in result['fitness_disciplines']]) 
    instructor_list_elem = [id, name, fitness_disciplines]
    return_val.append(instructor_list_elem)
    return return_val
    
def get_all_sessions(user_name, password):
    s = requests.Session()
    payload = {'username_or_email': user_name, 'password': password}
    r = s.post('https://api.onepeloton.com/auth/login', json=payload)
    result = json.loads(r.text)
    S_userid = result['user_id']
    D_userdata = result['user_data']
    L_workout = result['user_data']['workout_counts']
    return s, result, D_userdata, L_workout, S_userid


def get_all_workouts(s, url, user_id, option):
    url = url + user_id + '/workouts' + option
    r = s.get(url)
    result = r.json()
    return result


def get_all_details(s, url, workout_id, option):
    url = url + workout_id + option
    result = s.get(url)
    return result



    
