import os, sys
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PARENT_DIR, 'generated'))
sys.path.append(os.path.join(PARENT_DIR, 'helper_functions'))
import logging
import logging.config
import python_finance, qlist
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
        logging.info("python_finance Function {} called" .format(script))
        #If User name and Password Present Remove Username and Password and Pass only function name
        if(script.find('(') !=-1):
            index=script.index('(')
            Arguments = script[index:].strip(')(').split(',') 
            fName = script[:index]
            provider='yahoo'
        else:
            raise ValueError('Incorrect Formating of Function')
        
        if (script.find('get_ticker_data') !=-1):
            ticker = Arguments[0]
            start_date=Arguments[1]
            end_date=Arguments[2]
            result = self.get_ticker_data(ticker, start_date, end_date)
            logging.debug("result type  : {} data : {} " .format(type(result), result))
            converted = qlist.convert_df_list(result)
            logging.debug("converted type JRP : {} columns : {} data :{} " .format(type(converted[0]), converted[0], converted[1]))
            table.name = Arguments[0] +'- ticker_data'
            converted[0].insert(0, 'Ticker')
            for i in converted[0]:
                logging.debug('This is i {}'  .format(i))
                #if (i!='Date'):
                    #if (i!='Ticker'):
                 #       FieldName = ticker+' '+i
                    #else:
                #        FieldName = i
               # else:
                FieldName= i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            for x in converted[1]:
                x.insert(0, ticker.strip())
            result = converted[1]
            logging.debug("result type  : {} data : {} " .format(type(result), result))
            for x in result:
                logging.debug("x type  : {} data : {} " .format(type(x), x))
        elif (script.find('get_tickers') !=-1):
            tickers = Arguments[: len(Arguments) - 3]
            Arguments = Arguments[len(Arguments) - 3:]
            start_date=Arguments[0]
            end_date=Arguments[1]
            attrib = Arguments[2]
            logging.debug("get tickers - tickers: {} Arguments {} start_date : {} end_date :{} attrib :{} " .format(tickers, Arguments, start_date, end_date, attrib))
            result = self.get_tickers(tickers, start_date, end_date, attrib)
            converted = qlist.convert_df_list(result)
            table.name= ' '.join([str(elem) for elem in tickers]) + '-' + attrib + '-Data'
            logging.debug("column  {}" .format(converted[0]))
            x = 1
            for i in converted[0]:
                if(i!='Date'):
                    FieldName = 'Stock '+str(x)+' '+attrib
                    x += 1
                else:
                    FieldName= i    
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            result= converted[1]
            logging.debug("result {}" .format(result))
        elif (script.find('get_Percent_change') !=-1):
            tickers = Arguments[: len(Arguments) - 3]
            Arguments = Arguments[len(Arguments) - 3:]
            start_date=Arguments[0]
            end_date=Arguments[1]
            attrib = Arguments[2]
            logging.debug("get_Percent_change - tickers: {} Arguments {} start_date : {} end_date :{} attrib :{} " .format(tickers, Arguments, start_date, end_date, attrib))
            result = self.get_Percent_change(tickers, start_date, end_date, attrib)
            logging.debug("result - type: {} data: {}" .format(type(result), result))
            converted = qlist.convert_df_list(result)
            table.name= ' '.join([str(elem) for elem in tickers]) + '-' + attrib + '- Percent Change'
            #table.name= 'Percent Change'
            x =1
            logging.debug("column  {}" .format(converted[0]))
            for i in converted[0]:
                if(i!='Date'):
                    FieldName = 'Stock '+str(x)+'-Percent Change'
                    x += 1
                else:
                    FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            result= converted[1]
            logging.debug("result {}" .format(result))
        elif (script.find('get_Mean_Daily_Return') !=-1):
            tickers = Arguments[: len(Arguments) - 3]
            Arguments = Arguments[len(Arguments) - 3:]
            start_date=Arguments[0]
            end_date=Arguments[1]
            attrib = Arguments[2]
            logging.debug("get_Mean_Daily_Return - tickers: {} Arguments {} start_date : {} end_date :{} attrib :{} " .format(tickers, Arguments, start_date, end_date, attrib))
            result = self.get_Mean_Daily_Return(tickers, start_date, end_date, attrib)
            logging.debug("result - type: {} data: {} name: {}" .format(type(result), result, result.name))
            df_result = result.to_frame()
            logging.debug("df_result - type: {} data: {}" .format(type(df_result), df_result))
            temp_dict = df_result.to_dict("split")
            data =[]
            i =0
            for y in temp_dict['data']:
                y =  ['%.6f' % z for z in y]
                y.insert(0,temp_dict['index'][i].strip())
                data.append(y)
                i +=1
            table.name= ' '.join([str(elem) for elem in tickers]) + '-' + attrib + '- Mean Daily Returns'
            columns = ['Ticker' ,'Mean_Daily_Return']
            logging.debug("column  {}" .format(columns))
            for i in columns:
                FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            logging.debug("data type: {} data: {}" .format(type(data), data))
            result=data
            logging.debug("result {}" .format(result))
        elif (script.find('get_Cov_Matrix') !=-1):
            tickers = Arguments[: len(Arguments) - 3]
            Arguments = Arguments[len(Arguments) - 3:]
            start_date=Arguments[0]
            end_date=Arguments[1]
            attrib = Arguments[2]
            logging.debug("get_Cov_Matrix - tickers: {} Arguments {} start_date : {} end_date :{} attrib :{} " .format(tickers, Arguments, start_date, end_date, attrib))
            result = self.get_Cov_Matrix(tickers, start_date, end_date, attrib)
            logging.debug("result - type: {} data: {} " .format(type(result), result))
            converted = qlist.convert_df_list_cov(result)
            table.name= ' '.join([str(elem) for elem in tickers]) + '-' + attrib + '- Cov Matrix'
            logging.debug("column  {}" .format(converted[0]))
            for i in converted[0]:
                FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            result= converted[1]
            logging.debug("result {}" .format(result))
        elif (script.find('get_Simulated_Random_Portfolios') !=-1):
            logging.debug("Inside Else Block JRP ")
            tickers = Arguments[: len(Arguments) - 5]
            Arguments = Arguments[len(Arguments) - 5:]
            start_date=Arguments[0]
            end_date=Arguments[1]
            attrib = Arguments[2]
            num_portfolios=Arguments[3]
            rf=Arguments[4]
            logging.debug("get_Simulatd_Random_Portfolios - tickers: {} Arguments {} start_date : {} end_date :{} attrib :{} num_portfolios :{} rf : {} " .format(tickers, Arguments, start_date, end_date, attrib, num_portfolios, rf))
            mean_returns = self.get_Mean_Daily_Return(tickers, start_date, end_date, attrib)
            logging.debug("mean_returns - type: {} data: {} " .format(type(mean_returns), mean_returns))
            cov = self.get_Cov_Matrix(tickers, start_date, end_date, attrib)
            logging.debug("cov - type: {} data: {} " .format(type(cov), cov))
            result = self.get_Simulated_Random_Portfolios(num_portfolios, mean_returns, cov, rf,tickers)
            logging.debug("result - type: {} data: {} " .format(type(result), result[1]))
            converted = qlist.convert_df_list_sim(result[0])
            table.name= ' '.join([str(elem) for elem in tickers]) + '-' +'- Simulated_Random_Portfolios'
            logging.debug("column  {}" .format(converted[0]))
            x=1
            for i in converted[0]:
                FieldName = i
                FieldType=0
                table.fields.add(name=FieldName, dataType=FieldType)
            result= converted[1]
            logging.debug("result {}" .format(result))
        else:
            result = []

        self.send_table_description(table, context)
        return result


    @staticmethod
    def get_tickers(tickers, start, end, attrib):
        return python_finance.get_tickers(tickers, start, end, attrib)
    @staticmethod
    def get_ticker_data(tickers, start, end):
        return python_finance.get_ticker_data(tickers, start, end)
    @staticmethod
    def get_Percent_change(ticker, start, end, attrib):
        return python_finance.get_Percent_change(ticker, start, end, attrib)
    @staticmethod
    def get_Mean_Daily_Return(ticker, start, end, attrib):
        return python_finance.get_Mean_Daily_Return(ticker, start, end, attrib)
    @staticmethod
    def get_Cov_Matrix(ticker, start, end, attrib):
        return python_finance.get_Cov_Matrix(ticker, start, end, attrib)
    @staticmethod
    def calc_portfolio_perf(weights, mean_returns, cov, rf):
        return python_finance.calc_portfolio_perf(weights, mean_returns, cov, rf)
    @staticmethod
    def get_Simulated_Random_Portfolios(num_portfolios, mean_returns, cov, rf,tickers):
        return python_finance.simulate_random_portfolios(num_portfolios, mean_returns, cov, rf,tickers)