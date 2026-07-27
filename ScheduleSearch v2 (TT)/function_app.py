import os
import json
import logging
import requests
import azure.functions as func
from datetime import date
from azure.communication.email import EmailClient
from azure.core.credentials import AzureKeyCredential
from azure.data.tables import TableServiceClient


#For Azure Table
storage_key=os.environ.get('AzureWebJobsStorage')
#For ACS
credential = AzureKeyCredential(os.environ["ACS_EMAIL_KEY"])
endpoint=os.environ["ACS_ENDPOINT"]
client = EmailClient(endpoint,credential)



app = func.FunctionApp()


def emailchange(dep,arr,old,new,date2):
    message = {
            "senderAddress": "DoNotReply@b69c3249-d05b-47d9-a9a3-9fc4b60755d6.azurecomm.net",
            "recipients": {
                "to": [{"address": "autoalpha72110@gmail.com"},{"address":"rumaizankhan123456@gmail.com"},{"address":"arfathahmed380@gmail.com"}]
            },
            "content": {
                "subject": f'Frequency changing on {dep} - {arr}',
                "plainText": f'Frequency changing on\n\nRoute:{dep} - {arr}\nOld Frequency: {old}x daily\nNew Frequency: {new}x daily\nDate: {date2}',
            },
            
        }
    logging.info(f"Email sent for frequency change on {dep}-{arr}")
    poller = client.begin_send(message)

def emaildate(dep,arr):
    message = {
            "senderAddress": "DoNotReply@b69c3249-d05b-47d9-a9a3-9fc4b60755d6.azurecomm.net",
            "recipients": {
                "to": [{"address": "autoalpha72110@gmail.com"},{"address":"rumaizankhan123456@gmail.com"},{"address":"arfathahmed380@gmail.com"}]
            },
            "content": {
                "subject": f'Date expired for route',
                "plainText": f'Date expired for {dep} - {arr} today.\n\nThe route has been dropped from database.',
            },
            
        }
    logging.info(f"Email sent for date change on {dep}-{arr}")
    poller = client.begin_send(message)

def emailerror():
    message = {
            "senderAddress": "DoNotReply@b69c3249-d05b-47d9-a9a3-9fc4b60755d6.azurecomm.net",
            "recipients": {
                "to": [{"address": "autoalpha72110@gmail.com"}]
            },
            "content": {
                "subject": f'API Fault (IN)',
                "plainText": f'API fault detected, please check immediately',
            },
            
        }
    logging.info(f"Email sent for error")
    poller = client.begin_send(message)

def search (dep_id,arr_id, date3):
    api_key= os.environ["SERPAPI_KEY"]
    response = requests.get("https://serpapi.com/search.json?engine=google_flights&departure_id="+dep_id+"&arrival_id="+arr_id+"&gl=in&hl=en&currency=INR&type=2&outbound_date="+date3+"&show_hidden=true&adults=1&stops=1&api_key="+api_key)

    if response.status_code != 200:
        emailerror()
        return None

    data=response.json()

    best_flights = data.get("best_flights", [])
    other_flights = data.get("other_flights", [])

    if best_flights or other_flights:
        return(len(best_flights)+len(other_flights))
    else:
        return (0)

def dictcheck():
    table_service = TableServiceClient.from_connection_string(conn_str=storage_key)
    table_client = table_service.get_table_client("MasterTable")

    entities=table_client.list_entities()
    for entity in entities:
        pk=entity["PartitionKey"]
        rk=entity["RowKey"]
        dep=entity["DEP"]
        arr=entity["ARR"]
        date1=entity["DATE"]
        freq=int(entity["FREQ"])

        newfreq=search(dep,arr,date1)

        if newfreq!=freq and newfreq!=None:
            entity["FREQ"] = newfreq
            table_client.update_entity(entity)
            emailchange(dep,arr,freq,newfreq,date1)

        if date.fromisoformat(date1) <= date.today():
            emaildate(dep,arr)
            table_client.delete_entity(partition_key=pk, row_key=rk)


@app.timer_trigger(schedule="0 30 3 * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Starting search')
    dictcheck()

    logging.info('Python timer trigger function executed.')