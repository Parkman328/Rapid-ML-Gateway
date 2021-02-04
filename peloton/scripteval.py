import os, sys
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PARENT_DIR, 'generated'))
sys.path.append(os.path.join(PARENT_DIR, 'helper_functions'))
import logging
import logging.config
import peloton, qlist
import ServerSideExtension_pb2 as SSE
import grpc
import numpy 
import configparser
from ssedata import ArgType, FunctionType, ReturnType
config = configparser.ConfigParser()
from flatten_dict import flatten

class ScriptEval:
    """
    Class for SSE plugin ScriptEval functionality.
    """

    def EvaluateScript(self, header, request, context):
        """
        Evaluates script provided in the header, given the
        arguments provided in the sequence of RowData objects, the request.

        :param header:
        :param request: an iterable sequence of RowData.
        :param context: the context sent from client
        :return: an iterable sequence of RowData.
        """
        # Read Qrag File 
        conf_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'qrag.ini')
        logging.info('Location of qrag.ini {}' .format(conf_file))
        config.read(conf_file)

        # Retrieve function type
        func_type = self.get_func_type(header)

        # Retrieve data types from header
        arg_types = self.get_arg_types(header)
        ret_type = self.get_return_type(header)

        logging.info('EvaluateScript: {} ({} {}) {}'
                     .format(header.script, arg_types, ret_type, func_type))

        # Check if parameters are provided
        if header.params:
            all_rows = []

            # Iterate over bundled rows
            for request_rows in request:
                # Iterate over rows
                for row in request_rows.rows:
                    # Retrieve parameters
                    params = self.get_arguments(context, arg_types, row.duals, header)
                    all_rows.append(params)

            # First element in the parameter list should contain the data of the first parameter.
            all_rows = [list(param) for param in zip(*all_rows)]

            if arg_types == ArgType.Mixed:
                param_datatypes = [param.dataType for param in header.params]
                for i, datatype in enumerate(param_datatypes):
                    if datatype == SSE.DUAL:
                        # For easier access to the numerical and string representation of duals, in the script, we
                        # split them to two list. For example, if the first parameter is dual, it will contain two lists
                        # the first one being the numerical representation and the second one the string.
                        all_rows[i] = [list(datatype) for datatype in zip(*all_rows[i])]

            logging.debug('Received data from Qlik (args): {}'.format(all_rows))
            result = self.evaluate(context, header.script, ret_type, params=all_rows)

        else:
            # No parameters provided
            logging.debug('No Parameteres Provided')
            result = self.evaluate(context, header.script, ret_type)
        bundledRows = SSE.BundledRows()
        if isinstance(result, str) or not hasattr(result, '__iter__'):
            # A single value is returned
            bundledRows.rows.add(duals=self.get_duals(result, ret_type))
        else:
            for row in result:
                # note that each element of the result should represent a row
                bundledRows.rows.add(duals=self.get_duals(row, ret_type))

        yield bundledRows

    @staticmethod
    def get_func_type(header):
        """
        Retrieves the function type.
        :param header:
        :return:
        """
        func_type = header.functionType
        if func_type == SSE.SCALAR:
            return FunctionType.Scalar
        elif func_type == SSE.AGGREGATION:
            return FunctionType.Aggregation
        elif func_type == SSE.TENSOR:
            return FunctionType.Tensor

    @staticmethod
    def get_arguments(context, arg_types, duals, header):
        """
        Gets the array of arguments based on
        the duals, and the type (string, numeric)
        specified in the header.
        :param context: the context sent from client
        :param header: the script header.
        :param duals: an iterable sequence of duals.
        :return: an array of (potentially mixed data type) arguments.
        """

        if arg_types == ArgType.String:
            # All parameters are of string type
            script_args = [d.strData for d in duals]
        elif arg_types == ArgType.Numeric:
            # All parameters are of numeric type
            script_args = [d.numData for d in duals]
        elif arg_types == ArgType.Mixed:
            # Parameters can be either string, numeric or dual
            script_args = []
            for dual, param in zip(duals, header.params):
                if param.dataType == SSE.STRING:
                    script_args.append(dual.strData)
                elif param.dataType == SSE.NUMERIC:
                    script_args.append(dual.numData)
                elif param.dataType == SSE.DUAL:
                    script_args.append((dual.numData, dual.strData))
        else:
            # Undefined argument types
            # Make sure the error handling, including logging, works as intended in the client
            msg = 'Undefined argument type: '.format(arg_types)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(msg)
            # Raise error on the plugin-side
            raise grpc.RpcError(grpc.StatusCode.INVALID_ARGUMENT, msg)
        return script_args

    @staticmethod
    def get_arg_types(header):
        """
        Determines the argument types for all parameters.
        :param header:
        :return: ArgType
        """
        data_types = [param.dataType for param in header.params]

        if not data_types:
            return ArgType.Empty
        elif len(set(data_types)) > 1 or all(data_type == SSE.DUAL for data_type in data_types):
            return ArgType.Mixed
        elif all(data_type == SSE.STRING for data_type in data_types):
            return ArgType.String
        elif all(data_type == SSE.NUMERIC for data_type in data_types):
            return ArgType.Numeric
        else:
            return ArgType.Undefined

    @staticmethod
    def get_return_type(header):
        """
        :param header:
        :return: Return type
        """
        if header.returnType == SSE.STRING:
            return ReturnType.String
        elif header.returnType == SSE.NUMERIC:
            return ReturnType.Numeric
        elif header.returnType == SSE.DUAL:
            return ReturnType.Dual
        else:
            return ReturnType.Undefined
    @staticmethod
    def remove_columns(remlist, list_of_dict):
       
        for x in remlist:
            for dict in list_of_dict:
                #logging.debug(dict['name'])
                logging.debug("deleting {}" .format(x))
                key  = x.strip()
                logging.debug("deleting {}" .format(key))
                if key in dict.keys():
                    del dict[key]
        return list_of_dict
    @staticmethod
    def remove_columns_dict(remlist, dict):
        
        for x in remlist:
            #logging.debug(dict['name'])
            logging.debug("deleting {}" .format(x))
            key  = x.strip()
            logging.debug("deleting {}" .format(key))
            if key in dict.keys():
                del dict[key]
        return dict
    @staticmethod
    def get_duals(result, ret_type):
        if isinstance(result, str) or not hasattr(result, '__iter__'):
            result = [result]
        # Transform the result to an iterable of Dual data
        if ret_type == ReturnType.String:
            duals = [SSE.Dual(strData=col) for col in result]
        elif ret_type == ReturnType.Numeric:
            duals = [SSE.Dual(numData=col) for col in result]
        return iter(duals)

    @staticmethod
    def send_table_description(table, context):
        """
        # TableDescription is only handled in Qlik if sent from a 'Load ... Extension ...' script.
        # If tableDescription is set when evaluating an expression the header will be ignored
        # when received by Qlik.
        :param qResult: the result from evaluating the script
        :param table: the table description specified in the script
        :param context: the request context
        :return: nothing
        """
        #print(table)
        logging.debug('tableDescription sent to Qlik: {}'.format(table))
        # send table description
        table_header = (('qlik-tabledescription-bin', table.SerializeToString()),)
        context.send_initial_metadata(table_header)

    def evaluate(self, context, script, ret_type, params=[]):
        """
        Evaluates a script with given parameters and construct the result to a Row of duals.
        :param script:  script to evaluate
        :param ret_type: return data type
        :param params: params to evaluate. Default: []
        :return: a RowData of string dual
        """
        # Evaluate script
        logging.info("In Evaluate {} {} {}" .format(script, ret_type, params))


        table = SSE.TableDescription()
        logging.info("Peleton Function {} called" .format(script))
        #If User name and Password Present Remove Username and Password and Pass only function name
        if(script.find('(') !=-1):
            index=script.index('(')
            UserPass = script[index:]
            script = script[:index]
            UserPass = (UserPass.replace('(','')).replace(')','')
            index=UserPass.index(',')
            Pass = (UserPass[index:]).replace(',','')
            User = UserPass[:index]
            logging.debug("index {}, Script {} , UserPass {}, User {} Pass {}" .format(index, script, UserPass, User, Pass ))
            session = self.get_all_sessions(User, Pass)
        url = config.get(script, 'url')

        if (script.find('get_all_instructors') !=-1):
            result = self.get_all_instructors(url)
            #list of Dictionary returned
            logging.debug("result type  : {} data : {} " .format(type(result), result))
            remlist = (config.get(script, 'remlist')).strip('][').split(', ')
            logging.debug("Remlist Type {}, List {}" .format(type(remlist), remlist))
            if (len(remlist)) > 1:
                result = self.remove_columns(remlist, result)
            logging.debug("result type  : {} data : {} " .format(type(result), result))
            converted = qlist.convert_list_of_dicts(result)
            logging.debug("converted type JRP : {} columns : {} data :{} " .format(type(converted[0]), converted[0], converted[1]))
            
            table.name = 'Peloton-Instructor'
            for i in converted[0]:
                FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            result = converted[1]
            logging.debug("result type  : {} data : {} " .format(type(result), result))
            for x in result:
                logging.debug("x type  : {} data : {} " .format(type(x), x))
        elif (script.find('get_all_sessions') !=-1):
            logging.debug("get_all_sessions")
            UserData = session[2]
            UserWorkout = session[3]
            UserId=session[4]
            #filter all the non values
            #converst string representation to list
            remlist = (config.get(script, 'remlist')).strip('][').split(', ')
            logging.debug("Remlist Type {}, List {}" .format(type(remlist), remlist))
            if (len(remlist)) > 1:
                result = self.remove_columns_dict(remlist, UserData)
            else:
                result = UserData

            converted = qlist.convert_dicts_list(result)
            table.name= User +'- Peloton User Data'
            logging.debug("column  {}" .format(converted[0]))
            for i in converted[0]:
                FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            result=[]
            result.append(converted[1])
            logging.debug("result {}" .format(result))
            
        elif (script.find('get_all_workouts') !=-1):
            logging.debug("Calling get_all_workouts")
            UserData = session[2]
            UserWorkout = session[3]
            UserId=session[4]
            remlist = (config.get(script, 'remlist')).strip('][').split(', ')
            logging.debug("Remlist Type {}, List {}" .format(type(remlist), remlist))
            if (len(remlist)) > 1:
                result = self.remove_columns(remlist, UserWorkout)
            else:
                result = UserWorkout
            logging.debug("result type  : {} data : {} " .format(type(result), result))
            converted = qlist.convert_list_of_dicts(result)
            logging.debug("converted type JRP : {} columns : {} data :{} " .format(type(converted[0]), converted[0], converted[1]))
            #insert user id
            converted[0].insert(0, 'user_id')
            for x in converted[1]:
                x.insert(0, UserId)
            table.name = User +'- Peloton Work Out Data'
            for i in converted[0]:
                FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            result = converted[1]
            logging.debug("result type  : {} data : {} " .format(type(result), result))
         
       
        elif (script.find('get_all_rides') !=-1):
            result =[]
            options = config.get(script, 'options')
            url = config.get(script, 'url')
            UserData = self.get_all_workouts(session[0],url, session[2]["id"], options)
            logging.debug("get all workout {}" .format(UserData))
            UserData = UserData['data']
            UserId= session[4]
            UserData_Flattened = []
            logging.debug("UserData Type {}, List {}" .format(type(UserData), UserData))
            for x in UserData:
                logging.debug("UserDataElements Type {}, List {}" .format(type(x), x))
                flattend = flatten(x, reducer = 'underscore')
                UserData_Flattened.append(flattend)
            
            remlist = (config.get(script, 'remlist')).strip('][').split(', ')
            logging.debug("Remlist Type {}, List {}" .format(type(remlist), remlist))
            if (len(remlist)) > 1:
                result = self.remove_columns(remlist, UserData_Flattened)
            else:
                result = UserData_Flattened
            converted = qlist.convert_list_of_dicts(result)
            logging.debug("converted type JRP : {} columns : {} data :{} " .format(type(converted[0]), converted[0], converted[1]))
            converted[0].insert(0, 'user_id')
            for x in converted[1]:
                x.insert(0, UserId)
            table.name= User +'- Peloton Ride Data'
            for i in converted[0]:
                FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            result = converted[1]
            logging.debug("result type  : {} data : {} " .format(type(result), result))
            
        elif (script.find('get_all_output') !=-1):
            result =[]
            #get a list of workout ids
            options = config.get(script, 'options')
            url = config.get(script, 'user_url')
            UserData = self.get_all_workouts(session[0],url, session[2]["id"], options)
            UserData = UserData['data']
            logging.debug('UserData type {} and UserData {}' .format(type(UserData), UserData))
         
            workout_ids =[]
            for x in UserData:
                workout_id = (x['id'])
                workout_ids.append(workout_id)
                logging.debug("Workout ID Type {}, Data {}" .format(type(workout_ids), workout_ids))
            options = config.get(script, 'options_summary')
            url = config.get(script, 'url')
            
            remlist = (config.get(script, 'remlist')).strip('][').split(', ')
            logging.debug("Remlist Type {}, List {}" .format(type(remlist), remlist))
            logging.debug(len(remlist))
            
            for x in workout_ids:
                UserData = self.get_all_details(session[0],url, x, options).json()
                logging.debug('UserData type {} and UserData {}' .format(type(UserData), UserData))
                if (len(remlist)) > 1:
                    temp = self.remove_columns_dict(remlist, UserData)
                    logging.debug('Removed UserData type {} and UserData {}' .format(type(UserData), UserData))
                else:
                    temp = UserData
                    logging.debug('No Var UserData type {} and UserData {}' .format(type(UserData), UserData))
                logging.debug('Temp type {} and Temp {}' .format(type(temp), temp))
                converted = qlist.convert_dicts_list(temp)
                result.append(converted[1])
                
            table.name= User +'- Peloton Output Data'
            for i in converted[0]:
                FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            #result = [['a','b','c'],['a','b','c']]
            logging.debug("result {}" .format(result))
        elif (script.find('get_apple_watch_output') !=-1):
            result =[]
            #get a list of workout ids
            options = config.get(script, 'options')
            url = config.get(script, 'user_url')
            UserData = self.get_all_workouts(session[0],url, session[2]["id"], options)
            UserData = UserData['data']
            logging.debug('UserData type {} and UserData {}' .format(type(UserData), UserData))
            workout_ids =[]
            for x in UserData:
                workout_id = (x['id'])
                workout_ids.append(workout_id)
                logging.debug("Workout ID Type {}, Data {}" .format(type(workout_ids), workout_ids))
            options = config.get(script, 'options_summary')
            url = config.get(script, 'url')
            
            remlist = (config.get(script, 'remlist')).strip('][').split(', ')
            logging.debug("Remlist Type {}, List {}" .format(type(remlist), remlist))
            logging.debug(len(remlist))
            
            for x in workout_ids:
                UserData = self.get_all_details(session[0],url, x, options).json()
                logging.debug('UserData type {} and UserData {}' .format(type(UserData), UserData))
                key_to_lookup = 'apple_watch_active_calories'
                if (len(remlist)) > 1:
                    temp = self.remove_columns_dict(remlist, UserData)
                    logging.debug('Removed UserData type {} and UserData {}' .format(type(UserData), UserData))
                else:
                    logging.debug('No Var UserData type {} and UserData {}' .format(type(UserData), UserData))
                    temp = UserData
                if key_to_lookup in temp:
                    logging.debug('We have no Apple Watchj Data {} {}' .format(type(temp), temp))
                else :
                    temp['apple_watch_active_calories'] = ''
                    temp['apple_watch_total_calories'] = ''
                logging.debug('Temp type {} and Temp {}' .format(type(temp), temp))
                converted = qlist.convert_dicts_list(temp)
                result.append(converted[1])
            table.name= User +'- Peloton Apple Watch Output Data'
            for i in converted[0]:
                FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            logging.debug('JRP Columns type {} and columns {}' .format(type(converted[0]), converted[0]))
            logging.debug("result {}" .format(result))
        else:
            result = []

        self.send_table_description(table, context)
        return result
    @staticmethod
    def get_all_instructors(url):
        return peloton.get_all_instructors(url)
    @staticmethod
    def get_all_sessions(user_name, password):
        return peloton.get_all_sessions(user_name, password)
    @staticmethod
    def get_all_workouts(session, url, user_id, options):
        return peloton.get_all_workouts(session, url, user_id, options)
    @staticmethod
    def get_all_details(session, url, workout_id, option):
        return peloton.get_all_details(session, url, workout_id, option)