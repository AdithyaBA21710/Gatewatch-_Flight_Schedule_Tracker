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


def emailfreq(dep,arr,old,new,date2):
    if old<new:
        nameplate="increasing"
    else:
        nameplate="decreasing"
    message = {
            "senderAddress": "DoNotReply@b69c3249-d05b-47d9-a9a3-9fc4b60755d6.azurecomm.net",
            "recipients": {
                "bcc": [
                            {"address": "autoalpha72110@gmail.com"}
                        ]
            },
            "content": {
                "subject": f'Frequency is {nameplate} on {dep} - {arr}',
                "plainText": f'Frequency is {nameplate} on\n\nRoute:{dep} - {arr}\nOld Frequency: {old}x daily\nNew Frequency: {new}x daily\nDate: {date2}',
            },
            
        }
    logging.info(f"Email sent for frequency change on {dep}-{arr}")
    poller = client.begin_send(message)

def emailprice(dep,arr,old_price,new_price,old_airline,new_airline,old_logo,new_logo):
    if old_price<new_price:
        nameplate="increased"
    else:
        nameplate="decreased"
    message = {
            "senderAddress": "DoNotReply@b69c3249-d05b-47d9-a9a3-9fc4b60755d6.azurecomm.net",
            "recipients": {
                "bcc": [
                            {"address": "autoalpha72110@gmail.com"}
                        ]
            },
            "content": {
                "subject": f'Price has {nameplate} changing on {dep} - {arr}',
                "plainText": f'Price has {nameplate} on\n\nRoute:{dep} - {arr}\nOld Price: {old_price}\nNew Price: {new_price}',
            },
                
        }
    logging.info(f"Email sent for frequency change on {dep}-{arr}")
    poller = client.begin_send(message)

def emaildate(dep,arr):
    message = {
            "senderAddress": "DoNotReply@b69c3249-d05b-47d9-a9a3-9fc4b60755d6.azurecomm.net",
            "recipients": {
                "bcc": [
                            {"address": "autoalpha72110@gmail.com"}
                        ]
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

"""
def search1 (dep_id,arr_id, date3):
    
    
"""
    
def dictcheck():
    table_service = TableServiceClient.from_connection_string(conn_str=storage_key)
    table_client = table_service.get_table_client("MasterTable")
    table_client2 = table_service.get_table_client("AirlineDetails")

    api_key= os.environ["SERPAPI_KEY"]

    entities=table_client.list_entities()
    for entity in entities:
        pk1=entity["PartitionKey"]
        rk1=entity["RowKey"]
        dep=entity["DEP"]
        arr=entity["ARR"]
        date1=entity["DATE"]
        freq=int(entity["FREQ"])
        cheapest_price=int(entity["CHEAPEST_PRICE"])
        cheapest_airline=entity["CHEAPEST_AIRLINE"]
        cheapest_airline_logo=entity["CHEAPEST_AIRLINE_LOGO "]

        
        response = requests.get("https://serpapi.com/search.json?engine=google_flights&departure_id="+dep+"&arrival_id="+arr+"&gl=in&hl=en&currency=INR&type=2&outbound_date="+date1+"&show_hidden=true&adults=1&stops=1&api_key="+api_key)
        
        if response.status_code != 200:
            emailerror()
            return None
        
        data=response.json()
        
        best_flights = data.get("best_flights", [])
        other_flights = data.get("other_flights", [])
        all_flights = best_flights + other_flights

        new_freq=len(all_flights)

        if freq!=new_freq:
            entity["FREQ"]=new_freq
            table_client.update_entity(entity)
            emailfreq(dep,arr,freq,new_freq,date1)

        cheapest = min(all_flights, key=lambda f: f.get("price", float("inf")), default=None)
        cheapest_price2 = cheapest.get("price")
        cheapest_logo2 = cheapest.get("airline_logo")
        leg = cheapest.get("flights", [{}])[0]
        cheapest_airline2 = leg.get("airline")
        cheapest_flight_number2 = leg.get("flight_number")
        price_insights = data.get("price_insights", {})
        lowest_price2 = price_insights.get("lowest_price")
        price_level2 = price_insights.get("price_level")
        price_history_json2 = json.dumps(price_insights.get("price_history", []))

        if cheapest_airline!=cheapest_airline2 or cheapest_price!=cheapest_price2:
            entity["PRICE_HISTORY"]=price_history_json2
            entity["LOWEST_PRICE"]=lowest_price2
            entity["PRICE_LEVEL"]=price_level2
            entity["CHEAPEST_PRICE"]=cheapest_price2
            entity["CHEAPEST_AIRLINE"]=cheapest_airline2
            entity["CHEAPEST_AIRLINE_LOGO"]=cheapest_logo2
            entity["CHEAPEST_FLIGHT_NUMBER"]=cheapest_flight_number2
            table_client.update_entity(entity)
            emailprice(dep,arr,cheapest_price,cheapest_price2,cheapest_airline,cheapest_airline2,cheapest_airline_logo,cheapest_logo2)

        entity2 = table_client2.get_entity()

        if date.fromisoformat(date1) <= date.today():
            emaildate(dep,arr)
            table_client.delete_entity(partition_key=pk1, row_key=rk1)
            #table_client2.delete_entity()


@app.timer_trigger(schedule="0 30 3 * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Starting search')
    dictcheck()

    logging.info('Python timer trigger function executed.')