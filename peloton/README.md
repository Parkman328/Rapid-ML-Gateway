[QRAG Logo](../images/sagemaker.png)

# Integrating Qlik with Databricks


## Qlik Sagemaker Business Flow


## Architectural Diagram

![Technical High Level]
## Installation and Setup

Databricks Setup

AWS Component Setup

QRAG/API Server Setup

**Qlik Server Setup**

Setup Qlik Server to use Analytical Connection in the QMC

1. Log onto QMC
2. Create Analytics connections
   Detailed instructions can be found [here](https://help.qlik.com/en-US/sense-admin/June2020/Subsystems/DeployAdministerQSE/Content/Sense_DeployAdminister/QSEoW/Administer_QSEoW/Managing_QSEoW/create-analytic-connection.htm).
3. For Name use Sagemaker or somthing that can easily identify this module inside Qlik
4. For Port Use 50058 or 50051 - 50059

**_The Current integration has been tested on Qlik Sense Server 2020 Patch 2
qliksenseserver:13.72.5_**

#### 1. Defining [functions.json]

Basis of this implementation uses functions.json file from **Qlik SSE integration** (Please see reference [here](https://github.com/qlik-oss/server-side-extension)) you must use functions.json to expose integrated ML functions. The advantage of this implementation is natural feel of integration Qlik users.

Below is sample definition of function.json file located in sagemaker directiory/module.
![functions.json](../images/functions_json.png)

##### FunctionDefinition -Sagemaker

The definition of a function, which informs the Qlik engine how to use it.

| Id | number | optional | A unique ID number for the function, set by the plugin, to be used in calls from the Qlik engine to the plugin. |
| Name | string | optional | The name of the function. |
| Type | Function Type | optional | We will define this as value 2(Tensor) which allows multiple rows in and multiple rows out. |
| QRAP_Type | Qlik Rapid API Function Type | optional | We will definte this as type of Function i.e. rest_single_ws |
| ReturnType | DataType | optional | The return type of the function. For Sagemaker we will define all return types as 0(string). (Qlik will be able manipulate the String to Int with in Qlik Engine. |
| Params | Parameters | repeated | The parameters the function takes. For Sagemaker preffered param is str1:0 where a single row or file has comma delimited string of all defined params. |

2.Defining [qrag.ini]  
 In sagemaker model of QRAG;**_qrag.ini_** is the file that defines your end points. The name of your functions defined in [functions.json has] to correspond with section defined in qrag.ini.

qrag.ini file location is current module/config/directory. i.e. ./sagemaker/config/qrag.ini

Below is sample definition of function.json file located in sagemaker directiory/module.  
Please note that __Name__ field and headers correspond.

![functions.json](../images/sagemaker-qrag.jpeg) 

QRAG will determinte the functions variable input such as url, username, token and cache(For Websocket we also need route defined)

3.Restarting Services
After functions.json and qrag.ini is set please restart Qlik Engine Services

## Testing

Up to 3000 row Bulk Scoring/Single Scoring Real Time
1 million row Batch Scoring via Qlik Script
12 users on App using Real Time Scoring Interface

## Trouble Shooting and Logs

Logs are located logs parent folder of QRAG and logger.cofing file determines verbosity of logs.

## References
