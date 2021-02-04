
import os, json, logging
import logging.config
import sys
import ServerSideExtension_pb2 as SSE
import grpc
import precog, qlist, pysize
import configparser
from ssedata import ArgType, FunctionType, ReturnType

config = configparser.ConfigParser()
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
        logging.debug('In EvaluateScritp: ScriptEval')
        # Retrieve function type
        func_type = self.get_func_type(header)
        #logging.debug('Function Type {}' .format(func_type))
        # Retrieve data types from header
        arg_types = self.get_arg_types(header)
        #logging.debug('Arg Type {}' .format(arg_types))
        ret_type = self.get_return_type(header)
        #logging.debug('Return Type {}' .format(ret_type))
        conf_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'qrag.ini')
        ##print(conf_file)
        logging.info('Location of qrag.ini {}' .format(conf_file))
        config.read(conf_file)
        batch_size = int(config.get('base', 'batch_size'))
        logging.info('Size of Batch Size {}' .format(batch_size))
        #print(type(batch_size))
        logging.info('EvaluateScript: {} ({} {}) {}'
                     .format(header.script, arg_types, ret_type, func_type))

        # Check if parameters are provided
        #print(header.params)
        if header.params:
            all_rows = []

            # Iterate over bundled rows
            for request_rows in request:
                # Iterate over rows
                for row in request_rows.rows:
                    # Retrieve parameters
                    #print('row {} jrp' .format(row))
                    params = self.get_arguments(context, arg_types, row.duals, header)
                    all_rows.append(params)

            # First element in the parameter list should contain the data of the first parameter.
            all_rows = [list(param) for param in zip(*all_rows)]
            #print(all_rows)
            if arg_types == ArgType.Mixed:
                param_datatypes = [param.dataType for param in header.params]
                for i, datatype in enumerate(param_datatypes):
                    if datatype == SSE.DUAL:
                        # For easier access to the numerical and string representation of duals, in the script, we
                        # split them to two list. For example, if the first parameter is dual, it will contain two lists
                        # the first one being the numerical representation and the second one the string.
                        all_rows[i] = [list(datatype) for datatype in zip(*all_rows[i])]

            logging.debug('Received data from Qlik (args): {}'.format(all_rows))
            return_val = self.evaluate(context, header.script, ret_type, params=all_rows)

        else:
            # No parameters provided
            logging.debug('No Parameteres Provided')
            #print(ret_type)
            result = self.evaluate(context, header.script, ret_type)
        print(type(result))
        print(sys.getsizeof(result))
        #bundledRows = SSE.BundledRows()
        if isinstance(result, str) or not hasattr(result, '__iter__'):
            # A single value is returned
            bundledRows.rows.add(duals=self.get_duals(result, ret_type))
        else:
            logging.debug('Size of Result {} {}'.format(len(result), pysize.get_size(result)))
            #if(len(result) > )
            #result = result[:10000]
            batches = list(qlist.divide_chunks(result, batch_size)) 
            for i in batches:
                #print("loop")
                bundledRows = SSE.BundledRows()
                for row in i:
                    # note that each element of the result should represent a row
                    #logging.debug(row)
                    #logging.debug(type(row))
                    #logging.debug(ret_type)
        
                    #Yield the row data as bundled rows
                    bundledRows.rows.add(duals=self.get_duals(row, ret_type))
                #logging.debug('Size of BundledRow {}'.format(sys.getsizeof(bundledRows)))
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
        table = SSE.TableDescription()
        #print('JRP: {}' .format(table))
        # Evaluate script
        #print(script)
        #print(params)
        conf_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'qrag.ini')
        ##print(conf_file)
        logging.info('Location of qrag.ini {}' .format(conf_file))
        config.read(conf_file)
        url = config.get('base', 'url')
        logging.debug('Precog URL {}' .format(url))
        
        if (script.find('TableInfo') !=-1):
            result = self.getTableInfo(url)
            table.name = 'PreCog-Catalog'
            table.fields.add(name="Table_Id", dataType=0)
            table.fields.add(name="Name", dataType=0)
            table.fields.add(name="Column Desc", dataType=0)
        elif (script.find('TableMetaData') !=-1):
            vTable= script[:-14]
            logging.info('TableMetadata vTable {}' .format(vTable))
            table.name = vTable+"-Metadata"
            result =[]
            column_data = precog.get_column_info(vTable, url)
            table.fields.add(name="column", dataType=0)
            table.fields.add(name="type", dataType=0)
            for i in column_data:
                part = [i["column"], i["type"]]
                #print (part)
                result.append(part)
            #print(result)
        elif (script.find('getTableData') !=-1):
            vTable = script[:-13] 
            logging.info('getTableData vTable {}' .format(vTable))
            table.name = script[:-13]
            column_data = precog.get_column_info(vTable, url)
            for i in column_data:
                FieldName = i["column"]
                if(i["type"]=="number"):
                    FieldType=0
                else:
                    FieldType=0
                #logging.debug("Viewing Metadata from PreCog: {}" .format(i))
                #logging.debug('Adding Fields name :{}, dataType:{}' .format(FieldName, FieldType))
                table.fields.add(name=FieldName, dataType=FieldType)
            result = self.getTableData(url, vTable)
        else:
            result = []
        #logging.debug('Result: {}'.format(result))
        ###print(table)
        ###print(type(table))
        self.send_table_description(table, context)
        return result
   
    
    @staticmethod
    def getTableInfo (url):
       logging.info("In getTableInfo using url {}" .format(url))
       table_list = precog.get_tables(url)
       x = list(table_list[0].keys())
       results =[]
       for i in x:
            y = precog.get_table_information(i, url)[1]
            temp_li =[]
            for j in y:
                col_str = json.dumps(j)
                temp_li.append(col_str)
            column_str = ''.join(temp_li)
            result= [i, table_list[0][i]['name'], column_str]
            results.append(result)
            ###print(result)
       return results

    @staticmethod
    def getTableData(url, table_name):
       logging.info("In getTableDatausing url {} and tablename {}" .format(url, table_name))
       result = []
       table_id  = precog.get_table_id(table_name, url)
       #logging.debug('Table ID {}' .format(table_id[0]))
       token = precog.get_access_tokens(table_id[0],url)
       ###print(token[0].values())
       token_count = len(token[0]["accessTokens"])
       create_token_tuple = precog.create_token(url,table_id[0])
       ##print(create_token_tuple)
       ##print(precog.get_count_of_all_tokens(url))
       new_token = create_token_tuple[0]
       new_secret = create_token_tuple[1]
       response = create_token_tuple[2]
       result = precog.get_result_csv(url, new_secret)
       ##print(result[0])
       output_str = result[1]
       logging.debug("JRP Size of output_str {}" .format(len(output_str)))
       parsed_csv = precog.convert_csv(output_str)
       logging.debug("JRP Size of parsed_csv {}" .format(len(parsed_csv[0])))
       #print(type(parsed_csv))
       #print(parsed_csv[:10])
       resp_clean = precog.cleanup_token(new_token, table_id[0], url)
       logging.debug('Token Cleaned Resp: {}' .format(resp_clean))
       return parsed_csv[0]