#! /usr/bin/env python3
import os 
import sys
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PARENT_DIR, 'generated'))
sys.path.append(os.path.join(PARENT_DIR, 'helper_functions'))
import argparse
import json
import logging
import logging.config
import inspect, time
from websocket import create_connection
import socket
import re
from concurrent import futures
from datetime import datetime
import requests, uuid
import configparser
import ServerSideExtension_pb2 as SSE
import grpc
import qlist
import cognitive_services as cs
from google.protobuf.json_format import MessageToDict
from ssedata import ArgType, FunctionType, ReturnType
# import helper .py files
#from scripteval import ScriptEval
_ONE_DAY_IN_SECONDS = 60 * 60 * 24
config = configparser.ConfigParser()


class ExtensionService(SSE.ConnectorServicer):
    """
    A simple SSE-plugin created for the HelloWorld example.
    """

    def __init__(self, funcdef_file):
        """
        Class initializer.
        :param funcdef_file: a function definition JSON file
        """
        self._function_definitions = funcdef_file
        #self.ScriptEval = ScriptEval()
        os.makedirs('logs', exist_ok=True)
        log_file = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), 'logger.config')
        logging.config.fileConfig(log_file)
        logging.info(log_file)
        logging.info(self._function_definitions)
        logging.info('Logging enabled')
        function_name = "none"

    @property
    def function_definitions(self):
        """
        :return: json file with function definitions
        """
        return self._function_definitions

    @property
    def functions(self):
        """
        :return: Mapping of function id and implementation
        """
        return {
            0: '_rest_single',
        }

    @staticmethod
    def _get_function_id(context):
        """
        Retrieve function id from header.
        :param context: context
        :return: function id
        """
        metadata = dict(context.invocation_metadata())
        header = SSE.FunctionRequestHeader()
        header.ParseFromString(metadata['qlik-functionrequestheader-bin'])

        return header.functionId

  
       
    @staticmethod
    def _rest_single(request, context):
        """
        Rest using single variable
        """
        logging.info('Entering {} TimeStamp: {}' .format(function_name, datetime.now().strftime("%H:%M:%S.%f")))
   
        bCache= config.get(q_function_name, 'cache')
        logging.debug("Caching is set to {}" .format(bCache))
    
        if (bCache.lower() =="true"):
            logging.info("Caching ****Enabled*** for {}" .format(q_function_name))
        else:
            logging.info("Caching ****Disabled**** for {}" .format(q_function_name))
            md = (('qlik-cache', 'no-store'),)
            context.send_initial_metadata(md)
        response_rows = []
        request_counter = 1
        #if(q_function_name=='translate'):
        endpoint = config.get(q_function_name, 'endpoint') 
        logging.debug("endpoint is set to {}" .format(endpoint))
        key = config.get(q_function_name, 'key')
        logging.debug("key is set to {}" .format(key))
        region = config.get(q_function_name,  'region')
        logging.debug("region is set to {}" .format(region))
        
        for request_rows in request:
            logging.debug('Printing Request Rows - Request Counter {}' .format(request_counter))
            request_counter = request_counter +1
            for row in request_rows.rows:
                param = [d.strData for d in row.duals]
                logging.debug("The incoming parameter {}" .format(param))
                if (len(param[0])==0):
                    param[0] = "NA"
                if(q_function_name=='translate'):
                    language  = '&to=' + param[1]
                    logging.debug('Showing Language to Translate to : {}'.format(language))
                    client = cs.translate(key, region, endpoint)
                    finished_url = client[1] +language
                    logging.debug('Showing finished url to : {}'.format(finished_url))
                    input_text = param[0].replace('"','\\').replace(',','\\,')
                    body = [{'text' : input_text}]
                    logging.debug('Showing message body: {}'.format(body))
                    request = requests.post(finished_url, headers=client[0], json=body)
                    resp= request.json()
                    logging.debug('Show Payload Response as Text: {}'.format(resp))
                    result =''
                    if(param[-1] =='score'):
                        result = str(resp[0]['detectedLanguage']['score'])
                        logging.debug('Score: {}'.format(result))
                        print(result)
                        print(type(result))
                        #duals = iter([SSE.Dual(strData=result)])
                    if(param[-1] =='text'):   
                        result = resp[0]['translations'][0]['text']
                        print(type(result))
                    logging.debug('Translation: {}'.format(result))
                elif(q_function_name=='language_detection'):
                    client = cs.authenticate_client(key, endpoint)
                    result =cs.language_detection(client, param)
                    logging.debug('language detection: {}'.format(result))
                elif(q_function_name=='key_phrase_extraction'):
                    client = cs.authenticate_client(key, endpoint)
                    output =cs.key_phrase_extraction(client, param)
                    result = output[0]
                    logging.debug('key_phrase_extraction: {}'.format(result))
                elif(q_function_name=='sentiment_analysis'):
                    client = cs.authenticate_client(key, endpoint)
                    output =cs.sentiment_analysis(client, param)
                    print(output)
                    print(type(output))
                    if(param[-1] =='sentiment'):
                        result = output.sentiment
                    elif(param[-1] =='positive_score'):
                        result = str(output.confidence_scores.positive)
                    elif(param[-1] =='negative_score'):
                        result = str(output.confidence_scores.negative)
                    elif(param[-1] =='neutral_score'):
                        result = str(output.confidence_scores.neutral)
                    else:
                        result = output.sentiment
                    logging.debug('key_phrase_extraction: {}'.format(result))
                else:
                    result=""                
                
                duals = iter([SSE.Dual(strData=result)])
                response_rows.append(SSE.Row(duals=duals))               
        yield SSE.BundledRows(rows=response_rows)
        logging.info('Exiting {} TimeStamp: {}' .format(function_name, datetime.now().strftime("%H:%M:%S.%f")))


    @staticmethod
    def _cache(request, context):
        """
        Cache enabled. Add the datetime stamp to the end of each string value.
        :param request: iterable sequence of bundled rows
        :param context: not used.
        :return: string
        """
        # Iterate over bundled rows
        for request_rows in request:
            # Iterate over rows
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals][0]

                # Join with current timedate stamp
                result = param + ' ' + datetime.now().isoformat()
                # Create an iterable of dual with the result
                duals = iter([SSE.Dual(strData=result)])

                # Yield the row data as bundled rows
                yield SSE.BundledRows(rows=[SSE.Row(duals=duals)])

    @staticmethod
    def _no_cache(request, context):
        """
        Cache disabled. Add the datetime stamp to the end of each string value.
        :param request:
        :param context: used for disabling the cache in the header.
        :return: string
        """
        # Disable caching.
        md = (('qlik-cache', 'no-store'),)
        context.send_initial_metadata(md)

        # Iterate over bundled rows
        for request_rows in request:
            # Iterate over rows
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals][0]

                # Join with current timedate stamp
                result = param + ' ' + datetime.now().isoformat()
                # Create an iterable of dual with the result
                duals = iter([SSE.Dual(strData=result)])
       
                # Yield the row data as bundled rows
                yield SSE.BundledRows(rows=[SSE.Row(duals=duals)])

    def _get_call_info(self, context):
        """
        Retreive useful information for the function call.
        :param context: context
        :return: string containing header info
        """

        # Get metadata for the call from the context
        metadata = dict(context.invocation_metadata())
        
        # Get the function ID
        func_header = SSE.FunctionRequestHeader()
        func_header.ParseFromString(metadata['qlik-functionrequestheader-bin'])
        func_id = func_header.functionId

        # Get the common request header
        common_header = SSE.CommonRequestHeader()
        common_header.ParseFromString(metadata['qlik-commonrequestheader-bin'])

        # Get capabilities
        if not hasattr(self, 'capabilities'):
            self.capabilities = self.GetCapabilities(None, context)

        # Get the name of the capability called in the function
        capability = [function.name for function in self.capabilities.functions if function.functionId == func_id][0]
                
        # Get the user ID using a regular expression
        match = re.match(r"UserDirectory=(?P<UserDirectory>\w*)\W+UserId=(?P<UserId>\w*)", common_header.userId, re.IGNORECASE)
        if match:
            userId = match.group('UserDirectory') + '/' + match.group('UserId')
        else:
            userId = common_header.userId
        
        # Get the app ID
        appId = common_header.appId
        # Get the call's origin
        peer = context.peer()

        return "{0} - Capability '{1}' called by user {2} from app {3}".format(peer, capability, userId, appId)
   
    def EvaluateScript(self, request, context):
        """
        This plugin supports full script functionality, that is, all function types and all data types.
        :param request:
        :param context:
        :return:
        """
        logging.debug('In EvaluateScript: Main')
        # Parse header for script request
        metadata = dict(context.invocation_metadata())
        logging.debug('Metadata {}',metadata)
        header = SSE.ScriptRequestHeader()
        header.ParseFromString(metadata['qlik-scriptrequestheader-bin'])
        logging.debug('Header is : {}'.format(header))
        logging.debug('Request is : {}' .format(request))
        logging.debug("Context is: {}" .format(context))
        return self.ScriptEval.EvaluateScript(header, request, context)

    @staticmethod
    def _echo_table(request, context):
        """
        Echo the input table.
        :param request:
        :param context:
        :return:
        """
        for request_rows in request:
            response_rows = []
            for row in request_rows.rows:
                response_rows.append(row)
            yield SSE.BundledRows(rows=response_rows)

    def GetCapabilities(self, request, context):
        """
        Get capabilities.
        Note that either request or context is used in the implementation of this method, but still added as
        parameters. The reason is that gRPC always sends both when making a function call and therefore we must include
        them to avoid error messages regarding too many parameters provided from the client.
        :param request: the request, not used in this method.
        :param context: the context, not used in this method.
        :return: the capabilities.
        """
        logging.info('GetCapabilities')
        # Create an instance of the Capabilities grpc message
        # Enable(or disable) script evaluation
        # Set values for pluginIdentifier and pluginVersion
        capabilities = SSE.Capabilities(allowScript=True,
                                        pluginIdentifier='Qlik Rapid API Gateway - Partner Engineering',
                                        pluginVersion='v0.1.0')
        # If user defined functions supported, add the definitions to the message
        with open(self.function_definitions) as json_file:
            # Iterate over each function definition and add data to the capabilities grpc message
            for definition in json.load(json_file)['Functions']:
                function = capabilities.functions.add()
                function.name = definition['Name']
                function.functionId = definition['Id']
                function.functionType = definition['Type']
                function.returnType = definition['ReturnType']
            
                # Retrieve name and type of each parameter
                for param_name, param_type in sorted(definition['Params'].items()):
                    function.params.add(name=param_name, dataType=param_type)

                logging.info('Adding to capabilities: {}({})'.format(function.name,
                                                                     [p.name for p in function.params]))

        return capabilities

    def ExecuteFunction(self, request_iterator, context):
        """
        Execute function call.
        :param request_iterator: an iterable sequence of Row.
        :param context: the context.
        :return: an iterable sequence of Row.
        """
        func_id = self._get_function_id(context)
        logging.info(self._get_call_info(context))
        # Call corresponding function
        logging.info('ExecuteFunctions (functionId: {})' .format(func_id))
        #self.functions[func_id]))
        current_function_def = (json.load(open(self.function_definitions))['Functions'])[func_id]
        logging.debug(current_function_def)
        global q_function_name
        q_function_name = current_function_def["Name"]
        logging.debug('Logical Method Called is: {}' .format(q_function_name))
        
        current_qrap_type = current_function_def["QRAP_Type"]
        qrag_function_name ='_' + current_qrap_type
        logging.debug('This is the type of QRAG Method Name: {}' .format(current_qrap_type))
        logging.debug('Physical Method Called is:  {}' .format(qrag_function_name))
        # Convers to Method Name to Physical Main Function
        qrag_id = qlist.find_key(self.functions, qrag_function_name)
        logging.debug('QRAG ID: {}' .format(qrag_id))
        global function_name 
        function_name = self.functions[qrag_id]
        return getattr(self, self.functions[qrag_id])(request_iterator, context)

    def Serve(self, port, pem_dir):
        """
        Sets up the gRPC Server with insecure connection on port
        :param port: port to listen on.
        :param pem_dir: Directory including certificates
        :return: None
        """
        # Create gRPC server
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        SSE.add_ConnectorServicer_to_server(self, server)

        if pem_dir:
            # Secure connection
            with open(os.path.join(pem_dir, 'sse_server_key.pem'), 'rb') as f:
                private_key = f.read()
            with open(os.path.join(pem_dir, 'sse_server_cert.pem'), 'rb') as f:
                cert_chain = f.read()
            with open(os.path.join(pem_dir, 'root_cert.pem'), 'rb') as f:
                root_cert = f.read()
            credentials = grpc.ssl_server_credentials([(private_key, cert_chain)], root_cert, True)
            server.add_secure_port('[::]:{}'.format(port), credentials)
            logging.info('*** Running server in secure mode on port: {} ***'.format(port))
        else:
            # Insecure connection
            server.add_insecure_port('[::]:{}'.format(port))
            logging.info('*** Running server in insecure mode on port: {} ***'.format(port))

        # Start gRPC server
        server.start()
       
        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            server.stop(0)
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    conf_file = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'config', 'qrag.ini')

    #config.read(os.path.join(os.path.dirname(__file__), 'config', 'qrag.ini'))
    logging.debug(conf_file)
    logging.info('Location of qrag.ini {}' .format(conf_file))
    config.read(conf_file)
    port = config.get('base', 'port')
    parser.add_argument('--port', nargs='?', default=port)
    parser.add_argument('--pem_dir', nargs='?')
    parser.add_argument('--definition_file', nargs='?', default='functions.json')
    args = parser.parse_args()
    # need to locate the file when script is called from outside it's location dir.
    def_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.definition_file)
    #print(def_file)
    calc = ExtensionService(def_file)
    logging.info('*** Server Configurations Port: {}, Pem_Dir: {}, def_file {} TimeStamp: {} ***'.format(args.port, args.pem_dir, def_file,datetime.now().isoformat()))

    calc.Serve(args.port, args.pem_dir)