import glom
import numpy as np

#
def divide_chunks(l, n): 
      
    # looping till length l 
    for i in range(0, len(l), n):  
        yield l[i:i + n]    

def find_key(input_dict, value):
    return next((k for k, v in input_dict.items() if v == value), None)

def get_table_id(input_dict, value):
    keys = input_dict.keys()
    id = "Not Found"
    for k in keys:
        path = k + ".name"
        #print(path)
        table_name = glom.glom(input_dict, path)
        #print(table_name)
        if(table_name == value):
            id = k
            #path = k +".description.table.steps"
    return id

def convert_list_of_dicts(input_list):
    result = []
    for x in input_list:
        columns = list(x.keys())
        values = list(x.values())
        values = ["NA" if x == '' else x for x in values]
        temp = [str(x) for x in values]
        result.append(temp)
    return columns, result

def convert_dicts_list(input_dict):
    columns = list(input_dict.keys())
    values = list(input_dict.values())
    values = ["NA" if x == '' else x for x in values]
    temp = [str(x) for x in values]
    return columns, temp

def convert_df_list(input_df):
    temp_dict = input_df.to_dict('split')
    columns = temp_dict['columns']
    columns.insert(0,input_df.index.name) 
    values = []
    #temp_dict['data']
    i = 0
    for x in temp_dict['data']:
        temp =  ['%.6f' % y for y in x]
        temp.insert(0, np.datetime_as_string(input_df.index.values[i], unit='D'))
        i +=1
        data = [str(y) for y in temp]
        print('data {}', format(data))
        values.append(data)
    return columns, values

def convert_df_list_cov(input_df):
    temp_dict = input_df.to_dict('split')
    columns = temp_dict['columns']
    columns.insert(0,'Ticker') 
    values = []
    print('temp_dict type: {} data: {}'  .format(type(temp_dict['data']), temp_dict['data']))
    i= 0
    print(input_df.index.values)
    for x in temp_dict['data']:
        temp = ['%.6f' % y for y in x]
        print('temp type:{} data:{}' .format(type(temp), temp))
        temp.insert(0, input_df.index.values[i])
        i +=1
        data = [str(y).strip() for y in temp]
        print('data type:{} data:{}' .format(type(data), data))
        values.append(data)
    return columns, values

def convert_df_list_sim(input_df):
    temp_dict = input_df.to_dict('split')
    columns = temp_dict['columns']
    columns.insert(0,'random_portfolio_id') 
    values = []
    #temp_dict['data']
    i= 0
    print(input_df.index.values)
    for x in temp_dict['data']:
        x.insert(0, input_df.index.values[i])
        i +=1
        temp = [str(y).strip() for y in x]
        values.append(temp)
    return columns, values