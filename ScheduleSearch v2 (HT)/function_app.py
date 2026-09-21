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

@app.route(route="fetch_route",methods=["GET"])
def fetch_route(req: func.HttpRequest) -> func.HttpResponse:
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

@app.route(route="add_route", methods=['POST'])
def add_route(req: func.HttpRequest) -> func.HttpResponse:
    code = req.headers.get('code')
    
    e_code=os.environ.get('ACCESS_CODE')

    if code==e_code:
        table_service = TableServiceClient.from_connection_string(conn_str=storage_key)
        table_client = table_service.get_table_client("MasterTable")
        table_client2 = table_service.get_table_client("AirlineDetails")

        data1 = req.get_json()


        dep=data1["DEP"].upper()
        arr=data1["ARR"].upper()
        date3=data1["DATE"]
        
        api_key= os.environ["Serp_API2"]
        response = requests.get("https://serpapi.com/search.json?engine=google_flights&departure_id="+dep+"&arrival_id="+arr+"&gl=in&hl=en&currency=INR&type=2&outbound_date="+date3+"&show_hidden=true&adults=1&stops=1&api_key="+api_key)
        data2=response.json()
        best_flights = data2.get("best_flights", [])
        other_flights = data2.get("other_flights", [])
        all_flights = best_flights + other_flights

        rk=dep+arr+date3

        freq=len(all_flights)

        cheapest = min(all_flights, key=lambda f: f.get("price", float("inf")), default=None)

        if cheapest:
            cheapest_price = cheapest.get("price")
            cheapest_logo = cheapest.get("airline_logo")
            leg = cheapest.get("flights", [{}])[0]
            cheapest_airline = leg.get("airline")
            cheapest_flight_number = leg.get("flight_number")
        else:
            cheapest_price = cheapest_airline = cheapest_logo = cheapest_flight_number = None

        price_insights = data2.get("price_insights", {})
        lowest_price = price_insights.get("lowest_price")
        price_level = price_insights.get("price_level")
        price_history_json = json.dumps(price_insights.get("price_history", []))

        airports_list = data2.get("airports") or [{}]
        airports = airports_list[0]
        dep_image = (airports.get("departure") or [{}])[0].get("image")
        arr_image = (airports.get("arrival") or [{}])[0].get("image")


        new_entity={"PartitionKey":"Route",
                    "RowKey":rk,
                    "DEP":dep,
                    "ARR":arr,
                    "FREQ":freq,
                    "DATE":date3,
                    "PRICE_HISTORY":price_history_json,
                    "LOWEST_PRICE":lowest_price or 0,
                    "PRICE_LEVEL":price_level or "",
                    "CHEAPEST_PRICE":cheapest_price or 0,
                    "CHEAPEST_AIRLINE":cheapest_airline or "",
                    "CHEAPEST_AIRLINE_LOGO":cheapest_logo or "",
                    "CHEAPEST_FLIGHT_NUMBER":cheapest_flight_number or "",
                    "DEP_IMG":dep_image or "",
                    "ARR_IMG":arr_image or ""
                }

        for flight in all_flights:
            segment = flight["flights"][0]

            airline=segment["airline"]
            airline_logo=flight.get("airline_logo", "")
            airplane=segment["airplane"]
            rk2=segment["flight_number"]

            dep2=segment["departure_airport"]["time"]
            arr2=segment["arrival_airport"]["time"]


            new_entity2 = {"PartitionKey":rk,
                            "RowKey":rk2,
                            "AIRLINE":airline,
                            "AIRCRAFT":airplane,
                            "DEPT":dep2,
                            "ARRT":arr2,
                            "AIRLINE_LOGO":airline_logo}
            table_client2.create_entity(new_entity2)
            
        
        try:
            table_client.create_entity(new_entity)
        except ResourceExistsError:
            return func.HttpResponse("This route and date is already being tracked", status_code=409)

        message = {
            "senderAddress": "DoNotReply@b69c3249-d05b-47d9-a9a3-9fc4b60755d6.azurecomm.net",
            "recipients": {
                "bcc": [
                    {"address": "autoalpha72110@gmail.com"}
                ]
            },
            "content": {
                "subject": "New Prompt Added",
                "plainText": (
                    f"A new prompt has been added on the app, for:\n\n"
                    f"Route: {dep} - {arr}\n"
                    f"Frequency (as on date of addition): {freq}\n"
                    f"Date: {date3}"
                ),
            },
        }
        poller = client.begin_send(message)

        return func.HttpResponse("New Prompt Added Successfully",status_code=201)
    else:
        return func.HttpResponse("Access denied", status_code=403)
    
@app.route(route="delete_route",methods=["DELETE"])
def delete_route(req: func.HttpRequest) -> func.HttpResponse:
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
                "bcc": [
                            {"address": "autoalpha72110@gmail.com"}
                            
                        ]
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
