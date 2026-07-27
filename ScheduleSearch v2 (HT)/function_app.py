import os
import logging
import json
import requests
import azure.functions as func
from azure.data.tables import TableServiceClient
from azure.communication.email import EmailClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceExistsError

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

#For Azure Table
storage_key=os.environ.get('AzureWebJobsStorage')
#For ACS
credential = AzureKeyCredential(os.environ["ACS_EMAIL_KEY"])
endpoint=os.environ["ACS_ENDPOINT"]
client = EmailClient(endpoint,credential)

@app.route(route="http_get",methods=["GET"])
def http_get(req: func.HttpRequest) -> func.HttpResponse:
    table_service = TableServiceClient.from_connection_string(conn_str=storage_key)
    table_client = table_service.get_table_client("MasterTable")

    routelist=[]

    entities=table_client.list_entities()
    for entity in entities:
        routelist.append({"PartitionKey": entity["PartitionKey"],
                    "RowKey": entity["RowKey"],
                    "DEP":entity["DEP"],
                    "ARR":entity["ARR"],
                    "FREQ":entity["FREQ"],
                    "DATE":entity["DATE"]})

    return func.HttpResponse(json.dumps(routelist), status_code=200)


@app.route(route="http_post", methods=['POST'])
def http_post(req: func.HttpRequest) -> func.HttpResponse:
    code = req.headers.get('code')
    
    e_code=os.environ.get('ACCESS_CODE')

    if code==e_code:
        table_service = TableServiceClient.from_connection_string(conn_str=storage_key)
        table_client = table_service.get_table_client("MasterTable")

        data1 = req.get_json()

        
        dep=data1["DEP"]
        arr=data1["ARR"]
        date3=data1["DATE"]
        
        api_key= os.environ["Serp_API2"]
        response = requests.get("https://serpapi.com/search.json?engine=google_flights&departure_id="+dep+"&arrival_id="+arr+"&gl=in&hl=en&currency=INR&type=2&outbound_date="+date3+"&show_hidden=true&adults=1&stops=1&api_key="+api_key)
        data2=response.json()
        best_flights = data2.get("best_flights", [])
        other_flights = data2.get("other_flights", [])

        freq=len(best_flights)+len(other_flights)
        rk=data1["DEP"].upper()+data1["ARR"].upper()+data1["DATE"]

        new_entity={"PartitionKey":"Route",
                    "RowKey":rk,
                    "DEP":data1["DEP"].upper(),
                    "ARR":data1["ARR"].upper(),
                    "FREQ":freq,
                    "DATE":data1["DATE"]}
        
        try:
            table_client.create_entity(new_entity)
        except ResourceExistsError:
            return func.HttpResponse("This route and date is already being tracked", status_code=409)

        message = {
            "senderAddress": "DoNotReply@b69c3249-d05b-47d9-a9a3-9fc4b60755d6.azurecomm.net",
            "recipients": {
                "to": [{"address": "autoalpha72110@gmail.com"},{"address":"rumaizankhan123456@gmail.com"},{"address":"arfathahmed380@gmail.com"}]
            },
            "content": {
                "subject": f'New Prompt Added',
                "plainText": f'A new prompt has been added on the app, for:\n\nRoute: {dep}-{arr}\nFrequency (as on date of addition): {freq}\nDate: {date3}',
            },
            
        }
        poller = client.begin_send(message)

        return func.HttpResponse("New Prompt Added Successfully",status_code=201)
    else:
        return func.HttpResponse("Access denied", status_code=403)
    
@app.route(route="http_del",methods=["DELETE"])
def http_del(req: func.HttpRequest) -> func.HttpResponse:
    code = req.headers.get('code')
    
    e_code=os.environ.get('ACCESS_CODE')

    if code==e_code:
        table_service = TableServiceClient.from_connection_string(conn_str=storage_key)
        table_client = table_service.get_table_client("MasterTable")

        partition_key = req.params.get("PartitionKey")
        row_key = req.params.get("RowKey")

        data=table_client.get_entity(partition_key=partition_key,row_key=row_key)
        dep=data["DEP"]
        arr=data["ARR"]
        freq=data["FREQ"]
        date=data["DATE"]

        message = {
            "senderAddress": "DoNotReply@b69c3249-d05b-47d9-a9a3-9fc4b60755d6.azurecomm.net",
            "recipients": {
                "to": [{"address": "autoalpha72110@gmail.com"},{"address":"rumaizankhan123456@gmail.com"},{"address":"arfathahmed380@gmail.com"}]
            },
            "content": {
                "subject": f'Prompt Deleted',
                "plainText": f'A prompt has been deleted from the app, for:\n\nRoute: {dep}-{arr}\nFrequency (as on date of deletion): {freq}\nDate: {date}',
            },
            
        }
        poller = client.begin_send(message)

        table_client.delete_entity(partition_key=partition_key, row_key=row_key)


        return func.HttpResponse("Sucessfully Deleted",status_code=200)
    else:
        return func.HttpResponse("Access Denied",status_code=403)
