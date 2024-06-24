import json
import pandas as pd
import boto3
import io
from rapidfuzz import process, fuzz
													  
import numpy as np
import itertools
import difflib
		   
import re
from datetime import datetime
import datetime as dt
import logging
from config import BUCKET_NAME, LAMBDA_NAME, REGION_NAME, STUDY_CONTACT_TABLE_NAMES
logger = logging.getLogger()
logger.setLevel(logging.INFO)



def batch(iterable, n=1000):
    '''
    Creates a batch iterable.
    iterable : the list to iterate on
    n = batch size of the iterable
    '''
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]
        
        
def user_dashboard_access(user_id):
    """ Function takes in a user_id and queries the  USER_DASHBOARD_ACCESS 
    table to fetch the list of dashboard a user has access to. 
    Returns None incase user doesn't have access to any dashboard"""
    
    logger.info(f"Func: user_dashboard_access \n user_id: {user_id}")
    
    query = "Select dashboards from USER_DASHBOARD_ACCESS WHERE lower(user_id) = '{}'".format(user_id)
    
    logger.info(f"Func: user_dashboard_access \n query: {query}")
    invokeLam = boto3.client("lambda", region_name=REGION_NAME)
    payload ={"Query":query}
    response = invokeLam.invoke(FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(payload))
    response = json.loads(response['Payload'].read())
    logger.info(f"Response:  user_dashboard_access \n response: {response}")
    if response:
        return response[0][0].split(", ")
    else:
        return response 
        
        
def delegate(session_attributes, slots):
    logger.info(f"Func: delegate \n session_attributes: {session_attributes} \n slots : {slots}")
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    """
    Elicits the slot to a particular intent with a particular message.
    """
    logger.info(f"Func: elicit_slot \n session_attributes: {session_attributes} \n intent_name: {intent_name} \n slots: {slots} \n slot_to_elicit: {slot_to_elicit} \n message: {message}")
    session_attributes['slot_elicited'] = slot_to_elicit
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': {'contentType': 'PlainText', 'content': message}
        }
    }


def elicit_slot_buttons(session_attributes, intent_name, slots, slot_to_elicit, message, response_card):
																																																									 

    """
    Elicits the slot to a particular intent with an optional set of options which should be displayed as buttons.
    """
    logger.info(f"Func: elicit_slot_buttons \n session_attributes: {session_attributes} \n intent_name: {intent_name} \n slots: {slots} \n slot_to_elicit: {slot_to_elicit} \n message: {message} \n response_card: {response_card}")

    session_attributes['slot_elicited'] = slot_to_elicit

    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': {'contentType': 'PlainText', 'content': message},
            'responseCard': response_card
        }
    }


def build_response_card_dict(title, subtitle, options):
    logger.info(f"Func: build_response_card_dict \n title: {title} \n subtitle : {subtitle} \n options: {options}")

    """
    Build a responseCard with a title, subtitle, and an optional set of options which should be displayed as buttons.
    """

    buttons = []
    listdict = []
    if options is not None:
        for i in range(len(options)):
            buttons.append(options[i])
            if (i+1) % 5 == 0:
                listdict.append(
                    {'title': title, 'subTitle': subtitle, 'buttons': buttons})
                buttons = []
        if len(buttons) != 0:
            listdict.append(
                {'title': title, 'subTitle': subtitle, 'buttons': buttons})

    return {
        'contentType': 'application/vnd.amazonaws.card.generic',

        'genericAttachments': listdict
    }


def build_response_card(options, title=None, subtitle=None, include_no=False):
    logger.info(f"Func: build_response_card \n options: {options} \n title: {title} \n subtitle : {subtitle} \n include_no: {include_no}")
    """
    Build a responseCard with a title, subtitle, and an optional set of options which should be displayed as buttons.
    """
    if include_no:
        options.append("None of these")
    options = [{'text': i[:49], 'value':i[:49]} for i in options]
    buttons = []
    listdict = []
    if options is not None:
        for i in range(len(options)):
            buttons.append(options[i])
            if (i+1) % 5 == 0:
                listdict.append(
                    {'title': title, 'subTitle': subtitle, 'buttons': buttons})
                buttons = []
        if len(buttons) != 0:
            listdict.append(
                {'title': title, 'subTitle': subtitle, 'buttons': buttons})

    return {
        'contentType': 'application/vnd.amazonaws.card.generic',

        'genericAttachments': listdict
    }


def just_close(session_attributes, fulfillment_state, message):
    logger.info(f"Func: just_close \n session_attributes: {session_attributes} \n fulfillment_state : {fulfillment_state} \n message: {message}")

    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': {'contentType': 'PlainText', 'content': message}
        }
    }


def close(session_attributes, fulfillment_state, message):
    logger.info(f"Func: close \n session_attributes: {session_attributes} \n fulfillment_state: {fulfillment_state} \n message : {message}")

    """
      This function accepts three parameters- session_attributes, fulfillment_state, message.
      This function is realted to Metric value option.
      control passes to this function when user is done with all selection of Metric names and now user needs to enter parrticular query to get response.
    
    """
    from_intent = try_ex(lambda: session_attributes['from_intent'])
    if from_intent:
        session_attributes['status'] = 'closing from metric flow'
        response_card = build_response_card(
            ["Yes", "No"], title=None, subtitle=None)
        response = {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': fulfillment_state,
                'message': {'contentType': 'PlainText', 'content': message + "<br>You can filter the metric value using the below parameters:<br>- Study Number<br>- Site Number<br>- Country<br>- Time Period<br>( Note : Time period is available for metrics related to Data Management Tool Report only )  <br> <br> Please click Yes to Continue or No to Exit"},
                'responseCard': response_card
            }
        }

    else:
        session_attributes['status'] = 'closing'
        response_card = build_response_card(
            ["Yes", "No"], title=None, subtitle=None)
        response = {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': fulfillment_state,
                'message': {'contentType': 'PlainText', 'content': message + "<br>Is there anything else that you want assistance with? "},
                'responseCard': response_card
            }
        }

    return response


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except (KeyError, TypeError) as e:
        return None


def read_excel(name, sheet):

    """
    It will take two parameter -  name and sheet and corresponding data frame will be returned
    """
	
    logger.info(f"Func: read_excel \n name: {name} \n sheet: {sheet} ")
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=name)
    logger.info(f"Func: read_excel \n name: {name} \n sheet: {sheet} Reading data from excel")
    try:							
        data = pd.read_excel(io.BytesIO(obj['Body'].read()), index_col=None, sheet_name=sheet)
    except Exception as e:
        logger.info(f"Func: read_excel Error : {e}")
    logger.info(f"Func: read_excel \n name: {name} \n sheet: {sheet} data read")
    return data
    
def rapidfuzz_matches(key, choices, threshold = 80, limit = 3, return_type = False, choice_verbose = True):
    """
    Function accepts a keyword and a list of choices using the Fuzz.Wratio
    Input:
        key : the keyword 
        choices : list of choices to be compared
        threshold : threshold of the comparison
        limit : number of best choices to be returned
        return_type : False (bool) to return just matched choice
                      'index' to return just indexes
                      'both' to return both matches and indexes
    Output:
        metric_matches : list of items matched based on the threshold
    """
    if choice_verbose:
        logger.info(f"Func: rapidfuzz_matches \n key: {key} \n choices: {choices} \n threshold : {threshold} \n limit: {limit} \n return_type {return_type}")
    else:
        logger.info(f"Func: rapidfuzz_matches \n key: {key} \n len of choices: {len(choices)} \n threshold : {threshold} \n limit: {limit} \n return_type {return_type}")
    
    matches = process.extract(key, choices, scorer=fuzz.WRatio, limit=limit)
    if return_type == 'index':
        matches = [ index  for match, thres, index in matches if thres > threshold]
    elif return_type == 'both':
        matches = [ (match, index)  for match, thres, index in matches if thres > threshold]
    elif return_type == 'match_thres':
        matches = [ (match, thres)  for match, thres, index in matches if thres > threshold]
    else:
        matches = [ match  for match, thres, index in matches if thres > threshold]
    logger.info(f"Func: rapidfuzz_matches \n key: {key} \n matches: {matches}  ")

    return matches


def fetch_meeting_flow(table_name, slots, column_name):
    logger.info(f"Func: fetch_meeting_flow \n table_name: {table_name} \n slots: {slots} \n column_name : {column_name}")

    """
    This function take three parameters
    table_name of the metric name
    column_name, the column in database where the value present
    Slots, the value you want to validate
    This function works for Studies Meeting Plan and Country Meeting Plan.
    
    """
    query = "select LISTAGG(DISTINCT {},',') WITHIN GROUP (ORDER BY YEAR) from {} where ".format(
        column_name, table_name)
    filters = ""
    for k, v in slots.items():
        if v:
            k = k.replace("year_information", "year")
            k = k.replace("month_information", "month")
            k = k.replace("study_information", "study_type")
            query += " upper("+k+") = '"+v.upper() + "' and  "
            filters += "<strong>" + \
                k.replace("_", " ").title()+"</strong>" + " - " + v+"<br><br>"
    query = (query[:-5])
    logger.info(f"Func: fetch_meeting_flow \n query: {query} ")

    invokeLam = boto3.client("lambda", region_name=REGION_NAME)
    payload = {"Query": query}
    response = invokeLam.invoke(
        FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(payload))
    k = json.loads(response['Payload'].read())[0][0]
    logger.info(f"Func: fetch_meeting_flow \n query: {query} \n k: {k} ")
    return k


def fetch_enrolment_flow(table_name, study_number, slots, column_name):
    logger.info(f"Func: fetch_enrolment_flow \n table_name: {table_name} \n study_number: {study_number} \n slots: {slots} \n column_name : {column_name}")

    """
    This function take four parameters
    table_name of the metric name
    column_name, the column in database where the value present
    Slots, the value you want to validate
    study_number, validates the study number which user has entered
    This function works % to Plan Enrollment & Activation
    """
    #table_name = "EDT_SAMPLE_TABLE"
    query = "select LISTAGG(DISTINCT {},',') WITHIN GROUP (ORDER BY STUDY_NUMBER) from {} where STUDY_NUMBER ='{}' and  ".format(
        column_name, table_name, study_number)
    filters = ""
    for k, v in slots.items():
        if v:
            k = k.replace("year_information", "year")
            k = k.replace("month_information", "month")
            query += " upper("+k+") = '"+v.upper() + "' and  "
            #filters += k.replace("_"," ").title() +" - "+ v+"<br>"
            filters += "<strong>" + \
                k.replace("_", " ").title()+"</strong>" + " - " + v+"<br><br>"
    query = (query[:-5])
    logger.info(f"Func: fetch_enrolment_flow \n query: {query} ")

    invokeLam = boto3.client("lambda", region_name=REGION_NAME)
    payload = {"Query": query}
    response = invokeLam.invoke(
        FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(payload))
    return json.loads(response['Payload'].read())[0][0]


def validation_query_creator(table_name, validate_column, validate_value):
    logger.info(f"Func: validation_query_creator \n table_name: {table_name} \n validate_column: {validate_column} \n validate_value: {validate_value} ")

    """
    This function take three parameters
    table_name of the metric name
    validate_column, the column in database where the value present
    validate_value the value you want to validate
    """
    query = "select count(1) from "
    query += table_name + " where " + \
        "upper("+validate_column+")  = " + "'"+validate_value+"'"
    logger.info(f"Func: validation_query_creator \n query: {query} ")

    invokeLam = boto3.client("lambda", region_name=REGION_NAME)
    payload = {"Query": query}
    response = invokeLam.invoke(
        FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(payload))

    return json.loads(response['Payload'].read())[0][0]


def roles_table_identifier(role_name):
    """
    This function used to identify which table the roles fall in, it will take role_name as parameter
    this funtion return the table name of corresponding role
    """
    logger.info(f"Func: roles_table_identifier \n role_name: {role_name}")
    table_names = STUDY_CONTACT_TABLE_NAMES
    for i in table_names:
        sql = "select count(1) from "
        sql += i + " where " + "upper(ROLE)  = " + "'"+role_name.upper()+"'"
        invokeLam = boto3.client("lambda", region_name=REGION_NAME)
        payload = {"Query": sql}
        logger.info(f"Func: roles_table_identifier \n payload: {payload}")
        response = invokeLam.invoke(
            FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(payload))
        logger.info(f"Func: roles_table_identifier \n response: {response}")
        count = json.loads(response['Payload'].read())[0][0]
        if count > 0:
            return i
    return None


def validate_study_contact_information_intent(intent_request):
    logger.info(f"Func: validate_study_contact_information_intent \n intent_request: {intent_request} ")
    """
    validatiing all the slots in validate_study_contact_information_intent intent
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    user_query = intent_request['inputTranscript'].lower()
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    role_type = try_ex(
        lambda: intent_request['currentIntent']['slots']['role_type'])
    if slots['study_number']:
        if len(slots['study_number']) == 8 and slots['study_number'].isdigit():
            study_number = slots['study_number']
        elif re.findall(r'\d{8}(?:\.\d{1,2})?', slots['study_number']):
            study_number = re.findall(
                r'\d{8}(?:\.\d{1,2})?', slots['study_number'])[0]
        else:
            study_number = None
    elif re.findall(r'\d{8}(?:\.\d{1,2})?', user_query):
        study_number = re.findall(r'\d{8}(?:\.\d{1,2})?', user_query)[0]
    else:
        study_number = None
    #study_number = slots['study_number']if slots['study_number'] else re.findall(r'\d{8}(?:\.\d{2})?', user_query)[0] if re.findall(r'\d{8}(?:\.\d{2})?', user_query) else None
    #study_number = slots['study_number'] if slots['study_number'] else re.findall(r'\b(\d{8})\b', user_query)[0] if re.findall(r'\b(\d{8})\b', user_query) else None
    site_number = slots['site_number'] if slots['site_number'] else re.findall(
        r'\b(\d{5})\b', user_query)[0] if re.findall(r'\b(\d{5})\b', user_query) else None
    country = slots['country']

    slots = {'study_number': study_number, 'site_number': site_number,
             'role_type': role_type, 'country': country}
    if role_type is None or role_type == "others":
        session_attributes['role_type_retry_count'] = int(
            session_attributes['role_type_retry_count'])+1

        if int(session_attributes['role_type_retry_count']) > 1:
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                'role_type',
                "Sorry, I could not find the <b> {} </b> role. Could you please try again with different role ? ".format(
                    intent_request['inputTranscript'])
            )

        return elicit_slot(
            session_attributes,
            intent_request['currentIntent']['name'],
            slots,
            'role_type',
            'Please specify the role you are searching for.'
        )

    roles = find_metric_match(role_type, "study contact", intent_request)
    if len(roles) > 1:
        response_card = build_response_card(roles, include_no=True)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   slots,
                                   'role_type',
                                   "Are you looking for one of the following roles ?",
                                   response_card)
    role_type = roles[0]
    slots = {'study_number': study_number, 'site_number': site_number,
             'role_type': role_type, 'country': country}
    table = roles_table_identifier(role_type)
    session_attributes['table_name'] = table
    if not table:
        close
    if table:

        if not study_number:
            session_attributes['study_number_retry_count'] = int(
                session_attributes['study_number_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'study_number',
                               "You have selected <b> Role – {} </b>. Kindly enter the Study Number which I can assist you with: <br>".format(role_type.title()))
        if study_number and len(study_number) == 8:
            count = validation_query_creator(
                table, 'study_number', study_number)
            logger.info(f"Func: validate_study_contact_information_intent \n validation_query_creator count: {count} ")
            if (count) == 0:
                session_attributes['study_number_retry_count'] = int(
                    session_attributes['study_number_retry_count'])+1
                return elicit_slot(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   slots,
                                   'study_number',
                                   "You have entered incorrect <b> Study Number- {} </b> .Please enter correct Study Number to proceed further. <br>".format(study_number))
        if study_number and len(study_number) > 8:
            count = validation_query_creator(
                table, 'study_number', study_number[:8])
            logger.info(f"Func: validate_study_contact_information_intent \n validation_query_creator count: {count} ")
            if (count) == 0:
                session_attributes['study_number_retry_count'] = int(
                    session_attributes['study_number_retry_count'])+1
                return elicit_slot(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   slots,
                                   'study_number',
                                   "You have entered incorrect <b> Study Number- {} </b> .Please enter correct Study Number to proceed further. <br>".format(study_number))
        if table == "STUDY_WORKFORCE":
            slots = {'study_number': study_number, 'site_number': None,
                     'role_type': role_type, 'country': None}
        if table == "STUDY_REGION_WORKFORCE":
            slots = {'study_number': study_number, 'site_number': None,
                     'role_type': role_type, 'country': country}
            if not country:
                if len(study_number) > 8:
                    resp = "You have entered <b> Study number – {} </b>. for <b>  {} </b> role.<br>Please note that branch level information is not available for Study - Team Role.<br><br>  Kindly enter the country for master study number {}.: <br>".format(
                        study_number, role_type.title(), study_number[:8])
                else:
                    resp = "You have entered <b> Study number – {} </b>. for <b>  {} </b> role.<br>Kindly enter the country for study number {}.: <br>".format(
                        study_number, role_type.title(), study_number)

                session_attributes['country_retry_count'] = int(
                    session_attributes['country_retry_count'])+1
                return elicit_slot(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   slots,
                                   'country',
                                   resp)
            if country:
                if country.lower() in ['us', 'usa', 'united state']:
                    country = "United States"
                if country.lower() in ['uk', 'united kingdoms']:
                    country = "United Kingdom"
                count = validation_query_creator(
                    table, 'region', country.upper())
                if (count) == 0:
                    session_attributes['country_retry_count'] = int(
                        session_attributes['country_retry_count'])+1
                    return elicit_slot(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       'country',
                                       "You have entered incorrect <b> Country – {} </b>. Please enter correct Country to proceed further. <br>".format(country))
                slots = {'study_number': study_number, 'site_number': site_number,
                         'role_type': role_type, 'country': country}
        if table == "STUDY_SITE_WORKFORCE":
            slots = {'study_number': study_number, 'site_number': site_number,
                     'role_type': role_type, 'country': None}
            if not site_number:
                if len(study_number) > 8:
                    resp = "You have entered <b> Study number – {} </b>. for <b>  {} </b> role.<br>Please note that branch level information is not available for Study - Team Role.<br> <br> Kindly enter the site for master study number {}.: <br>".format(
                        study_number, role_type.title(), study_number[:8])
                else:
                    resp = "You have entered <b> Study number – {} </b>. for <b>  {} </b> role.<br>Kindly enter the site for study number {}.: <br>".format(
                        study_number, role_type.title(), study_number)

                session_attributes['site_number_retry_count'] = int(
                    session_attributes['site_number_retry_count'])+1
                return elicit_slot(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   slots,
                                   'site_number',
                                   resp)
            if site_number:
                count = validation_query_creator(
                    table, 'site_number', site_number)
                if (count) == 0:
                    session_attributes['site_number_retry_count'] = int(
                        session_attributes['site_number_retry_count'])+1
                    return elicit_slot(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       'site_number',
                                       "You have entered incorrect <b> Site Number – {} </b>. Please enter correct Site Number to proceed further. <br>".format(site_number))
    slots = {'study_number': study_number[:8], 'site_number': site_number,
             'role_type': role_type, 'country': country}
    return delegate(session_attributes, slots)


def validate_dashboard_metric_value(intent_request):
    logger.info(f"Func: validate_dashboard_metric_value \n intent_request: {intent_request} ")
    
    """
    validatiing all the slots in dashboard_metric_value intent
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    metric_name_retry_count = try_ex(
        lambda: session_attributes['metric_name_retry_count'])
    session_attributes['metric_name_retry_count'] = 0 if not metric_name_retry_count else int(
        metric_name_retry_count)
    user_query = intent_request['inputTranscript'].lower()
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    time_period = slots['time_period']
    if slots['study_number']:
        if len(slots['study_number']) == 8 and slots['study_number'].isdigit():
            study_number = slots['study_number']
        elif re.findall(r'\d{8}(?:\.\d{1,2})?', slots['study_number']):
            study_number = re.findall(
                r'\d{8}(?:\.\d{1,2})?', slots['study_number'])[0]
        else:
            study_number = None
    elif re.findall(r'\d{8}(?:\.\d{1,2})?', user_query):
        study_number = re.findall(r'\d{8}(?:\.\d{1,2})?', user_query)[0]
    else:
        study_number = None

    #study_number = slots['study_number'] if  slots['study_number'] else re.findall(r'\d{8}(?:\.\d{2})?', user_query)[0] if re.findall(r'\d{8}(?:\.\d{2})?', user_query) else None
    #study_number = slots['study_number'] if slots['study_number'] else re.findall(r'\b(\d{8})\b', user_query)[0] if re.findall(r'\b(\d{8})\b', user_query) else None
    site_number = slots['site_number'] if slots['site_number'] else re.findall(
        r'\b(\d{5})\b', user_query)[0] if re.findall(r'\b(\d{5})\b', user_query) else None
    country = slots['country']
    quarter = slots['quarter'] if slots['quarter'] else re.findall(
        r'\b(q[1-4])\b', user_query)[0] if re.findall(r'\b(q[1-4])\b', user_query) else None
    year = re.findall(r'\b(\d{4})\b', user_query)
    metric_name = slots['metric_name']
    month = re.findall(
        r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may?|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)', user_query)

    if time_period or year:
        year = str(year[0])if len(year) > 0 else None
        month = str(month[0])if len(month) > 0 else None
        if time_period is not None:
            month_dict = {'01': 'jan', '02': 'feb', '03': 'mar', '04': 'apr', '05': 'may', '06': 'jun',
                          '07': 'jul', '08': 'aug', '09': 'sep', '10': 'oct', '11': 'nov', '12': 'dec'}
            year_time_period = str(dt.date.today().year)
            month_time_period = str(
                time_period[time_period.find("-")+1:time_period.find("-")+3])
            month_time_period = month_dict.get(month_time_period)
            year = year_time_period if year is None else year
            month = month_time_period if month is None else month
        time_period = str(year)+"-"+str(month)

    spaqDashboardList = ['total submitted pages', 'pages submitted <=7days', 'pages submitted <=15 days', 'pages submitted >90 days', 'total query', 'queries <=7days open to answer/closed',
                         'queries 8-13 days open to answered/closed', 'queries 14-20 days open to answered/closed', 'queries 21-50 days open to answered/closed', 'queries >50 days open to answered/closed']
    tableMapper = {'total unforecasted unsubmitted pages': 'UNFORECASTED_UNSUBMITTED_PAGES', 'total unforecasted unsubmitted site pages': 'UNFORECASTED_UNSUBMITTED_PAGES', 'total unforecasted unsubmitted  non-site pages': 'UNFORECASTED_UNSUBMITTED_PAGES', 'in activated pages non-site entered data not present': 'INACTIVATED_PAGES', 'queries >50 days open to answered/closed': 'ANSWERED_QUERIES', 'in activated pages non-site entered data present': 'INACTIVATED_PAGES', 'in activated pages site entered data not present': 'INACTIVATED_PAGES', 'in activated pages site entered data present': 'INACTIVATED_PAGES', 'total signatures outstanding': 'SUMMARY_OF_OUTSTANDING_INV_SIG', '% signature complete (all types)': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'milestone signatures outstanding': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'visit signatures outstanding': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'other signatures outstanding': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total signatures outstanding zero to thirty days': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total signatures outstanding thirtyone to sixty days': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total signatures outstanding sixty one to ninety days': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total signatures outstanding greater than ninety days': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total milestone forms signed': 'MILESTONE_SIGNATURES', 'average number of days for total milestone forms signed': 'MILESTONE_SIGNATURES', '% of milestone forms signed <= 3 days': 'MILESTONE_SIGNATURES', 'milestone forms signed less than or equal to three days': 'MILESTONE_SIGNATURES', 'milestone forms signed four to six days': 'MILESTONE_SIGNATURES', 'milestone forms signed seven to ten days': 'MILESTONE_SIGNATURES', 'milestone forms signed greater than ten days': 'MILESTONE_SIGNATURES', 'visit signatures total signed': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures % signed <= 30 days': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures signed less than or equal to thirty days': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures signed thirty one to sixty days': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures signed sixtyone to ninety days': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures signed greater than ninety days': 'VISIT_SIGNATURES_DETAILED_TABL', 'in active logline on active page non-site entered data not present': 'INACTIVE_LOGLINES_ON_ACTIVE_PA', 'in active logline on active page non-site entered data present': 'INACTIVE_LOGLINES_ON_ACTIVE_PA',
                   'in active logline on active page site entered data not present': 'INACTIVE_LOGLINES_ON_ACTIVE_PA', 'in active logline on active page site entered data present': 'INACTIVE_LOGLINES_ON_ACTIVE_PA', 'total pages outstanding': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding (site)': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding (non-site)': 'OUTSTANDING_PAGES_TABLE', 'total pages to be inactivated': 'OUTSTANDING_PAGES_TABLE', 'total outstanding blank pages': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding zero to five days': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding six to fifteen days': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding sixteen to thirty days': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding greater than thirty days': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding percentage greater than thirty days': 'OUTSTANDING_PAGES_TABLE', 'total outstanding queries': 'QUERIES_OUTSTANDING_TABLE', 'total open queries': 'QUERIES_OUTSTANDING_TABLE', 'total answered queries': 'QUERIES_OUTSTANDING_TABLE', 'total query': 'ANSWERED_QUERIES', 'total outstanding (re-queries)': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding (ipd queries)': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries zero to seven days': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries eight to thirteen days': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries fourteen to twenty days': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries twenty one to fifty days': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries greater than fifty days': 'QUERIES_OUTSTANDING_TABLE', 'percentage of total outstanding queries greater than fifty days': 'QUERIES_OUTSTANDING_TABLE', 'total pages forecasted': 'FORECASTED_PAGES_TABLE', 'total pages forecasted (site)': 'FORECASTED_PAGES_TABLE', 'total pages forecasted (non-site)': 'FORECASTED_PAGES_TABLE', 'total pages forecasted to be inactivated': 'FORECASTED_PAGES_TABLE', 'total forecasted blank pages': 'FORECASTED_PAGES_TABLE', 'total submitted pages': 'SUBMITTED_PAGES', 'pages submitted <=7days': 'SUBMITTED_PAGES', 'pages submitted <=15 days': 'SUBMITTED_PAGES', 'pages submitted >90 days': 'SUBMITTED_PAGES', 'queries <=7days open to answer/closed': 'ANSWERED_QUERIES', 'queries 8-13 days open to answered/closed': 'ANSWERED_QUERIES', 'queries 14-20 days open to answered/closed': 'ANSWERED_QUERIES', 'queries 21-50 days open to answered/closed': 'ANSWERED_QUERIES'}

    slots = {'study_number': study_number, 'site_number': site_number, 'quarter': quarter,
             'country': country, 'metric_name': metric_name, 'time_period': time_period}
    if not metric_name:
        session_attributes['metric_name_retry_count'] = int(
            session_attributes['metric_name_retry_count'])+1
        return elicit_slot(session_attributes,
                           intent_request['currentIntent']['name'],
                           slots,
                           'metric_name',
                           "Please specify the Metric Name as available in Data Management Tool/Submitted Pages and Answered Queries.")
    if metric_name:
        metric = find_metric_match(metric_name, "metric value")
        
        if len(metric) == 0:
            metric_collibra = find_metric_match(metric_name, "collibra")
            if len(metric_collibra) == 0:
                session_attributes['metric_name_retry_count'] = int(
                    session_attributes['metric_name_retry_count'])+1
                return elicit_slot(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   slots,
                                   'metric_name',
                                   "Sorry we don't have a metric called {}.<br>Currently we are supporting only Data Management Tool and Submitted Pages and Answered Queries metrics, please type a metric from this report".format(metric_name))
            if len(metric_collibra) > 1:
                response_card = build_response_card(
                    metric_collibra, include_no=True)
                return elicit_slot_buttons(session_attributes,
                                           "collibra_metric_report_name",
                                           {"metric_name": None},
                                           'metric_name',
                                           f"I am not able to find the value of {metric_name}, But I can help you where you can find values <br> <br> These are the closest metric names which I can find reports, please choose from the buttons ",
                                           response_card)
            response = f"I am not able to find the value for - {metric_collibra[0]} but below are the links where you can find the report "
            response += fulfill_collibra_metric_report_name(
                session_attributes, slots)
            return close(session_attributes, 'Fulfilled', response)
        if len(metric) > 1:
            response_card = build_response_card(metric, include_no=True)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       'metric_name',
                                       "These are the closest metric names which I can find from your query, please choose from the buttons ",
                                       response_card)
        metric = metric[0]
        try_ex(lambda: session_attributes.pop('metric_name_retry_count'))
        slots['metric_name'] = metric
    # fetch dashboard name where this metric is available
    data = read_excel("MetricCombination.xlsx", "Sheet1")
    data = data[data['Metric Name'] == metric]
    dashboard_name = data['Dashboard Name'].unique()[0]
    # fetch userid for the request
    user_id = intent_request['userId'].split("_")[0]
    # fetch list of dashboard accessible to the user
    user_access_list = user_dashboard_access(user_id)
    # if dashboard is accessible by the user then go to validate the request
    if dashboard_name not in user_access_list:
        response = "Sorry, it looks like you don't have access to this metric.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
        logger.info("No dashboard Access")
    try:
        table = tableMapper.get(metric)
        logger.info("Table Mapper Executed")
        
        session_attributes['table_name'] = table
        dashboard = "SPAQ" if metric.lower() in spaqDashboardList else "DMT"
        if study_number:
            logger.info("Study Number")
            count = validation_query_creator(table, 'study_number', study_number)
            if (count) == 0:
                session_attributes['study_number_retry_count'] = int(
                    session_attributes['study_number_retry_count'])+1
                return elicit_slot(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   slots,
                                   'study_number',
                                   "We don't have this Study number {}, please type again.".format(study_number))
        if site_number:
            count = validation_query_creator(table, 'site_number', site_number)
            if (count) == 0:
                session_attributes['site_number_retry_count'] = int(
                    session_attributes['site_number_retry_count'])+1
                return elicit_slot(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   slots,
                                   'site_number',
                                   "We don't have this Site number {}, please type again.".format(site_number))
    
        if country:
            if country.lower() in ['us', 'usa', 'united state']:
                country = "United States"
            if country.lower() in ['uk', 'united kingdoms']:
                country = "United Kingdom"
            slots['country'] = country
            count = validation_query_creator(table, 'country', country.upper())
            if (count) == 0:
                session_attributes['country_retry_count'] = int(
                    session_attributes['country_retry_count'])+1
                return elicit_slot(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   slots,
                                   'country',
                                   "We don't have this country {}, please type again.".format(country))
        if dashboard == "SPAQ" and time_period:
            year = time_period[:4]
            month = time_period[time_period.find("-")+1:time_period.find("-")+4]
            if year and month:
                count_year = validation_query_creator(table, 'year', year.upper())
                count_month = validation_query_creator(
                    table, 'month', year.upper())
                if (count_year or count_month) == 0:
                    return elicit_slot(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       'time_period',
                                       "We don't have this year {} and month {}, please type the year and month again .".format(year, month))
            if year and quarter:
                count_year = validation_query_creator(table, 'year', year.upper())
                count_quarter = validation_query_creator(
                    table, 'quarter', quarter.upper())
                if (count_year) == 0:
                    return elicit_slot(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       'time_period',
                                       "We don't have this year {} please type the year again .".format(year))
                if (count_quarter) == 0:
                    return elicit_slot(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       'quarter',
                                       "We don't have this quarter {} please type the quarter again .".format(quarter))
        return delegate(session_attributes, slots)
    except Exception as e:
        logger.info("Error : " + str(e))
        

def first_and_last(string):
    if len(string) > 49:
        new_str = string.split()
        return " ".join(new_str[:1]+new_str[-5:])
    else:
        return string


def find_metric_match(metric_name, context, json_input=None):
    logger.info(f'Func find_metric_match \n metric_name : {metric_name} \n context: {context} \n  json_input: {json_input}')
    """
    This function will take two arguments
    1. metric_name - the name of metric that we need to match
    2. context - in which context you want to identify this metric collibra or metric value
    If no match is found it will return None
    If matches found it return a list of all the matched metrics

    """

    if context == "study contact":

        if json_input:
            if len(json_input['currentIntent']['slotDetails']['role_type']['resolutions']) > 1:
                role_list = [i['value']for i in json_input['currentIntent']
                             ['slotDetails']['role_type']['resolutions']]
                if json_input['currentIntent']['slotDetails']['role_type']['originalValue'] in role_list:
                    return [json_input['currentIntent']['slotDetails']['role_type']['originalValue']]
                else:
                    return role_list
            else:
                return [metric_name]
    if context == "metric value":

        synonyms_metrics = {'total unforecasted unsubmitted pages': 'total unforecasted unsubmitted pages', 'unforecasted unsubmitted pages': 'total unforecasted unsubmitted pages', 'unsubmitted pages': 'total unforecasted unsubmitted pages', 'number of unsubmitted pages': 'total unforecasted unsubmitted pages', 'number of unforecasted unsubmitted pages': 'total unforecasted unsubmitted pages', 'count of unforecasted unsubmitted pages': 'total unforecasted unsubmitted pages', 'sum of unforecasted unsubmitted pages': 'total unforecasted unsubmitted pages', 'total unforecasted unsubmitted site pages': 'total unforecasted unsubmitted site pages', 'unforecasted unsubmitted site pages': 'total unforecasted unsubmitted site pages', 'unsubmitted site pages': 'total unforecasted unsubmitted site pages', 'number of unsubmitted site pages': 'total unforecasted unsubmitted site pages', 'number of unforecasted unsubmitted site pages': 'total unforecasted unsubmitted site pages', 'count of unforecasted unsubmitted site pages': 'total unforecasted unsubmitted site pages', 'sum of unforecasted unsubmitted site pages': 'total unforecasted unsubmitted site pages', 'unforcasted unsubmitted pages for site': 'total unforecasted unsubmitted site pages', 'total unforecasted unsubmitted  non-site pages': 'total unforecasted unsubmitted  non-site pages', 'unforecasted unsubmitted non-site pages': 'total unforecasted unsubmitted  non-site pages', 'unsubmitted non-site pages': 'total unforecasted unsubmitted  non-site pages', 'number of unsubmitted non-site pages': 'total unforecasted unsubmitted  non-site pages', 'number of unforecasted unsubmitted non-site pages': 'total unforecasted unsubmitted  non-site pages', 'count of unforecasted unsubmitted non-site pages': 'total unforecasted unsubmitted  non-site pages', 'sum of unforecasted unsubmitted non-site pages': 'total unforecasted unsubmitted  non-site pages', 'unforcasted unsubmitted pages for non-site': 'total unforecasted unsubmitted  non-site pages', 'in activated pages non-site entered data not present': 'in activated pages non-site entered data not present', 'total number of in activated pages non-site entered data not present.': 'in activated pages non-site entered data not present', 'total number of in-activated pages non-site entered data not present.': 'in activated pages non-site entered data not present', 'count of in-activated pages non-site entered data not present.': 'in activated pages non-site entered data not present', 'sum of in-activated pages non-site entered data not present.': 'in activated pages non-site entered data not present', '': 'queries >50 days open to answered/closed', 'in activated pages non-site entered data present': 'in activated pages non-site entered data present', 'total number of in activated pages non-site entered data present': 'in activated pages non-site entered data present', 'total number of in-activated pages non-site entered data present': 'in activated pages non-site entered data present', 'in activated pages site entered data not present': 'in activated pages site entered data not present', 'total number of in activated pages site entered data not present': 'in activated pages site entered data not present', 'total number of in-activated pages site entered data not present': 'in activated pages site entered data not present', 'count of in-activated pages site entered data not present': 'in activated pages site entered data not present', 'in activated pages site entered data present': 'in activated pages site entered data present', 'total number of in activated pages site entered data present': 'in activated pages site entered data present', 'total number of in-activated pages site entered data present': 'in activated pages site entered data present', 'count of in-activated pages site entered data present': 'in activated pages site entered data present', 'total signatures outstanding': 'total signatures outstanding', 'signatures outstanding': 'total signatures outstanding', 'number of signatures outstanding': 'total signatures outstanding', 'number of outstanding signatures': 'total signatures outstanding', 'total outstanding signatures': 'total signatures outstanding', 'count outstanding signatures': 'total signatures outstanding', '% signature complete (all types)': '% signature complete (all types)', 'signature complete': '% signature complete (all types)', 'number of signature complete': '% signature complete (all types)', 'total signature complete': '% signature complete (all types)', 'percentage of signature complete': '% signature complete (all types)', 'milestone signatures outstanding': 'milestone signatures outstanding', 'total milestone signatures outstanding': 'milestone signatures outstanding', 'number milestone signatures outstanding': 'milestone signatures outstanding', 'visit signatures outstanding': 'visit signatures outstanding', 'total visit signatures outstanding': 'visit signatures outstanding', 'number of visit signatures outstanding': 'visit signatures outstanding', 'count of visit signatures outstanding': 'visit signatures outstanding', 'other signatures outstanding': 'other signatures outstanding', 'total other signatures outstanding': 'other signatures outstanding', 'number of other signatures outstanding': 'other signatures outstanding', 'count of other signatures outstanding': 'other signatures outstanding', 'total signatures outstanding zero to thirty days': 'total signatures outstanding zero to thirty days', 'number of signatures outstanding zero to thirty days': 'total signatures outstanding zero to thirty days', 'count of signatures outstanding zero to thirty days': 'total signatures outstanding zero to thirty days', 'sum of signatures outstanding zero to thirty days': 'total signatures outstanding zero to thirty days', 'signatures outstanding zero to thirty days': 'total signatures outstanding zero to thirty days', 'signatures outstanding 0-30 days': 'total signatures outstanding zero to thirty days', 'number of signatures outstanding 0-30 days': 'total signatures outstanding zero to thirty days', 'count of signatures outstanding 0-30 days': 'total signatures outstanding zero to thirty days', 'total signatures outstanding thirtyone to sixty days': 'total signatures outstanding thirtyone to sixty days', 'number of signatures outstanding thirtyone to sixty days': 'total signatures outstanding thirtyone to sixty days', 'count of signatures outstanding thirtyone to sixty days': 'total signatures outstanding thirtyone to sixty days', 'sum of signatures outstanding thirtyone to sixty days': 'total signatures outstanding thirtyone to sixty days', 'signatures outstanding thirtyone to sixty days': 'total signatures outstanding thirtyone to sixty days', 'signatures outstanding 31-60 days': 'total signatures outstanding thirtyone to sixty days', 'number of signatures outstanding 31-60 days': 'total signatures outstanding thirtyone to sixty days', 'count of signatures outstanding 31-60 days': 'total signatures outstanding thirtyone to sixty days', 'total signatures outstanding sixty one to ninety days': 'total signatures outstanding sixty one to ninety days', 'number of signatures outstanding sixty one to ninety days': 'total signatures outstanding sixty one to ninety days', 'count of signatures outstanding sixty one to ninety days': 'total signatures outstanding sixty one to ninety days', 'sum of signatures outstanding sixty one to ninety days': 'total signatures outstanding sixty one to ninety days', 'signatures outstanding sixty one to ninety days': 'total signatures outstanding sixty one to ninety days', 'signatures outstanding 61-90 days': 'total signatures outstanding sixty one to ninety days', 'number of signatures outstanding 61-90 days': 'total signatures outstanding sixty one to ninety days', 'count of signatures outstanding 61-90 days': 'total signatures outstanding sixty one to ninety days', 'total signatures outstanding greater than ninety days': 'total signatures outstanding greater than ninety days', 'number of signatures outstanding greater than ninety days': 'total signatures outstanding greater than ninety days', 'count of signatures outstanding greater than ninety days': 'total signatures outstanding greater than ninety days', 'sum of signatures outstanding greater than ninety days': 'total signatures outstanding greater than ninety days', 'signatures outstanding greater than ninety days': 'total signatures outstanding greater than ninety days', 'signatures outstanding >90 days': 'total signatures outstanding greater than ninety days', 'number of signatures outstanding >90 days': 'total signatures outstanding greater than ninety days', 'count of signatures outstanding >90 days': 'total signatures outstanding greater than ninety days', 'total milestone forms signed': 'total milestone forms signed', 'milestone forms signed': 'total milestone forms signed', 'number of milestone forms signed': 'total milestone forms signed', 'count of milestone forms signed': 'total milestone forms signed', 'average number of days for total milestone forms signed': 'average number of days for total milestone forms signed', 'average days for total milestone forms signed': 'average number of days for total milestone forms signed', 'average number of days for number of milestone forms signed': 'average number of days for total milestone forms signed', 'average number of days for count of milestone forms signed': 'average number of days for total milestone forms signed', '% of milestone forms signed <= 3 days': '% of milestone forms signed <= 3 days', 'percentage of milestone forms signed less than or equal to 3 days': '% of milestone forms signed <= 3 days', 'percentage of milestone forms signed <= 3 days': '% of milestone forms signed <= 3 days', 'milestone forms signed <= 3 days': '% of milestone forms signed <= 3 days', 'milestone forms signed less than or equal to 3 days': '% of milestone forms signed <= 3 days', 'milestone forms signed less than or equal to three days': 'milestone forms signed less than or equal to three days', 'count of milestone forms signed less than or equal to three days': 'milestone forms signed less than or equal to three days', 'number of milestone forms signed less than or equal to three days': 'milestone forms signed less than or equal to three days', 'total milestone forms signed less than or equal to three days': 'milestone forms signed less than or equal to three days', 'count of milestone forms signed <=3 days': 'milestone forms signed less than or equal to three days', 'number of milestone forms signed <=3 days': 'milestone forms signed less than or equal to three days', 'total milestone forms signed <=3 days': 'milestone forms signed less than or equal to three days', 'milestone forms signed four to six days': 'milestone forms signed four to six days', 'count of milestone forms signed four to six days': 'milestone forms signed four to six days', 'number of milestone forms signed four to six days': 'milestone forms signed four to six days', 'total milestone forms signed four to six days': 'milestone forms signed four to six days', 'count of milestone forms signed 4-6 days': 'milestone forms signed four to six days', 'number of milestone forms signed 4-6 days': 'milestone forms signed four to six days', 'total milestone forms signed 4-6 days': 'milestone forms signed four to six days', 'milestone forms signed seven to ten days': 'milestone forms signed seven to ten days', 'count of milestone forms signed seven to ten days': 'milestone forms signed seven to ten days', 'number of milestone forms signed seven to ten days': 'milestone forms signed seven to ten days', 'total milestone forms signed seven to ten days': 'milestone forms signed seven to ten days', 'count of milestone forms signed 7-10 days': 'milestone forms signed seven to ten days', 'number of milestone forms signed 7-10 days': 'milestone forms signed seven to ten days', 'total milestone forms signed 7-10 days': 'milestone forms signed seven to ten days', 'milestone forms signed greater than ten days': 'milestone forms signed greater than ten days', 'count of milestone forms signed greater than ten days': 'milestone forms signed greater than ten days', 'number of milestone forms signed greater than ten days': 'milestone forms signed greater than ten days', 'total milestone forms signed greater than ten days': 'milestone forms signed greater than ten days', 'count of milestone forms signed >10 days': 'milestone forms signed greater than ten days', 'number of milestone forms signed >10 days': 'milestone forms signed greater than ten days', 'total milestone forms signed >10 days': 'milestone forms signed greater than ten days', 'visit signatures total signed': 'visit signatures total signed', 'total visit signatures total signed': 'visit signatures total signed', 'number of visit signatures total signed': 'visit signatures total signed', 'count of visit signatures total signed': 'visit signatures total signed', 'visit signatures signed': 'visit signatures total signed', 'visit signatures % signed <= 30 days': 'visit signatures % signed <= 30 days', 'percentage of visit signatures signed <= 30 days': 'visit signatures % signed <= 30 days', 'percentage of visit signatures signed less than or equal to 30 days': 'visit signatures % signed <= 30 days', 'visit signatures signed <= 30 days': 'visit signatures % signed <= 30 days', 'visit signatures signed less than or equal to thirty days': 'visit signatures signed less than or equal to thirty days', 'number of visit signatures <=30 days': 'visit signatures signed less than or equal to thirty days', 'count of visit signatures <=30 days': 'visit signatures signed less than or equal to thirty days', 'total visit signatures <=30 days': 'visit signatures signed less than or equal to thirty days', 'number of visit signatures less than or equal to thirty days': 'visit signatures signed less than or equal to thirty days', 'count of visit signatures less than or equal to thirty days': 'visit signatures signed less than or equal to thirty days', 'total visit signatures less than or equal to thirty days': 'visit signatures signed less than or equal to thirty days', 'visit signatures signed thirty one to sixty days': 'visit signatures signed thirty one to sixty days', 'number of visit signatures thirty one to sixty days': 'visit signatures signed thirty one to sixty days', 'count of visit signatures thirty one to sixty days': 'visit signatures signed thirty one to sixty days', 'total visit signatures thirty one to sixty days': 'visit signatures signed thirty one to sixty days', 'number of visit signatures 31-60 days': 'visit signatures signed thirty one to sixty days', 'count of visit signatures thirty 31-60 days': 'visit signatures signed thirty one to sixty days', 'total visit signatures thirty 31-60 days': 'visit signatures signed thirty one to sixty days', 'visit signatures signed sixtyone to ninety days': 'visit signatures signed sixtyone to ninety days', 'number of visit signatures sixtyone to ninety days': 'visit signatures signed sixtyone to ninety days', 'count of visit signatures sixtyone to ninety days': 'visit signatures signed sixtyone to ninety days', 'total visit signatures sixtyone to ninety days': 'visit signatures signed sixtyone to ninety days', 'number of visit signatures 61-90 days': 'visit signatures signed sixtyone to ninety days', 'count of visit signatures thirty 61-90 days': 'visit signatures signed sixtyone to ninety days', 'total visit signatures thirty 61-90 days': 'visit signatures signed sixtyone to ninety days', 'visit signatures signed greater than ninety days': 'visit signatures signed greater than ninety days', 'number of visit signatures >90 days': 'visit signatures signed greater than ninety days', 'count of visit signatures >90 days': 'visit signatures signed greater than ninety days', 'total visit signatures >90 days': 'visit signatures signed greater than ninety days', 'number of visit signatures greater than ninety days': 'visit signatures signed greater than ninety days', 'count of visit signatures greater than ninety days': 'visit signatures signed greater than ninety days', 'total visit signatures greater than ninety days': 'visit signatures signed greater than ninety days', 'in active logline on active page non-site entered data not present': 'in active logline on active page non-site entered data not present', 'total in active logline on active page non-site entered data not present': 'in active logline on active page non-site entered data not present', 'number of in active logline on active page non-site entered data not present': 'in active logline on active page non-site entered data not present', 'count of in active logline on active page non-site entered data not present': 'in active logline on active page non-site entered data not present', 'total in-active logline on active page non-site entered data not present': 'in active logline on active page non-site entered data not present', 'number of in-active logline on active page non-site entered data not present': 'in active logline on active page non-site entered data not present', 'count of in-active logline on active page non-site entered data not present': 'in active logline on active page non-site entered data not present', 'in active logline on active page non-site entered data present': 'in active logline on active page non-site entered data present', 'total in active logline on active page non-site entered data present': 'in active logline on active page non-site entered data present', 'number of in active logline on active page non-site entered data present': 'in active logline on active page non-site entered data present', 'count of in active logline on active page non-site entered data present': 'in active logline on active page non-site entered data present', 'total in-active logline on active page non-site entered data present': 'in active logline on active page non-site entered data present', 'number of in-active logline on active page non-site entered data present': 'in active logline on active page non-site entered data present', 'count of in-active logline on active page non-site entered data present': 'in active logline on active page non-site entered data present', 'in active logline on active page site entered data not present': 'in active logline on active page site entered data not present', 'total in active logline on active page site entered data not present': 'in active logline on active page site entered data not present', 'number of in active logline on active page site entered data not present': 'in active logline on active page site entered data not present', 'count of in active logline on active page site entered data not present': 'in active logline on active page site entered data not present', 'total in-active logline on active page site entered data not present': 'in active logline on active page site entered data not present', 'number of in-active logline on active page site entered data not present': 'in active logline on active page site entered data not present', 'count of in-active logline on active page site entered data not present': 'in active logline on active page site entered data not present', 'in active logline on active page site entered data present': 'in active logline on active page site entered data present', 'total in active logline on active page site entered data present': 'in active logline on active page site entered data present', 'number of in active logline on active page site entered data present': 'in active logline on active page site entered data present', 'count of in active logline on active page site entered data present': 'in active logline on active page site entered data present', 'total in-active logline on active page site entered data present': 'in active logline on active page site entered data present', 'number of in-active logline on active page site entered data present': 'in active logline on active page site entered data present', 'count of in-active logline on active page site entered data present': 'in active logline on active page site entered data present', 'total pages outstanding': 'total pages outstanding', 'pages outstanding': 'total pages outstanding', 'outstanding pages': 'total pages outstanding', 'number of outstanding pages': 'total pages outstanding', 'outstanding pages number': 'total pages outstanding', 'count of outstanding pages': 'total pages outstanding', 'outstanding pages count': 'total pages outstanding', 'sum of outstanding pages': 'total pages outstanding', 'total pages outstanding (site)': 'total pages outstanding (site)', 'site pages outstanding': 'total pages outstanding (site)', 'pages outstanding for site': 'total pages outstanding (site)', 'outstanding pages for site': 'total pages outstanding (site)', 'outstanding site pages': 'total pages outstanding (site)', 'number of outstanding site pages': 'total pages outstanding (site)', 'number of outstanding pages for site': 'total pages outstanding (site)', 'number of site pages outstanding': 'total pages outstanding (site)', 'count of outstanding site pages': 'total pages outstanding (site)', 'count of pages outstanding for site': 'total pages outstanding (site)', 'count of site pages outstanding': 'total pages outstanding (site)', 'sum of outstanding site pages': 'total pages outstanding (site)', 'sum of site pages outstanding': 'total pages outstanding (site)', 'sum of pages outstanding  for site': 'total pages outstanding (site)', 'total pages outstanding (non-site)': 'total pages outstanding (non-site)', 'non-site pages outstanding': 'total pages outstanding (non-site)', 'non site pages outstanding': 'total pages outstanding (non-site)', 'pages outstanding for non-site': 'total pages outstanding (non-site)', 'pages outstanding for non site': 'total pages outstanding (non-site)', 'outstanding pages for non-site': 'total pages outstanding (non-site)', 'outstanding pages for non site': 'total pages outstanding (non-site)', 'outstanding non-site pages': 'total pages outstanding (non-site)', 'outstanding non site pages': 'total pages outstanding (non-site)', 'number of outstanding non-site pages': 'total pages outstanding (non-site)', 'number of outstanding non site pages': 'total pages outstanding (non-site)', 'number of outstanding pages for non-site': 'total pages outstanding (non-site)', 'number of outstanding pages for non site': 'total pages outstanding (non-site)', 'number of non-site pages outstanding': 'total pages outstanding (non-site)', 'number of non site pages outstanding': 'total pages outstanding (non-site)', 'count of outstanding non-site pages': 'total pages outstanding (non-site)', 'count of outstanding non site pages': 'total pages outstanding (non-site)', 'count of pages outstanding for non-site': 'total pages outstanding (non-site)', 'count of pages outstanding for non site': 'total pages outstanding (non-site)', 'count of non-site pages outstanding': 'total pages outstanding (non-site)', 'count of non site pages outstanding': 'total pages outstanding (non-site)', 'sum of outstanding non-site pages': 'total pages outstanding (non-site)', 'sum of outstanding non site pages': 'total pages outstanding (non-site)', 'sum of non-site pages outstanding': 'total pages outstanding (non-site)', 'sum of non site pages outstanding': 'total pages outstanding (non-site)', 'sum of pages outstanding  for non-site': 'total pages outstanding (non-site)', 'sum of pages outstanding  for non site': 'total pages outstanding (non-site)', 'total pages to be inactivated': 'total pages to be inactivated', 'to be inactivated pages': 'total pages to be inactivated', 'to be in activated pages': 'total pages to be inactivated', 'pages to be inactivated': 'total pages to be inactivated', 'pages to be in activated': 'total pages to be inactivated', 'total outstanding blank pages': 'total outstanding blank pages', 'outstanding blank pages': 'total outstanding blank pages', 'blank pages': 'total outstanding blank pages', 'blank pages outstanding': 'total outstanding blank pages', 'total pages outstanding zero to five days': 'total pages outstanding zero to five days', 'pages outstanding 0-5 days': 'total pages outstanding zero to five days', 'pages outstanding 0 to 5 days': 'total pages outstanding zero to five days', 'pages outstanding less than 5 days': 'total pages outstanding zero to five days', 'pages outstanding < 5 days': 'total pages outstanding zero to five days', 'pages outstanding <= 5 days': 'total pages outstanding zero to five days', 'pages outstanding less than 7 days': 'total pages outstanding zero to five days', 'pages outstanding < 7 days': 'total pages outstanding zero to five days', 'pages outstanding <= 7 days': 'total pages outstanding zero to five days', 'outstanding pages 0-5 days': 'total pages outstanding zero to five days', 'outstanding pages 0 to 5 days': 'total pages outstanding zero to five days', 'outstanding pages less than 5 days': 'total pages outstanding zero to five days', 'outstanding pages < 5 days': 'total pages outstanding zero to five days', 'outstanding pages<= 5 days': 'total pages outstanding zero to five days', 'outstanding pages less than 7 days': 'total pages outstanding zero to five days', 'outstanding pages< 7 days': 'total pages outstanding zero to five days', 'outstanding pages<= 7 days': 'total pages outstanding zero to five days', 'number of outstanding pages 0-5 days': 'total pages outstanding zero to five days', 'number of outstanding pages 0 to 5 days': 'total pages outstanding zero to five days', 'number of outstanding pages less than 5 days': 'total pages outstanding zero to five days', 'number of outstanding pages < 5 days': 'total pages outstanding zero to five days', 'number of outstanding pages<= 5 days': 'total pages outstanding zero to five days', 'number of outstanding pages less than 7 days': 'total pages outstanding zero to five days', 'number of outstanding pages< 7 days': 'total pages outstanding zero to five days', 'number of outstanding pages<= 7 days': 'total pages outstanding zero to five days', 'count of outstanding pages 0-5 days': 'total pages outstanding zero to five days', 'count of outstanding pages 0 to 5 days': 'total pages outstanding zero to five days', 'count of outstanding pages less than 5 days': 'total pages outstanding zero to five days', 'count of outstanding pages < 5 days': 'total pages outstanding zero to five days', 'count of outstanding pages<= 5 days': 'total pages outstanding zero to five days', 'count of outstanding pages less than 7 days': 'total pages outstanding zero to five days', 'count of outstanding pages< 7 days': 'total pages outstanding zero to five days', 'count of outstanding pages<= 7 days': 'total pages outstanding zero to five days', 'sum of outstanding pages 0-5 days': 'total pages outstanding zero to five days', 'sum of outstanding pages 0 to 5 days': 'total pages outstanding zero to five days', 'sum of outstanding pages less than 5 days': 'total pages outstanding zero to five days', 'sum of outstanding pages < 5 days': 'total pages outstanding zero to five days', 'sum of outstanding pages<= 5 days': 'total pages outstanding zero to five days', 'sum of outstanding pages less than 7 days': 'total pages outstanding zero to five days', 'sum of outstanding pages< 7 days': 'total pages outstanding zero to five days', 'sum of outstanding pages<= 7 days': 'total pages outstanding zero to five days', 'outstanding pages count 0-5 days': 'total pages outstanding zero to five days', 'outstanding pages count 0 to 5 days': 'total pages outstanding zero to five days', 'outstanding pages count less than 5 days': 'total pages outstanding zero to five days', 'outstanding pages count < 5 days': 'total pages outstanding zero to five days', 'outstanding pages count <= 5 days': 'total pages outstanding zero to five days', 'outstanding pages count less than 7 days': 'total pages outstanding zero to five days', 'outstanding pages count< 7 days': 'total pages outstanding zero to five days', 'outstanding pages count <= 7 days': 'total pages outstanding zero to five days', 'total pages outstanding six to fifteen days': 'total pages outstanding six to fifteen days', 'pages outstanding 6-15 days': 'total pages outstanding six to fifteen days', 'pages outstanding 6 to 15 days': 'total pages outstanding six to fifteen days', 'pages outstanding less than 15 days': 'total pages outstanding six to fifteen days', 'pages outstanding < 15 days': 'total pages outstanding six to fifteen days', 'pages outstanding <= 15 days': 'total pages outstanding six to fifteen days', 'outstanding pages 6-15 days': 'total pages outstanding six to fifteen days', 'outstanding pages 6 to 15 days': 'total pages outstanding six to fifteen days', 'outstanding pages less than 15 days': 'total pages outstanding six to fifteen days', 'outstanding pages < 15 days': 'total pages outstanding six to fifteen days', 'outstanding pages<= 15 days': 'total pages outstanding six to fifteen days', 'number of outstanding pages 6-15 days': 'total pages outstanding six to fifteen days', 'number of outstanding pages 6 to 15 days': 'total pages outstanding six to fifteen days', 'number of outstanding pages less than 15 days': 'total pages outstanding six to fifteen days', 'number of outstanding pages < 15 days': 'total pages outstanding six to fifteen days', 'number of outstanding pages<= 15 days': 'total pages outstanding six to fifteen days', 'count of outstanding pages 6-15 days': 'total pages outstanding six to fifteen days', 'count of outstanding pages 6 to 15 days': 'total pages outstanding six to fifteen days', 'count of outstanding pages less than 15 days': 'total pages outstanding six to fifteen days', 'count of outstanding pages < 15 days': 'total pages outstanding six to fifteen days', 'count of outstanding pages<= 15 days': 'total pages outstanding six to fifteen days', 'sum of outstanding pages 6-15 days': 'total pages outstanding six to fifteen days', 'sum of outstanding pages 6 to 15 days': 'total pages outstanding six to fifteen days', 'sum of outstanding pages less than 15 days': 'total pages outstanding six to fifteen days', 'sum of outstanding pages < 15 days': 'total pages outstanding six to fifteen days', 'sum of outstanding pages<= 15 days': 'total pages outstanding six to fifteen days', 'outstanding pages count 6-15 days': 'total pages outstanding six to fifteen days', 'outstanding pages count 6 to 15 days': 'total pages outstanding six to fifteen days', 'outstanding pages count less than 15 days': 'total pages outstanding six to fifteen days', 'outstanding pages count < 15 days': 'total pages outstanding six to fifteen days', 'outstanding pages count <= 15 days': 'total pages outstanding six to fifteen days', 'total pages outstanding sixteen to thirty days': 'total pages outstanding sixteen to thirty days', 'pages outstanding 16-30 days': 'total pages outstanding sixteen to thirty days', 'pages outstanding 16 to 30 days': 'total pages outstanding sixteen to thirty days', 'pages outstanding less than 30 days': 'total pages outstanding sixteen to thirty days', 'pages outstanding < 30 days': 'total pages outstanding sixteen to thirty days', 'pages outstanding <= 30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages 16-30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages 16 to 30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages less than 30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages < 30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages<= 30 days': 'total pages outstanding sixteen to thirty days', 'number of outstanding pages 16-30 days': 'total pages outstanding sixteen to thirty days', 'number of outstanding pages 16 to 30 days': 'total pages outstanding sixteen to thirty days', 'number of outstanding pages less than 30 days': 'total pages outstanding sixteen to thirty days', 'number of outstanding pages < 30 days': 'total pages outstanding sixteen to thirty days', 'number of outstanding pages<= 30 days': 'total pages outstanding sixteen to thirty days', 'count of outstanding pages 16-30 days': 'total pages outstanding sixteen to thirty days', 'count of outstanding pages 16 to 30 days': 'total pages outstanding sixteen to thirty days', 'count of outstanding pages less than 30 days': 'total pages outstanding sixteen to thirty days', 'count of outstanding pages < 30 days': 'total pages outstanding sixteen to thirty days', 'count of outstanding pages<= 30 days': 'total pages outstanding sixteen to thirty days', 'sum of outstanding pages 16-30 days': 'total pages outstanding sixteen to thirty days', 'sum of outstanding pages 16 to 30 days': 'total pages outstanding sixteen to thirty days', 'sum of outstanding pages less than 30 days': 'total pages outstanding sixteen to thirty days', 'sum of outstanding pages < 30 days': 'total pages outstanding sixteen to thirty days', 'sum of outstanding pages<= 30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages count 16-30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages count 16 to 30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages count less than 30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages count < 30 days': 'total pages outstanding sixteen to thirty days', 'outstanding pages count <= 30 days': 'total pages outstanding sixteen to thirty days', 'total pages outstanding greater than thirty days': 'total pages outstanding greater than thirty days', 'pages outstanding greater than 30 days': 'total pages outstanding greater than thirty days', 'pages outstanding 30 days': 'total pages outstanding greater than thirty days', 'pages outstanding > 30 days': 'total pages outstanding greater than thirty days', 'outstanding pages 30 days': 'total pages outstanding greater than thirty days', 'outstanding pages greater than 30 days': 'total pages outstanding greater than thirty days', 'outstanding pages > 30 days': 'total pages outstanding greater than thirty days', 'number of outstanding pages 30 days': 'total pages outstanding greater than thirty days', 'number of outstanding pages greater than 30 days': 'total pages outstanding greater than thirty days', 'number of outstanding pages > 30 days': 'total pages outstanding greater than thirty days', 'count of outstanding pages 30 days': 'total pages outstanding greater than thirty days', 'count of outstanding pages greater than 30 days': 'total pages outstanding greater than thirty days', 'count of outstanding pages > 30 days': 'total pages outstanding greater than thirty days', 'sum of outstanding pages 30 days': 'total pages outstanding greater than thirty days', 'sum of outstanding pages greater than 30 days': 'total pages outstanding greater than thirty days', 'sum of outstanding pages > 30 days': 'total pages outstanding greater than thirty days', 'outstanding pages count 30 days': 'total pages outstanding greater than thirty days', 'outstanding pages count greater than 30 days': 'total pages outstanding greater than thirty days', 'outstanding pages count > 30 days': 'total pages outstanding greater than thirty days', 'outstanding pages count >= 30 days': 'total pages outstanding greater than thirty days', 'total pages outstanding percentage greater than thirty days': 'total pages outstanding percentage greater than thirty days', 'pages outstanding greater than 30 days percentage': 'total pages outstanding percentage greater than thirty days', 'pages outstanding greater than 30 days percent': 'total pages outstanding percentage greater than thirty days',
                            'percentage of pages outstanding greater than 30 days': 'total pages outstanding percentage greater than thirty days', 'percent of pages outstanding greater than 30 days': 'total pages outstanding percentage greater than thirty days', 'pages outstanding 30 days percentage': 'total pages outstanding percentage greater than thirty days', 'pages outstanding 30 days percent': 'total pages outstanding percentage greater than thirty days', 'percentage of pages outstanding 30 days': 'total pages outstanding percentage greater than thirty days', 'percent of pages outstanding 30 days': 'total pages outstanding percentage greater than thirty days', 'pages outstanding > 30 days percentage': 'total pages outstanding percentage greater than thirty days', 'pages outstanding > 30 days percent': 'total pages outstanding percentage greater than thirty days', 'percentage of pages outstanding > 30 days': 'total pages outstanding percentage greater than thirty days', 'percent of pages outstanding > 30 days': 'total pages outstanding percentage greater than thirty days', 'outstanding pages 30 days percentage': 'total pages outstanding percentage greater than thirty days', 'outstanding pages 30 days percent': 'total pages outstanding percentage greater than thirty days', 'percentage of outstanding pages 30 days': 'total pages outstanding percentage greater than thirty days', 'percent of outstanding pages 30 days': 'total pages outstanding percentage greater than thirty days', 'outstanding pages greater than 30 days percentage': 'total pages outstanding percentage greater than thirty days', 'outstanding pages greater than 30 days percent': 'total pages outstanding percentage greater than thirty days', 'percentage of outstanding pages greater than 30 days': 'total pages outstanding percentage greater than thirty days', 'percent of outstanding pages greater than 30 days': 'total pages outstanding percentage greater than thirty days', 'outstanding pages > 30 days percentage': 'total pages outstanding percentage greater than thirty days', 'outstanding pages > 30 days percent': 'total pages outstanding percentage greater than thirty days', 'percentage of outstanding pages > 30 days': 'total pages outstanding percentage greater than thirty days', 'percent of outstanding pages > 30 days': 'total pages outstanding percentage greater than thirty days', 'total outstanding queries': 'total outstanding queries', 'queries outstanding': 'total outstanding queries', 'outstanding queries': 'total outstanding queries', 'number of outstanding queries': 'total outstanding queries', 'outstanding queries number': 'total outstanding queries', 'count of outstanding queries': 'total outstanding queries', 'outstanding queries count': 'total outstanding queries', 'sum of outstanding queries': 'total outstanding queries', 'query outstanding': 'total outstanding queries', 'outstanding query': 'total outstanding queries', 'number of outstanding query': 'total outstanding queries', 'outstanding query number': 'total outstanding queries', 'count of outstanding query': 'total outstanding queries', 'outstanding query count': 'total outstanding queries', 'sum of outstanding query': 'total outstanding queries', 'total open queries': 'total open queries', 'queries open': 'total open queries', 'open queries': 'total open queries', 'number of open queries': 'total open queries', 'open queries number': 'total open queries', 'count of open queries': 'total open queries', 'open queries count': 'total open queries', 'sum of open queries': 'total open queries', 'query open': 'total open queries', 'open query': 'total open queries', 'number of open query': 'total open queries', 'open query number': 'total open queries', 'count of open query': 'total open queries', 'open query count': 'total open queries', 'sum of open query': 'total open queries', 'total answered queries': 'total query', 'queries answered': 'total answered queries', 'answered queries': 'total query', 'number of answered queries': 'total query', 'answered queries number': 'total answered queries', 'count of answered queries': 'total query', 'answered queries count': 'total answered queries', 'sum of answered queries': 'total answered queries', 'query answered': 'total answered queries', 'answered query': 'total answered queries', 'number of answered query': 'total answered queries', 'answered query number': 'total answered queries', 'count of answered query': 'total answered queries', 'answered query count': 'total answered queries', 'sum of answered query': 'total answered queries', 'total outstanding (re-queries)': 'total outstanding (re-queries)', 'outstanding re-queries': 'total outstanding (re-queries)', 'number of outstanding re-queries': 'total outstanding (re-queries)', 'outstanding number re-queires': 'total outstanding (re-queries)', 'count of outstanding re-queries': 'total outstanding (re-queries)', 'outstanding count re-queries': 'total outstanding (re-queries)', 'sum of outstanding re-queries': 'total outstanding (re-queries)', 'number of outstanding re-queires': 'total outstanding (re-queries)', 'count of outstanding re-queires': 'total outstanding (re-queries)', 'outstanding re queries': 'total outstanding (re-queries)', 'number of outstanding re queries': 'total outstanding (re-queries)', 'outstanding number re queires': 'total outstanding (re-queries)', 'count of outstanding re queries': 'total outstanding (re-queries)', 'outstanding count re queries': 'total outstanding (re-queries)', 'sum of outstanding re queries': 'total outstanding (re-queries)', 'number of outstanding re queires': 'total outstanding (re-queries)', 'count of outstanding re queires': 'total outstanding (re-queries)', 'total outstanding (ipd queries)': 'total outstanding (ipd queries)', 'outstanding ipd-queries': 'total outstanding (ipd queries)', 'number of outstanding ipd-queries': 'total outstanding (ipd queries)', 'outstanding number ipd-queires': 'total outstanding (ipd queries)', 'count of outstanding ipd-queries': 'total outstanding (ipd queries)', 'outstanding count ipd-queries': 'total outstanding (ipd queries)', 'sum of outstanding ipd-queries': 'total outstanding (ipd queries)', 'number of outstanding ipd-queires': 'total outstanding (ipd queries)', 'count of outstanding ipd-queires': 'total outstanding (ipd queries)', 'outstanding ipd queries': 'total outstanding (ipd queries)', 'number of outstanding ipd queries': 'total outstanding (ipd queries)', 'outstanding number ipd queires': 'total outstanding (ipd queries)', 'count of outstanding ipd queries': 'total outstanding (ipd queries)', 'outstanding count ipd queries': 'total outstanding (ipd queries)', 'sum of outstanding ipd queries': 'total outstanding (ipd queries)', 'number of outstanding ipd queires': 'total outstanding (ipd queries)', 'count of outstanding ipd queires': 'total outstanding (ipd queries)', 'total outstanding queries zero to seven days': 'total outstanding queries zero to seven days', 'queries outstanding 0-5 days': 'total outstanding queries zero to seven days', 'queries outstanding 0 to 5 days': 'total outstanding queries zero to seven days', 'queries outstanding less than 5 days': 'total outstanding queries zero to seven days', 'queries outstanding < 5 days': 'total outstanding queries zero to seven days', 'queries outstanding <= 5 days': 'total outstanding queries zero to seven days', 'queries outstanding less than 7 days': 'total outstanding queries zero to seven days', 'queries outstanding < 7 days': 'total outstanding queries zero to seven days', 'queries outstanding <= 7 days': 'total outstanding queries zero to seven days', 'outstanding queries 0-5 days': 'total outstanding queries zero to seven days', 'outstanding queries 0 to 5 days': 'total outstanding queries zero to seven days', 'outstanding queries less than 5 days': 'total outstanding queries zero to seven days', 'outstanding queries < 5 days': 'total outstanding queries zero to seven days', 'outstanding queries<= 5 days': 'total outstanding queries zero to seven days', 'outstanding queries less than 7 days': 'total outstanding queries zero to seven days', 'outstanding queries< 7 days': 'total outstanding queries zero to seven days', 'outstanding queries<= 7 days': 'total outstanding queries zero to seven days', 'number of outstanding queries 0-5 days': 'total outstanding queries zero to seven days', 'number of outstanding queries 0 to 5 days': 'total outstanding queries zero to seven days', 'number of outstanding queries less than 5 days': 'total outstanding queries zero to seven days', 'number of outstanding queries < 5 days': 'total outstanding queries zero to seven days', 'number of outstanding queries<= 5 days': 'total outstanding queries zero to seven days', 'number of outstanding queries less than 7 days': 'total outstanding queries zero to seven days', 'number of outstanding queries< 7 days': 'total outstanding queries zero to seven days', 'number of outstanding queries<= 7 days': 'total outstanding queries zero to seven days', 'count of outstanding queries 0-5 days': 'total outstanding queries zero to seven days', 'count of outstanding queries 0 to 5 days': 'total outstanding queries zero to seven days', 'count of outstanding queries less than 5 days': 'total outstanding queries zero to seven days', 'count of outstanding queries < 5 days': 'total outstanding queries zero to seven days', 'count of outstanding queries<= 5 days': 'total outstanding queries zero to seven days', 'count of outstanding queries less than 7 days': 'total outstanding queries zero to seven days', 'count of outstanding queries< 7 days': 'total outstanding queries zero to seven days', 'count of outstanding queries<= 7 days': 'total outstanding queries zero to seven days', 'sum of outstanding queries 0-5 days': 'total outstanding queries zero to seven days', 'sum of outstanding queries 0 to 5 days': 'total outstanding queries zero to seven days', 'sum of outstanding queries less than 5 days': 'total outstanding queries zero to seven days', 'sum of outstanding queries < 5 days': 'total outstanding queries zero to seven days', 'sum of outstanding queries<= 5 days': 'total outstanding queries zero to seven days', 'sum of outstanding queries less than 7 days': 'total outstanding queries zero to seven days', 'sum of outstanding queries< 7 days': 'total outstanding queries zero to seven days', 'sum of outstanding queries<= 7 days': 'total outstanding queries zero to seven days', 'outstanding queries count 0-5 days': 'total outstanding queries zero to seven days', 'outstanding queries count 0 to 5 days': 'total outstanding queries zero to seven days', 'outstanding queries count less than 5 days': 'total outstanding queries zero to seven days', 'outstanding queries count < 5 days': 'total outstanding queries zero to seven days', 'outstanding queries count <= 5 days': 'total outstanding queries zero to seven days', 'outstanding queries count less than 7 days': 'total outstanding queries zero to seven days', 'outstanding queries count< 7 days': 'total outstanding queries zero to seven days', 'outstanding queries count <= 7 days': 'total outstanding queries zero to seven days', 'total outstanding queries eight to thirteen days': 'total outstanding queries eight to thirteen days', 'queries outstanding 8-13 days': 'total outstanding queries eight to thirteen days', 'queries outstanding 8 to 13 days': 'total outstanding queries eight to thirteen days', 'queries outstanding less than 13 days': 'total outstanding queries eight to thirteen days', 'queries outstanding < 13 days': 'total outstanding queries eight to thirteen days', 'queries outstanding <= 13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries 8-13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries 8 to 13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries less than 13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries < 13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries<= 13 days': 'total outstanding queries eight to thirteen days', 'number of outstanding queries 8-13 days': 'total outstanding queries eight to thirteen days', 'number of outstanding queries 8 to 13 days': 'total outstanding queries eight to thirteen days', 'number of outstanding queries less than 13 days': 'total outstanding queries eight to thirteen days', 'number of outstanding queries < 13 days': 'total outstanding queries eight to thirteen days', 'number of outstanding queries<= 13 days': 'total outstanding queries eight to thirteen days', 'count of outstanding queries 8-13 days': 'total outstanding queries eight to thirteen days', 'count of outstanding queries 8 to 13 days': 'total outstanding queries eight to thirteen days', 'count of outstanding queries less than 13 days': 'total outstanding queries eight to thirteen days', 'count of outstanding queries < 13 days': 'total outstanding queries eight to thirteen days', 'count of outstanding queries<= 13 days': 'total outstanding queries eight to thirteen days', 'sum of outstanding queries 8-13 days': 'total outstanding queries eight to thirteen days', 'sum of outstanding queries 8 to 13 days': 'total outstanding queries eight to thirteen days', 'sum of outstanding queries less than 13 days': 'total outstanding queries eight to thirteen days', 'sum of outstanding queries < 13 days': 'total outstanding queries eight to thirteen days', 'sum of outstanding queries<= 13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries count 8-13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries count 8 to 13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries count less than 13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries count < 13 days': 'total outstanding queries eight to thirteen days', 'outstanding queries count <= 13 days': 'total outstanding queries eight to thirteen days', 'total outstanding queries fourteen to twenty days': 'total outstanding queries fourteen to twenty days', 'queries outstanding 14-20 days': 'total outstanding queries fourteen to twenty days', 'queries outstanding 14 to 20 days': 'total outstanding queries fourteen to twenty days', 'queries outstanding less than 20 days': 'total outstanding queries fourteen to twenty days', 'queries outstanding < 20 days': 'total outstanding queries fourteen to twenty days', 'queries outstanding <= 20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries 14-20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries 14 to 20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries less than 20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries < 20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries<= 20 days': 'total outstanding queries fourteen to twenty days', 'number of outstanding queries 14-20 days': 'total outstanding queries fourteen to twenty days', 'number of outstanding queries 14 to 20 days': 'total outstanding queries fourteen to twenty days', 'number of outstanding queries less than 20 days': 'total outstanding queries fourteen to twenty days', 'number of outstanding queries < 20 days': 'total outstanding queries fourteen to twenty days', 'number of outstanding queries<= 20 days': 'total outstanding queries fourteen to twenty days', 'count of outstanding queries 14-20 days': 'total outstanding queries fourteen to twenty days', 'count of outstanding queries 14 to 20 days': 'total outstanding queries fourteen to twenty days', 'count of outstanding queries less than 20 days': 'total outstanding queries fourteen to twenty days', 'count of outstanding queries < 20 days': 'total outstanding queries fourteen to twenty days', 'count of outstanding queries<= 20 days': 'total outstanding queries fourteen to twenty days', 'sum of outstanding queries 14-20 days': 'total outstanding queries fourteen to twenty days', 'sum of outstanding queries 14 to 20 days': 'total outstanding queries fourteen to twenty days', 'sum of outstanding queries less than 20 days': 'total outstanding queries fourteen to twenty days', 'sum of outstanding queries < 20 days': 'total outstanding queries fourteen to twenty days', 'sum of outstanding queries<= 20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries count 14-20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries count 14 to 20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries count less than 20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries count < 20 days': 'total outstanding queries fourteen to twenty days', 'outstanding queries count <= 20 days': 'total outstanding queries fourteen to twenty days', 'total outstanding queries twenty one to fifty days': 'total outstanding queries twenty one to fifty days', 'queries outstanding 21-50 days': 'total outstanding queries twenty one to fifty days', 'queries outstanding 21 to 50 days': 'total outstanding queries twenty one to fifty days', 'queries outstanding less than 50 days': 'total outstanding queries twenty one to fifty days', 'queries outstanding < 50 days': 'total outstanding queries twenty one to fifty days', 'queries outstanding <= 50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries 21-50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries 21 to 50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries less than 50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries < 50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries<= 50 days': 'total outstanding queries twenty one to fifty days', 'number of outstanding queries 21-50 days': 'total outstanding queries twenty one to fifty days', 'number of outstanding queries 21 to 50 days': 'total outstanding queries twenty one to fifty days', 'number of outstanding queries less than 50 days': 'total outstanding queries twenty one to fifty days', 'number of outstanding queries < 50 days': 'total outstanding queries twenty one to fifty days', 'number of outstanding queries<= 50 days': 'total outstanding queries twenty one to fifty days', 'count of outstanding queries 21-50 days': 'total outstanding queries twenty one to fifty days', 'count of outstanding queries 21 to 50 days': 'total outstanding queries twenty one to fifty days', 'count of outstanding queries less than 50 days': 'total outstanding queries twenty one to fifty days', 'count of outstanding queries < 50 days': 'total outstanding queries twenty one to fifty days', 'count of outstanding queries<= 50 days': 'total outstanding queries twenty one to fifty days', 'sum of outstanding queries 21-50 days': 'total outstanding queries twenty one to fifty days', 'sum of outstanding queries 21 to 50 days': 'total outstanding queries twenty one to fifty days', 'sum of outstanding queries less than 50 days': 'total outstanding queries twenty one to fifty days', 'sum of outstanding queries < 50 days': 'total outstanding queries twenty one to fifty days', 'sum of outstanding queries<= 50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries count 21-50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries count 21 to 50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries count less than 50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries count < 50 days': 'total outstanding queries twenty one to fifty days', 'outstanding queries count <= 50 days': 'total outstanding queries twenty one to fifty days', 'total outstanding queries greater than fifty days': 'total outstanding queries greater than fifty days', 'queries outstanding greater than 50 days': 'total outstanding queries greater than fifty days', 'queries outstanding 50 days': 'total outstanding queries greater than fifty days', 'queries outstanding > 50 days': 'total outstanding queries greater than fifty days', 'outstanding queries 50 days': 'total outstanding queries greater than fifty days', 'outstanding queries greater than 50 days': 'total outstanding queries greater than fifty days', 'outstanding queries > 50 days': 'total outstanding queries greater than fifty days', 'number of outstanding queries 50 days': 'total outstanding queries greater than fifty days', 'number of outstanding queries greater than 50 days': 'total outstanding queries greater than fifty days', 'number of outstanding queries > 50 days': 'total outstanding queries greater than fifty days', 'count of outstanding queries 50 days': 'total outstanding queries greater than fifty days', 'count of outstanding queries greater than 50 days': 'total outstanding queries greater than fifty days', 'count of outstanding queries > 50 days': 'total outstanding queries greater than fifty days', 'sum of outstanding queries 50 days': 'total outstanding queries greater than fifty days', 'sum of outstanding queries greater than 50 days': 'total outstanding queries greater than fifty days', 'sum of outstanding queries > 50 days': 'total outstanding queries greater than fifty days', 'outstanding queries count 50 days': 'total outstanding queries greater than fifty days', 'outstanding queries count greater than 50 days': 'total outstanding queries greater than fifty days', 'outstanding queries count > 50 days': 'total outstanding queries greater than fifty days', 'outstanding queries count >= 50 days': 'total outstanding queries greater than fifty days', 'percentage of total outstanding queries greater than fifty days': 'percentage of total outstanding queries greater than fifty days', 'queries outstanding greater than 50 days percentage': 'percentage of total outstanding queries greater than fifty days', 'queries outstanding greater than 50 days percent': 'percentage of total outstanding queries greater than fifty days', 'percentage of queries outstanding greater than 50 days': 'percentage of total outstanding queries greater than fifty days', 'percent of queries outstanding greater than 50 days': 'percentage of total outstanding queries greater than fifty days', 'queries outstanding 50 days percentage': 'percentage of total outstanding queries greater than fifty days', 'queries outstanding 50 days percent': 'percentage of total outstanding queries greater than fifty days', 'percentage of queries outstanding 50 days': 'percentage of total outstanding queries greater than fifty days', 'percent of queries outstanding 50 days': 'percentage of total outstanding queries greater than fifty days', 'queries outstanding > 50 days percentage': 'percentage of total outstanding queries greater than fifty days', 'queries outstanding > 50 days percent': 'percentage of total outstanding queries greater than fifty days', 'percentage of queries outstanding > 50 days': 'percentage of total outstanding queries greater than fifty days', 'percent of queries outstanding > 50 days': 'percentage of total outstanding queries greater than fifty days', 'outstanding queries 50 days percentage': 'percentage of total outstanding queries greater than fifty days', 'outstanding queries 50 days percent': 'percentage of total outstanding queries greater than fifty days', 'percentage of outstanding queries 50 days': 'percentage of total outstanding queries greater than fifty days', 'percent of outstanding queries 50 days': 'percentage of total outstanding queries greater than fifty days', 'outstanding queries greater than 50 days percentage': 'percentage of total outstanding queries greater than fifty days', 'outstanding queries greater than 50 days percent': 'percentage of total outstanding queries greater than fifty days', 'percentage of outstanding queries greater than 50 days': 'percentage of total outstanding queries greater than fifty days', 'percent of outstanding queries greater than 50 days': 'percentage of total outstanding queries greater than fifty days', 'outstanding queries > 50 days percentage': 'percentage of total outstanding queries greater than fifty days', 'outstanding queries > 50 days percent': 'percentage of total outstanding queries greater than fifty days', 'percentage of outstanding queries > 50 days': 'percentage of total outstanding queries greater than fifty days', 'percent of outstanding queries > 50 days': 'percentage of total outstanding queries greater than fifty days', 'total pages forecasted': 'total pages forecasted', 'number of forecasted pages': 'total pages forecasted', 'count of forecasted pages': 'total pages forecasted', 'sum of forecasted pages': 'total pages forecasted', 'pages forecasted': 'total pages forecasted', 'number of pages forecasted': 'total pages forecasted', 'count of pages forecasted': 'total pages forecasted', 'forcasted pages': 'total pages forecasted', 'total pages forecasted (site)': 'total pages forecasted (site)', 'number of forecasted pages (site)': 'total pages forecasted (site)', 'count of forecasted pages (site)': 'total pages forecasted (site)', 'sum of forecasted pages (site)': 'total pages forecasted (site)', 'pages forecasted (site)': 'total pages forecasted (site)', 'number of pages forecasted (site)': 'total pages forecasted (site)', 'count of pages forecasted (site)': 'total pages forecasted (site)', 'forcasted pages (site)': 'total pages forecasted (site)', 'total pages forecasted (non-site)': 'total pages forecasted (non-site)', 'number of forecasted pages (non-site)': 'total pages forecasted (non-site)', 'count of forecasted pages (non-site)': 'total pages forecasted (non-site)', 'sum of forecasted pages (non-site)': 'total pages forecasted (non-site)', 'pages forecasted (non-site)': 'total pages forecasted (non-site)', 'number of pages forecasted (non-site)': 'total pages forecasted (non-site)', 'count of pages forecasted (non-site)': 'total pages forecasted (non-site)', 'forcasted pages (non-site)': 'total pages forecasted (non-site)', 'total pages forecasted to be inactivated': 'total pages forecasted to be inactivated', 'number of pages forecasted to be inactivated': 'total pages forecasted to be inactivated', 'sum of pages forecasted to be inactivated': 'total pages forecasted to be inactivated', 'count of pages forecasted to be inactivated': 'total pages forecasted to be inactivated', 'pages forecasted to be inactivated': 'total pages forecasted to be inactivated', 'total forecasted blank pages': 'total forecasted blank pages', 'number of forecasted blank pages': 'total forecasted blank pages', 'count of forecasted blank pages': 'total forecasted blank pages', 'forecasted blank pages': 'total forecasted blank pages', 'total submitted pages': 'total submitted pages', 'number of submitted pages': 'total submitted pages', 'count of submitted pages': 'total submitted pages', 'submitted pages': 'total submitted pages', 'number of pages submitted': 'total submitted pages', 'count of pages submitted': 'total submitted pages', 'pages submitted': 'total submitted pages', 'pages submitted <=7days': 'pages submitted <=7days', 'number of submitted pages <=7days': 'pages submitted <=7days', 'count of submitted pages <=7days': 'pages submitted <=7days', 'submitted pages <=7days': 'pages submitted <=7days', 'number of pages submitted <=7days': 'pages submitted <=7days', 'count of pages submitted <=7days': 'pages submitted <=7days', 'number of submitted pages less than equal to 7 days': 'pages submitted <=7days', 'count of submitted pages less than equal to 7 days': 'pages submitted <=7days', 'submitted pages less than equal to 7 days': 'pages submitted <=7days', 'number of pages submitted less than equal to 7 days': 'pages submitted <=7days', 'count of pages submitted less than equal to 7 days': 'pages submitted <=7days', 'pages submitted less than equal to 7 days': 'pages submitted <=7days', 'pages submitted <=15 days': 'pages submitted <=15 days', 'number of submitted pages <=15 days': 'pages submitted <=15 days', 'count of submitted pages <=15 days': 'pages submitted <=15 days', 'submitted pages <=15 days': 'pages submitted <=15 days', 'number of pages submitted <=15 days': 'pages submitted <=15 days', 'count of pages submitted <=15 days': 'pages submitted <=15 days', 'number of submitted pages less than equal to 15 days': 'pages submitted <=15 days', 'count of submitted pages less than equal to 15 days': 'pages submitted <=15 days', 'submitted pages less than equal to 15 days': 'pages submitted <=15 days', 'number of pages submitted less than equal to 15 days': 'pages submitted <=15 days', 'count of pages submitted less than equal to 15 days': 'pages submitted <=15 days', 'pages submitted less than equal to 15 days': 'pages submitted <=15 days', 'pages submitted >90 days': 'pages submitted >90 days', 'number of submitted pages >90 days': 'pages submitted >90 days', 'count of submitted pages >90 days': 'pages submitted >90 days', 'submitted pages >90 days': 'pages submitted >90 days', 'number of pages submitted >90 days': 'pages submitted >90 days', 'count of pages submitted >90 days': 'pages submitted >90 days', 'number of submitted pages greater than 90 days': 'pages submitted >90 days', 'count of submitted pages greater than 90 days': 'pages submitted >90 days', 'submitted pages greater than 90 days': 'pages submitted >90 days', 'number of pages submitted greater than 90 days': 'pages submitted >90 days', 'count of pages submitted greater than 90 days': 'pages submitted >90 days', 'pages submitted greater than 90 days': 'pages submitted >90 days', 'total query': 'total query', 'number of queries': 'total query', 'count of queries': 'total query', 'closed queries': 'total query', 'answered/closed queries': 'total query', 'number of answered/closed queries': 'total query', 'count of answered/closed queries': 'total query', 'queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'number of queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'count of queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'answered queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'closed queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'answered/closed queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'number of answered queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'count of answered queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'number of answered/closed queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'count of answered/closed queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'total answered queries <=7days open to answer/closed': 'queries <=7days open to answer/closed', 'queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'number of queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'count of queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'answered queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'closed queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'answered/closed queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'number of answered queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'count of answered queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'number of answered/closed queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'count of answered/closed queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'total answered queries 8-13 days open to answered/closed': 'queries 8-13 days open to answered/closed', 'queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'number of queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'count of queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'answered queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'closed queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'answered/closed queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'number of answered queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'count of answered queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'number of answered/closed queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'count of answered/closed queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'total answered queries 14-20 days open to answered/closed': 'queries 14-20 days open to answered/closed', 'queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'number of queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'count of queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'answered queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'closed queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'answered/closed queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'number of answered queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'count of answered queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'number of answered/closed queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'count of answered/closed queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'total answered queries 21-50 days open to answered/closed': 'queries 21-50 days open to answered/closed', 'queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'number of queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'count of queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'answered queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'closed queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'answered/closed queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'number of answered queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'count of answered queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'number of answered/closed queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'count of answered/closed queries >50 days open to answered/closed': 'queries >50 days open to answered/closed', 'total answered queries >50 days open to answered/closed': 'queries >50 days open to answered/closed'}

											  
							   
							   
											  
        spell_check = list(itertools.chain.from_iterable(
            [i.lower().split() for i in synonyms_metrics]))

        if json_input:
            if len(json_input['currentIntent']['slotDetails']['metric_name']['resolutions']) > 1:
                role_list = [i['value']for i in json_input['currentIntent']
                             ['slotDetails']['metric_name']['resolutions']]
                if json_input['currentIntent']['slotDetails']['metric_name']['originalValue'] in role_list:
                    return [json_input['currentIntent']['slotDetails']['metric_name']['originalValue']]
                else:
                    return role_list

    if context == "collibra":
        try:
            data = read_excel("Collibra.xlsx", "BTM")
            data = data[data.Type == "Metric"]
        except:
            return ("oops..! seems like our databases have some problem, please try after some time thanks.")
        synonyms_metrics = list(set(data['Name']))
        synonyms_metrics = [ item.lower() for item in synonyms_metrics]
        
        spell_check = list(itertools.chain.from_iterable(
            [i.lower().split() for i in synonyms_metrics]))
																   
							   
        
        
        if json_input:
            role_list = []
            if metric_name and metric_name.lower() in synonyms_metrics:
                logger.info(f'Func find_metric_match \n metric_name found in synonyms_metrics: {metric_name}')
					   
																								 
																		   
																		   
                return [metric_name], True

            metric_matches = rapidfuzz_matches(metric_name, synonyms_metrics, threshold = 80, limit = 3)
            return metric_matches, False

    if context == "enrollment hub":
        #new_hub_info = find_metric_match(hub_info, "enrollment hub")
        try:
            data = read_excel("Enrollment.xlsx", "Sheet1")
        except:
            return ("oops..! seems like our databases have some problem, please try after some time thanks.")
        synonyms_metrics = [str(i) for i in list(set(data['HUB']))]
        spell_check = list(itertools.chain.from_iterable(
            [i.lower().split() for i in synonyms_metrics]))

    if context == "enrollment gmo":
        try:
            data = read_excel("Enrollment.xlsx", "Sheet1")
        except:
            return ("oops..! seems like our databases have some problem, please try after some time thanks.")
        synonyms_metrics = [str(i) for i in list(set(data['GMO Region']))]
        spell_check = list(itertools.chain.from_iterable(
            [i.lower().split() for i in synonyms_metrics]))

    if context == "enrollment gdo":
        try:
            data = read_excel("Enrollment.xlsx", "Sheet1")
        except:
            return ("oops..! seems like our databases have some problem, please try after some time thanks.")
        synonyms_metrics = [str(i) for i in list(set(data['GDO Region']))]
        spell_check = list(itertools.chain.from_iterable(
            [i.lower().split() for i in synonyms_metrics]))

    if context == "country":
        try:
            data = read_excel("Enrollment.xlsx", "Sheet1")
        except:
            return ("oops..! seems like our databases have some problem, please try after some time thanks.")
        synonyms_metrics = [str(i) for i in list(set(data['Country']))]
        spell_check = list(itertools.chain.from_iterable(
            [i.lower().split() for i in synonyms_metrics]))

    if context == "cap rule":
        return_list = []
        if json_input:
            metric_name = metric_name.lower()
            data = read_excel("CAPRule.xlsx", "Sheet1")
            business_rule_list = data['BUSINESS_RULE'].unique()
            business_rule_list = [ item.lower() for item  in business_rule_list]
            business_rule_first_last = [first_and_last(item) for item in business_rule_list]
            logger.info(f'Func find_metric_match  \n metric_name : {metric_name} \n context: {context} \n  business_rule_list: {business_rule_list}')
            if metric_name in business_rule_first_last:
                actual_metric_name = [item for item in business_rule_list if first_and_last(item) == metric_name]
                logger.info(f'Func find_metric_match EXACT MATCH \n metric_name : {metric_name} IN  business_rule_list: {business_rule_list}')
                return actual_metric_name, True
            else:
                match_list = rapidfuzz_matches(metric_name, business_rule_list, threshold = 80, limit = 3)
                match_list = [first_and_last(item) for item in match_list]
                logger.info(f'Func find_metric_match NO EXACT MATCH \n match_list : {match_list} \n  metric_name: {metric_name}')
                return match_list, False

            resolutions = try_ex(lambda: json_input['currentIntent']['slotDetails']['business_rule']['resolutions'])
            if resolutions and len(resolutions) > 1:
                role_list = [i['value']for i in json_input['currentIntent']
                             ['slotDetails']['business_rule']['resolutions']]
                logger.info(f'Func find_metric_match \n role_list: {role_list}')
                if json_input['currentIntent']['slotDetails']['business_rule']['originalValue'] in role_list:
                    logger.info(f'Func find_metric_match \n Original value in rolelist: {business_rule}')
                    return [business_rule]

                else:
                    all_values = role_list
                    for i in all_values:
                        if len(i) > 49:
                            return_list.append(first_and_last(i))
                        else:
                            return_list.append(i)
                    logger.info(f'Func find_metric_match \n return_list: {return_list}')
                    return return_list
            else:
                logger.info(f'Func find_metric_match \n resolutions <= 1 \n resolutions: {resolutions} \n metric_name: {metric_name}')
                return [metric_name]

    if not difflib.get_close_matches(metric_name, synonyms_metrics, n=3, cutoff=1):
        logger.info(f'Func find_metric_match \n difflib in synonyms_metrics')
        metric_name_list = metric_name.lower().split()
        word_to_complete = ""
        completed_word = []
																 
								
        for i in metric_name_list:
            try:
                word_to_complete = difflib.get_close_matches(i, spell_check)[0]

            except IndexError:
                pass

            completed_word.append(
                set([word for word in synonyms_metrics if word_to_complete in word.lower()]))

        try:
            all_values = list(set.intersection(*completed_word))
            if len(all_values) == 1:
                return (all_values)

        except:
            return [0]
        if context == "metric value":
            return list(set(map(lambda x: synonyms_metrics.get(x), all_values)))[0:10]
        else:
            all_values = all_values[0:10]
            return [i[:48] for i in all_values]
    else:
        if context == "metric value":
            return [synonyms_metrics.get(metric_name)]

        else:
            return [metric_name]


def validate_cap_rule_information_intent(intent_request):
    logger.info(f"Func: validate_cap_rule_information_intent \n intent_request: {intent_request} ")
    """
      Validating all the user input/ Rules for CAP Rule.
    """
						   
																		  
					   
																	  

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
									   
																

    business_rule = try_ex(lambda : session_attributes['business_rule'])
    logger.info(f"Func: validate_cap_rule_information_intent \n From session_attributes  business_rule: {business_rule} ")
    rule_type = try_ex(
        lambda: intent_request['currentIntent']['slots']['rule_type'])

    
    business_rule_retry_count = try_ex(
        lambda: session_attributes['business_rule_retry_count'])
    
    if not business_rule_retry_count:
        session_attributes['business_rule_retry_count'] = 0 
        
    slots = {'business_rule': business_rule, 'rule_type': rule_type}
    
    # new version
    if business_rule:
        logger.info(f"Func: validate_cap_rule_information_intent  \n HAS business_rule: {business_rule} ")
        
        new_business_rule, exact_match = find_metric_match(business_rule, "cap rule", intent_request)
        logger.info(f"Func: validate_cap_rule_information_intent \n new_business_rule: {new_business_rule} \n exact_match :{exact_match} ")
        data = read_excel("CAPRule.xlsx", "Sheet1")
        if new_business_rule and exact_match:
            session_attributes['business_rule'] = new_business_rule[0]
            businessRule = data[data['BUSINESS_RULE'].str.lower() == new_business_rule[0]]
            rule = list(businessRule['RULE_TYPE'].unique())

            if len(rule) > 1 and not rule_type:
                response_card = build_response_card(rule)
                logger.info(f"Func: validate_cap_rule_information_intent \n rule \n : {rule} ")
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'rule_type',
                                           "Next, select the rule type: <br>",
                                           response_card)
            elif rule_type:
                slots = {
                    'business_rule': new_business_rule[0], 'rule_type': rule_type}
            elif len(rule) == 1:
                slots = {
                    'business_rule': new_business_rule[0], 'rule_type': rule[0]}
            logger.info(f"Func: validate_cap_rule_information_intent \n delegate called \n session_attributes : {session_attributes} \n slots : {slots} ")
            return delegate(session_attributes, slots)
        elif len(new_business_rule) > 1:
                    response_card = build_response_card(new_business_rule, include_no=True)
                    logger.info(f"Func: validate_cap_rule_information_intent \n new_business_rule \n : {new_business_rule} ")
                    return elicit_slot_buttons(session_attributes,
                                               intent_request['currentIntent']['name'],
                                               slots,
                                               'business_rule',
                                               "Please choose from options below: <br>",
                                               response_card)
        elif not new_business_rule:
            session_attributes['business_rule_retry_count'] += 1
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                'business_rule',
                "Sorry, I could not find the <b> {} </b>  rule. Could you please try again with different rule? ".format(
                    business_rule)
            )
    else:
        if not business_rule:
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'business_rule',
                               "You have selected <b> CAP </b> , Great! <br>Kindly enter the CAP rule which I can assist you with: <br>")
            
            
    # OLd version
    logger.info(f"Func: validate_cap_rule_information_intent  OLD VERSION \n  business_rule: {business_rule} ")
    if business_rule:
        logger.info(f"Func: validate_cap_rule_information_intent  \n HAS business_rule: {business_rule} ")
        
        new_business_rule, exact_match = find_metric_match(business_rule, "cap rule", intent_request)
        logger.info(f"Func: validate_cap_rule_information_intent \n new_business_rule: {new_business_rule} \n exact_match :{exact_match} ")
        data = read_excel("CAPRule.xlsx", "Sheet1")
        
        if new_business_rule and exact_match:
            session_attributes['business_rule'] = new_business_rule[0]
            rule = list(businessRule['RULE_TYPE'].unique())
            if len(rule) > 1 and not rule_type:
                response_card = build_response_card(rule)
                logger.info(f"Func: validate_cap_rule_information_intent \n rule \n : {rule} ")
                    
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'rule_type',
                                           "Next, select the rule type: <br>",
                                           response_card)
            elif len(rule) == 1 and not rule_type:
                slots = {
                    'business_rule': new_business_rule[0], 'rule_type': rule[0]}
        elif new_business_rule and not exact_match:
            if len(new_business_rule) > 1:
                session_attributes['business_rule_retry_count'] = int(
                    session_attributes['business_rule_retry_count'])+1
																																						   
                response_card = build_response_card(
                    new_business_rule, include_no=True)
                logger.info(f"Func: validate_cap_rule_information_intent \n new_business_rule \n : {new_business_rule} ")
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'business_rule',
                                           "Please choose from options below: <br>",
                                           response_card)

            slots = {
                'business_rule': new_business_rule[0], 'rule_type': rule_type}
            businessRule = data[data['BUSINESS_RULE']
                                == (new_business_rule[0])]
        else:
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'business_rule',
                               "You have selected <b> CAP </b> , Great! <br>Kindly enter the CAP rule which I can assist you with: <br>")
        try_ex(lambda: session_attributes.pop('slot_business_rule_called'))
        rule = list(businessRule['RULE_TYPE'].unique())
        if len(rule) == 1 and not rule_type:
            slots = {
                'business_rule': new_business_rule[0], 'rule_type': rule[0]}
        if len(rule) > 1 and not rule_type:
            response_card = build_response_card(rule)
            logger.info(f"Func: validate_cap_rule_information_intent \n rule \n : {rule} ")
                
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       'rule_type',
                                       "Next, select the rule type: <br>",
                                       response_card)
    
    logger.info(f"Func: validate_cap_rule_information_intent \n delegate called \n session_attributes : {session_attributes} \n slots : {slots} ")
    return delegate(session_attributes, slots)


def information_retrieval_rapidfuzz(user_input, area=None, threshold = 80):
																							
    """
    This funtion will take two argument user_input and area- for filtering the data(not mandatory)
    using tfidf bigram algorithm to match the user input and that of FAQ Data
    this function will return the string
    """
    logger.info(f"Func: information_retrieval_rapidfuzz \n user_input: {user_input} \n area: {area} ")
    try:
        data = read_excel("FAQ.xlsx", "Sheet1")

    except:
        return ("oops..! seems like our databases have some problem, please try after some time thanks.")
    if area:
        data = data[data['Area'] == area]
    data.drop_duplicates(subset=['Question'], inplace=True)
															
    choices_list = data['Question'].tolist()
    current_match = ''
    for choices in batch(choices_list, 4000):
        matches = rapidfuzz_matches(user_input, choices, threshold = threshold, limit = 1, return_type = "match_thres", choice_verbose = False)
        if matches:
            [(match, thres)] = matches
            threshold = max(thres, threshold)
            if match:
                current_match = match
            print(f"Func: information_retrieval_rapidfuzz \n matches: {matches} current_match : {current_match}")
    if current_match:
        response = data[data['Question'] == current_match]['Answer'].item()
    else:
        response = data.Answer[0]
    
    logger.info(f"Func: information_retrieval_rapidfuzz \n response: {response} \n len of choices: {len(choices_list)} ")
    return "<font size=2>" + (response) + "</font>"




def fulfill_dashboard_metric_value(session_attributes, slots):
    logger.info(f"Func: fulfill_dashboard_metric_value \n session_attributes: {session_attributes} \n slots: {slots} ")

    """
       This function is related to Metric Value fullfillment. 
       It accepts two parameters - Session attributes & Slots.
       This funtcion assembles the information from database and validates the response.
       Also, it prepares Text message consists of all selected filters which will be shown of chatbot window.
       
    """
    percentage_dict = {"SIGNED_GREATER_THAN_NINETY_DAY": "sum(SIGNED_GREATER_THAN_NINETY_DAY)*100/sum(TOTAL_SIGNED),sum(SIGNED_GREATER_THAN_NINETY_DAY)", "GREATER_THAN_THIRTY_DAYS": "sum(GREATER_THAN_THIRTY_DAYS)*100/sum(TOTAL_PAGES_OUTSTANDING),sum(GREATER_THAN_THIRTY_DAYS)", "PERCENTAGE_GREATER_THAN_THIRTY": "sum(GREATER_THAN_THIRTY_DAYS)*100/sum(TOTAL_PAGES_OUTSTANDING),sum(GREATER_THAN_THIRTY_DAYS)", "GREATER_THAN_FIFTY_DAYS": "sum(GREATER_THAN_FIFTY_DAYS)*100/sum(TOTAL_OPEN_QUERIES),sum(GREATER_THAN_FIFTY_DAYS)", "PERCENTAGE_GREATER_THAN_FIFTY_": "sum(GREATER_THAN_FIFTY_DAYS)*100/sum(TOTAL_OPEN_QUERIES),sum(GREATER_THAN_FIFTY_DAYS)", "PERCENTAGE_SIGNED_LESS_THAN_OR": "sum(SIGNED_LESS_THAN_OR_EQUAL_TO_T)*100/sum(TOTAL_SIGNED),sum(SIGNED_LESS_THAN_OR_EQUAL_TO_T)", "SIGNED_LESS_THAN_OR_EQUAL_TO_T":  "sum(SIGNED_LESS_THAN_OR_EQUAL_TO_T)*100/sum(TOTAL_SIGNED),sum(SIGNED_LESS_THAN_OR_EQUAL_TO_T)", "PERCENTAGE_FORMS_SIGNED_LESS_T": "sum(MILESTONE_FORMS_SIGNED_LESS_TH)*100/sum(TOTAL_MILESTONE_FORMS_SIGNED),sum(MILESTONE_FORMS_SIGNED_LESS_TH)", "MILESTONE_FORMS_SIGNED_LESS_TH": "sum(MILESTONE_FORMS_SIGNED_LESS_TH)*100/sum(TOTAL_MILESTONE_FORMS_SIGNED),sum(MILESTONE_FORMS_SIGNED_LESS_TH)", "PAGES_SUBMITTED_LESS_THAN_OR_E": "sum(PAGES_SUBMITTED_LESS_THAN_OR_E)*100/sum(TOTAL_SUBMITTED),sum(PAGES_SUBMITTED_LESS_THAN_OR_E)", "PERCENTAGE_PAGES_SUBMITTED_LE": "sum(PAGES_SUBMITTED_LESS_THAN_OR_E)*100/sum(TOTAL_SUBMITTED),sum(PAGES_SUBMITTED_LESS_THAN_OR_E)",
                       "PAGES_SUBMITTED_LESS_THAN_OR_": "sum(PAGES_SUBMITTED_LESS_THAN_OR_)*100/sum(TOTAL_SUBMITTED),sum(PAGES_SUBMITTED_LESS_THAN_OR_)", "PERCENTAGE_PAGES_SUBMITTED_LES": "sum(PAGES_SUBMITTED_LESS_THAN_OR_)*100/sum(TOTAL_SUBMITTED),sum(PAGES_SUBMITTED_LESS_THAN_OR_)", "PAGES_SUBMITTED_GREATER_THAN_N": "sum(PAGES_SUBMITTED_GREATER_THAN_N)*100/sum(TOTAL_SUBMITTED),sum(PAGES_SUBMITTED_GREATER_THAN_N)", "PERCENTAGE_PAGES_SUBMITTED_GRE": "sum(PAGES_SUBMITTED_GREATER_THAN_N)*100/sum(TOTAL_SUBMITTED),sum(PAGES_SUBMITTED_GREATER_THAN_N)", "PERCENTAGE_SIGNATURE_COMPLETE_": "(1-(sum(TOTAL_SIGNATURES_OUTSTANDING)/sum(PERCENTAGE_SIGNATURE_COMPLETE_)))*100,sum(PERCENTAGE_SIGNATURE_COMPLETE_)", "GREATER_THAN_FIFTY_DAYS_OPEN_": "sum(GREATER_THAN_FIFTY_DAYS_OPEN_)*100/sum(TOTAL_QUERY_COUNT),sum(GREATER_THAN_FIFTY_DAYS_OPEN_)", "LESS_THAN_OR_EQUAL_TO_SEVEN_DA": "sum(LESS_THAN_OR_EQUAL_TO_SEVEN_DA)*100/sum(TOTAL_QUERY_COUNT),sum(LESS_THAN_OR_EQUAL_TO_SEVEN_DA)", "EIGHT_TO_THIRTEEN_DAYS_OPEN_TO": "sum(EIGHT_TO_THIRTEEN_DAYS_OPEN_TO)*100/sum(TOTAL_QUERY_COUNT),sum(EIGHT_TO_THIRTEEN_DAYS_OPEN_TO)", "FOURTEEN_TO_TWENTY_DAYS_OPEN_T": "sum(FOURTEEN_TO_TWENTY_DAYS_OPEN_T)*100/sum(TOTAL_QUERY_COUNT),sum(FOURTEEN_TO_TWENTY_DAYS_OPEN_T)", "TWENTYONE_TO_FIFTY_DAYS_OPEN_": "sum(TWENTYONE_TO_FIFTY_DAYS_OPEN_)*100/sum(TOTAL_QUERY_COUNT),sum(TWENTYONE_TO_FIFTY_DAYS_OPEN_)"}
    table_name = session_attributes['table_name']
    metric_name_colummn_mapper = {'total unforecasted unsubmitted pages': 'TOTAL_PAGES', 'total unforecasted unsubmitted site pages': 'TOTAL_SITE_PAGES', 'total unforecasted unsubmitted  non-site pages': 'TOTAL_NON_SITE_PAGES', 'in activated pages non-site entered data not present': 'NON_SITE_ENTERED_DATA_NOT_PRES', 'queries >50 days open to answered/closed': 'GREATER_THAN_FIFTY_DAYS_OPEN_', 'in activated pages non-site entered data present': 'NON_SITE_ENTERED_DATA_PRESENT', 'in activated pages site entered data not present': 'SITE_ENTERED_DATA_NOT_PRESENT', 'in activated pages site entered data present': 'SITE_ENTERED_DATA_PRESENT', 'total signatures outstanding': 'TOTAL_SIGNATURES_OUTSTANDING', '% signature complete (all types)': 'PERCENTAGE_SIGNATURE_COMPLETE_', 'milestone signatures outstanding': 'MILESTONE_SIGNATURES_OUTSTANDI', 'visit signatures outstanding': 'VISIT_SIGNATURES_OUTSTANDING', 'other signatures outstanding': 'OTHER_SIGNATURES_OUTSTANDING', 'total signatures outstanding zero to thirty days': 'OUTSTANDING_ZERO_TO_THIRTY_DAY', 'total signatures outstanding thirtyone to sixty days': 'OUTSTANDING_THIRTY_ONE_TO_SIXT', 'total signatures outstanding sixty one to ninety days': 'OUTSTANDING_SIXTY_ONE_TO_NINET', 'total signatures outstanding greater than ninety days': 'OUTSTANDING_GREATER_THAN_NINET', 'total milestone forms signed': 'TOTAL_MILESTONE_FORMS_SIGNED', 'average number of days for total milestone forms signed': 'AVERAGE_NUM_DAYS', '% of milestone forms signed <= 3 days': 'PERCENTAGE_FORMS_SIGNED_LESS_T', 'milestone forms signed less than or equal to three days': 'MILESTONE_FORMS_SIGNED_LESS_TH', 'milestone forms signed four to six days': 'MILESTONE_FORMS_SIGNED_FOUR_TO', 'milestone forms signed seven to ten days': 'MILESTONE_FORMS_SIGNED_SEVEN_T', 'milestone forms signed greater than ten days': 'MILESTONE_FORMS_SIGNED_GREATER', 'visit signatures total signed': 'TOTAL_SIGNED', 'visit signatures % signed <= 30 days': 'PERCENTAGE_SIGNED_LESS_THAN_OR', 'visit signatures signed less than or equal to thirty days': 'SIGNED_LESS_THAN_OR_EQUAL_TO_T', 'visit signatures signed thirty one to sixty days': 'SIGNED_THIRTY_ONE_TO_SIXTY_DAY', 'visit signatures signed sixtyone to ninety days': 'SIGNED_SIXTY_ONE_NINETY_DAYS', 'visit signatures signed greater than ninety days': 'SIGNED_GREATER_THAN_NINETY_DAY', 'in active logline on active page non-site entered data not present': 'NON_SITE_ENTERED_DATA_NOT_PRES', 'in active logline on active page non-site entered data present': 'NON_SITE_ENTERED_DATA_PRESENT',
                                  'in active logline on active page site entered data not present': 'SITE_ENTERED_DATA_NOT_PRESENT', 'in active logline on active page site entered data present': 'SITE_ENTERED_DATA_PRESENT', 'total pages outstanding': 'TOTAL_PAGES_OUTSTANDING', 'total pages outstanding (site)': 'TOTAL_PAGES_OUTSTANDING_SITE', 'total pages outstanding (non-site)': 'TOTAL_PAGES_OUTSTANDING_NONSIT', 'total pages to be inactivated': 'TOTAL_PAGES_TO_BE_INACTIVATED', 'total outstanding blank pages': 'TOTAL_BLANK_PAGES', 'total pages outstanding zero to five days': 'ZERO_TO_FIVE_DAYS', 'total pages outstanding six to fifteen days': 'SIX_TO_FIFTEEN_DAYS', 'total pages outstanding sixteen to thirty days': 'SIXTEEN_TO_THIRTY_DAYS', 'total pages outstanding greater than thirty days': 'GREATER_THAN_THIRTY_DAYS', 'total pages outstanding percentage greater than thirty days': 'PERCENTAGE_GREATER_THAN_THIRTY', 'total outstanding queries': 'TOTAL_OUTSTANDING_QUERIES', 'total open queries': 'TOTAL_OPEN_QUERIES', 'total answered queries': 'TOTAL_ANSWERED_QUERIES', 'total query': 'TOTAL_QUERY_COUNT', 'total outstanding (re-queries)': 'TOTAL_OUTSTANDING_RE_QUERIES', 'total outstanding (ipd queries)': 'TOTAL_OUTSTANDING_IPD_QUERIES', 'total outstanding queries zero to seven days': 'ZERO_TO_SEVEN_DAYS', 'total outstanding queries eight to thirteen days': 'EIGHT_TO_THIRTEEN_DAYS', 'total outstanding queries fourteen to twenty days': 'FOURTEEN_TO_TWENTY_DAYS', 'total outstanding queries twenty one to fifty days': 'TWENTY_ONE_TO_FIFTY_DAYS', 'total outstanding queries greater than fifty days': 'GREATER_THAN_FIFTY_DAYS', 'percentage of total outstanding queries greater than fifty days': 'PERCENTAGE_GREATER_THAN_FIFTY_', 'total pages forecasted': 'TOTAL_PAGES_FORECASTED', 'total pages forecasted (site)': 'TOTAL_PAGES_FORECASTED_SITE', 'total pages forecasted (non-site)': 'TOTAL_PAGES_FORECASTED_NON_SIT', 'total pages forecasted to be inactivated': 'TOTAL_PAGES_TO_BE_INACTIVATED', 'total forecasted blank pages': 'TOTAL_BLANK_PAGES', 'total submitted pages': 'TOTAL_SUBMITTED', 'pages submitted <=7days': 'PAGES_SUBMITTED_LESS_THAN_OR_E', 'pages submitted <=15 days': 'PAGES_SUBMITTED_LESS_THAN_OR_', 'pages submitted >90 days': 'PAGES_SUBMITTED_GREATER_THAN_N', 'queries <=7days open to answer/closed': 'LESS_THAN_OR_EQUAL_TO_SEVEN_DA', 'queries 8-13 days open to answered/closed': 'EIGHT_TO_THIRTEEN_DAYS_OPEN_TO', 'queries 14-20 days open to answered/closed': 'FOURTEEN_TO_TWENTY_DAYS_OPEN_T', 'queries 21-50 days open to answered/closed': 'TWENTYONE_TO_FIFTY_DAYS_OPEN_ '}
    metric_name = slots['metric_name']
    metric_name_db = metric_name_colummn_mapper.get(metric_name)
    if metric_name_db in percentage_dict:
        metric_name_db = percentage_dict[metric_name_db]
        formater = True
    else:
        metric_name_db = "sum({})".format(metric_name_db)
        formater = False
    slots.pop('metric_name')
    query = "select {0} from {1}  where".format(metric_name_db, table_name)
    filters = ""
    for k, v in slots.items():
        if v:
            query += " upper("+(k)+") = '"+(v.upper())+"' and  "
            filters += "<strong>" + \
                k.replace("_", " ").title()+"</strong>" + " - " + v+"<br><br>"
    query = (query[:-5])
    invokeLam = boto3.client("lambda", region_name=REGION_NAME)
    payload = {"Query": query}

    if not formater:
        try:
            response = invokeLam.invoke(
                FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(payload))
        except:
            response = "we didn't get any value for your query :("
        try:
            count = json.loads(response['Payload'].read())[0][0]
        except:
            count = "we didn't get any value for your query :("
    date_info = invokeLam.invoke(FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(
        {"Query": "select  max(time) from data_loader"}))
    try:
        date = json.loads(date_info['Payload'].read())[0][0]
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
        date = date.strftime("%b %d %Y %I:%M %p")
    except:
        date = "Not available right now"
    #count = "0"
    if formater:
        if metric_name.find("%"):
            metric_name = metric_name.replace("%", "")
        try:
            payload = {"Query": query}
            response = invokeLam.invoke(
                FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(payload))

            count1 = json.loads(response['Payload'].read())[0]
            count = "<br><font size=2> Count : " + \
                str(count1[1]) + "</font><br>"+"<font size=2> Percentage : " + \
                str(round(count1[0], 2)) + " %</font><br>"

        except:
            count = 'None'
    response = "<strong>Metric Name: <font style=color:#1C60A7>{}</font></strong>  <br><br> {} <strong>Value: </strong> {}<br> ".format(
        metric_name.title(), filters, count)
    response = "<font size=2>" + response + "</font>"
    response += "<br><font size=2><i>Last Refresh : " + date+" PST </i></font><br>"
    return (response)


def fulfill_study_contact_information(session_attributes, slots):
    logger.info(f"Func: fulfill_study_contact_information \n session_attributes: {session_attributes} \n slots: {slots} ")

    """
       This function is related to Study contact information fullfillment. 
       It accepts two parameters - Session attributes & Slots.
       This funtcion assembles the information from database and validates the response.
       Also, it prepares Text message consists of all selected filters which will be shown of chatbot window.
       
    """
    table_name = session_attributes['table_name']
    role_type = slots['role_type'].upper()
    slots.pop('role_type')
    query = "select LISTAGG(name,',') WITHIN GROUP (ORDER BY role) from {} where upper(role) ='{}' and  ".format(
        table_name, role_type)
    filters = ""
    for k, v in slots.items():
        if v:
            query += " upper("+k+") = '"+v.upper() + "' and  "
            #filters += k.replace("_"," ").title() +" - "+ v+"<br>"
            filters += "<strong>" + \
                k.replace("_", " ").title()+"</strong>" + " - " + v+"<br><br>"
    query = (query[:-5])
    query = query.replace("country", "region")
    logger.info(f"Func: fulfill_study_contact_information \n query: {query} ")
    invokeLam = boto3.client("lambda", region_name=REGION_NAME)
    payload = {"Query": query}
    response = invokeLam.invoke(
        FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(payload))
    logger.info(f"Func: fulfill_study_contact_information \n response: {response} ")
    count = json.loads(response['Payload'].read())[0][0]
    logger.info(f"showing database value for roles count : {count}")
    if not count:
        count = "Role is not assigned for this combination"
    date_info = invokeLam.invoke(FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(
        {"Query": "select  max(time) from data_loader"}))
    try:
        date = json.loads(date_info['Payload'].read())[0][0]
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
        date = date.strftime("%b %d %Y %I:%M %p")
    except:
        date = "Not available right now"
    response = "<strong>Role: <font style=color:#1C60A7>{}</font> </strong><br><br> {} <strong>Name</strong> - {}<br> ".format(
        role_type.title(), filters, count)

    response = "<font size=2>" + response + "</font>"
    response += "<br><font size=2><i>Last Refresh : " + date + " PST </i></font><br>"
    return response


def fulfill_collibra_metric_information(session_attributes, slots):
    logger.info(f"Func: fulfill_collibra_metric_information \n session_attributes: {session_attributes} \n slots: {slots} ")

    """
       This function is related to Metric Logic. 
       It accepts two parameters - Session attributes & Slots.
       This funtcion assembles the information from excel file "Collibra" placed into S3 bucket, validates the response.
       Also, it prepares Text message consists of all selected filters which will be shown of chatbot window.
       
    """

    data = read_excel("Collibra.xlsx", "BTM")
    metric_name = slots['metric_name']
    user_type = slots['user_type']
    data = data[data['Name'].str.lower() == (metric_name.lower())]
    response = "<strong>Metric Name : <font style=color:#1C60A7>{}</font></strong> <br><br>".format(
        metric_name.title())
    if user_type in ['Definition (No Formatting)', 'Calculation Rule (No Formatting)']:
        value = list(data[user_type].unique())

        response += "<strong>" + \
            user_type.replace("(No Formatting)", "")+"</strong> : <br>"
        for i in value:
            response += str(i) + "<br>"
    if user_type in ['Inclusion Criteria (No Formatting)', 'Exclusion Criteria (No Formatting)', 'Inclusion Criteria/Exclusion Criteria']:
        value1 = list(data['Inclusion Criteria (No Formatting)'].unique())[0]

        value2 = list(data['Exclusion Criteria (No Formatting)'].unique())[0]
        response += "<strong><br>Inclusion Criteria:</strong><br> {} <br><br><strong>Exclusion Criteria:</strong> <br>{}" .format(
            value1, value2)
    response += '<br><br>  Please visit<a href="https://amgen.collibra.com/dashboard" target="_blank"> <b><u> Collibra </u></b></a>for more information. <br>'
    response = "<font size=2>" + response + "</font>"
    return response


def fulfill_collibra_metric_report_name(session_attributes, slots):
    logger.info(f"Func: fulfill_collibra_metric_report_name \n session_attributes: {session_attributes} \n slots: {slots} ")

    """
       This function is related to Find A Metric. 
       It accepts two parameters - Session attributes & Slots.
       This funtcion assembles the information from excel file "Collibra" placed into S3 bucket, validates the response.
       Also, it prepares Text message consists of all selected filters which will be shown of chatbot window.
       
    """
    data = read_excel("Collibra.xlsx", "BTM")
    data2 = read_excel("Collibra.xlsx", "RBP")
    data = data[data.Type == "Metric"]
    data3 = data2[data2.Type == "Report"]
    metric_name = slots['metric_name']
    data = data[data['Name'].str.lower() == (metric_name.lower())]
    logger.info(f"Func: fulfill_collibra_metric_report_name \n data: {data.head()} ")
    report_name = list(data['Used In [Asset] > Asset'].unique())
    logger.info(f"Func: fulfill_collibra_metric_report_name \n report_name: {report_name} ")
    response = "<font size=2> <strong> Metric Name: <font style=color:#1C60A7>{}</font> </strong></font> <br><br>".format(
        metric_name)
    response += "<font size=2> <strong> Report Links: </strong></font> <br>"
    link_list = []
    for d in report_name:
        new_data = data3[data3['Name'].str.lower() == (d.lower())]
        link = list(new_data['Location (No Formatting)'].unique())
        for i in link:
            link_list.append(i)
            response += '<a href=' + \
                str(i)+' target="_blank" > <b><u>'+str(d)+'</u></b></a><br>'
    if not link_list:
        response = "I can't find any link for <font size=2> <strong> Metric Name: <font style=color:#1C60A7>{}</font></strong></font> ".format(
            metric_name)
        data2 = data2[data2['Name'].str.lower() == (report_name[0].lower())]
        process = list(data2['Type'].unique())
    if not link_list and process[0] == "Business Process" and len(process) == 1:
        response += "as metric is not mapped to any report in our data governance tool - Collibra. <br>"
    response += '<br> Please visit<a href="https://amgen.collibra.com/dashboard" target="_blank"> <b><u> Collibra </u></b></a>for more information or reach out to <a href=mailto:caas@amgen.com?subject=Amgen Blu:> <b> <u> caas@amgen.com </u> </b> </a> to raise a request. <br>'
    response = "<font size=2>" + response + "</font>"
    session_attributes["spotfireLinks"] = json.dumps(link_list)
    session_attributes["actions"] = "openLink"
    return response


def fulfill_cap_rule_information(session_attributes, slots):
    logger.info(f"Func: fulfill_cap_rule_information \n session_attributes: {session_attributes} \n slots: {slots} ")

    """
       This function is related to CAP Rule Fullfillment. 
       It accepts two parameters - Session attributes & Slots.
       This funtcion assembles the information from excel file "CAPRule" placed into S3 bucket, validates the response.
       Also, it prepares Text message consists of all selected filters which will be shown of chatbot window.
       
    """
    data = read_excel("CAPRule.xlsx", "Sheet1")

    business_rule = slots['business_rule'].lower()
    rule_type = slots['rule_type']
    businessRule = data['BUSINESS_RULE'].str.lower()
    businessRule = [item for item in businessRule if first_and_last(item) == business_rule]
    data = data[data['BUSINESS_RULE'].str.lower() == businessRule[0]]
    
    logger.info(f"Func: fulfill_cap_rule_information \n rule_type: {rule_type} \n business_rule: {business_rule} \n data: {data}")
    data = data[data['RULE_TYPE'].str.lower() == rule_type.lower()]
    logger.info(f"Func: fulfill_cap_rule_information \n rule_type: {rule_type} \n business_rule: {business_rule} \n data: {data}")
    description = list(data['DESCRIPTION'].unique())[0]
    response = '<strong>Business Rule- <font style=color:#1C60A7>{}</font> </strong> <br> <br><strong>Rule Type  - <font style="color:#1C60A7">{}</font></strong><br><br><strong>Description : </strong> <br> {} <br><br><strong>Action: <br></strong>  ' .format(
        business_rule.title(), rule_type.title(), description)
    response += list(data['ACTION'].unique())[0]
    response += "<br>"
    response = "<font size=2>" + response + "</font>"
    return response


def faq_fall_back_intent(intent_request):
    logger.info(f"Func: faq_fall_back_intent \n intent_request: {intent_request} ")
    return close(
        {},
        'Fulfilled',
        information_retrieval_rapidfuzz(intent_request['inputTranscript'])
    )


def dashboard_metric_value_intent(intent_request):
    logger.info(f"Func: dashboard_metric_value_intent \n intent_request: {intent_request} ")
    """
     This function validates all the Session attributes for their retry count for Metric Value information.
     Also, reroute to validate_dashboard_metric_value and fulfill_dashboard_metric_value accordingly.
     It accepts one parameter (intent_request) from dispatch function/ Greetings accordingly.
       
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    metric_name_retry_count = try_ex(
        lambda: session_attributes['metric_name_retry_count'])
    session_attributes['metric_name_retry_count'] = 0 if not metric_name_retry_count else int(
        metric_name_retry_count)

    study_number_retry_count = try_ex(
        lambda: session_attributes['study_number_retry_count'])
    session_attributes['study_number_retry_count'] = 0 if not study_number_retry_count else int(
        study_number_retry_count)

    site_number_retry_count = try_ex(
        lambda: session_attributes['site_number_retry_count'])
    session_attributes['site_number_retry_count'] = 0 if not site_number_retry_count else int(
        site_number_retry_count)

    country_retry_count = try_ex(
        lambda: session_attributes['country_retry_count'])
    session_attributes['country_retry_count'] = 0 if not country_retry_count else int(
        country_retry_count)

    if session_attributes['study_number_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('metric_name_retry_count'))
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('site_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Study Number.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close({}, 'Fulfilled', response)
    if session_attributes['site_number_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('metric_name_retry_count'))
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('site_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Site Number.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close({}, 'Fulfilled', response)
    if session_attributes['country_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('metric_name_retry_count'))
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('site_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Country.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close({}, 'Fulfilled', response)

    if session_attributes['metric_name_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('metric_name_retry_count'))
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('site_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Metric Name.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if intent_request['invocationSource'] == 'DialogCodeHook':
        return validate_dashboard_metric_value(intent_request)
            
    response = fulfill_dashboard_metric_value(session_attributes, slots)
    return close({}, 'Fulfilled', response)


def cap_rule_information_intent(intent_request):
    logger.info(f"Func: cap_rule_information_intent \n intent_request: {intent_request} ")
    """
     This function validates all the Session attributes for their retry count for CAP Rule information.
     Also, reroute to validate_cap_rule_information_intent and fulfill_cap_rule_information accordingly.
     It accepts one parameter (intent_request) from dispatch function/ Greetings accordingly.
       
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    #slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    business_rule_retry_count = try_ex(lambda: session_attributes['business_rule_retry_count'])
																
    session_attributes['business_rule_retry_count'] = 0 if not business_rule_retry_count else int(
        business_rule_retry_count) 
        
    business_rule = try_ex(lambda : session_attributes['business_rule'])
    logger.info(f"Func: validate_cap_rule_information_intent \n From session_attributes  business_rule: {business_rule} ")
    rule_type = try_ex(lambda: intent_request['currentIntent']['slots']['rule_type'])
    slots = {'business_rule': business_rule, 'rule_type': rule_type}

    logger.info(f"Func: cap_rule_information_intent \n slots: {slots} \n session_attributes: {session_attributes} \n intent_request: {intent_request} ")
    if session_attributes['business_rule_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('business_rule_retry_count'))

        response = "Sorry, it looks like you have entered the incorrect Business Rule.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if intent_request['invocationSource'] == 'DialogCodeHook':
											
											
        validation_out = validate_cap_rule_information_intent(intent_request)
        logger.info(f"Func: cap_rule_information_intent \n validation_out: {validation_out} ")
        return validation_out
    response = fulfill_cap_rule_information(session_attributes, slots)
    logger.info(f"Func: cap_rule_information_intent \n close response: {response} ")
    return close({}, 'Fulfilled', response)


def study_contact_information_intent(intent_request):
    logger.info(f"Func: study_contact_information_intent \n intent_request: {intent_request} ")
    """
     This function validates all the Session attributes for their retry count for Study contact information.
     Also, reroute to validate_study_contact_information_intent and fulfill_study_contact_information accordingly.
     It accepts one parameter (intent_request) from dispatch function/ Greetings accordingly.
       
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    role_type_retry_count = try_ex(
        lambda: session_attributes['role_type_retry_count'])
    session_attributes['role_type_retry_count'] = 0 if not role_type_retry_count else int(
        role_type_retry_count)
    study_number_retry_count = try_ex(
        lambda: session_attributes['study_number_retry_count'])
    session_attributes['study_number_retry_count'] = 0 if not study_number_retry_count else int(
        study_number_retry_count)
    site_number_retry_count = try_ex(
        lambda: session_attributes['site_number_retry_count'])
    session_attributes['site_number_retry_count'] = 0 if not site_number_retry_count else int(
        site_number_retry_count)
    country_retry_count = try_ex(
        lambda: session_attributes['country_retry_count'])
    session_attributes['country_retry_count'] = 0 if not country_retry_count else int(
        country_retry_count)
    if session_attributes['role_type_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('role_type_retry_count'))
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('site_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Role.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['study_number_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('role_type_retry_count'))
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('site_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Study Number.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['site_number_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('role_type_retry_count'))
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('site_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Site Number.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['country_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('role_type_retry_count'))
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('site_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Country.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if intent_request['invocationSource'] == 'DialogCodeHook':
        return validate_study_contact_information_intent(intent_request)
    try_ex(lambda: session_attributes.pop('study_number_retry_count'))
    try_ex(lambda: session_attributes.pop('site_number_retry_count'))
    try_ex(lambda: session_attributes.pop('country_retry_count'))
    response = fulfill_study_contact_information(session_attributes, slots)
    return close({}, 'Fulfilled', response)


def collibra_metric_information_intent(intent_request):
    logger.info(f"Func: collibra_metric_information_intent \n intent_request: {intent_request} ")
    """
     This function one parameter (intent_request) from dispatch function/ Greetings.
     It Validates options and sub-options for Metric Logic.
    
    """
    metric_name = try_ex(
        lambda: intent_request['currentIntent']['slots']['metric_name'])
    logger.info(f"Func: collibra_metric_information_intent \n metric_name: {metric_name} ")
								 
    user_type = try_ex(
        lambda: intent_request['currentIntent']['slots']['user_type'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    metric_name_retry_count = try_ex(
        lambda: session_attributes['metric_name_retry_count'])
    session_attributes['metric_name_retry_count'] = 0 if not metric_name_retry_count else int(
        metric_name_retry_count) + 1
    if session_attributes['metric_name_retry_count'] > 3:
        try_ex(lambda: session_attributes.pop('metric_name_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Metric Name.<br><br>Please reach out to the CSAR team for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if intent_request['invocationSource'] == 'DialogCodeHook':
        if not metric_name and int(session_attributes['metric_name_retry_count']) == 0:
            #session_attributes['metric_name_retry_count'] = int(session_attributes['metric_name_retry_count'])+1
																
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               {'metric_name': metric_name,
                                   'user_type': user_type},
                               'metric_name',
                               "You have selected <b> Metric Logic </b>. <br> Kindly enter the Metric Name as available in Collibra which I can assist you with: <br>")
        if not metric_name and session_attributes['slot_elicited'] == 'metric_name':
            metric_name = intent_request['inputTranscript']
        metric, exact_match = find_metric_match(metric_name, "collibra", intent_request)
        if len(metric) == 0:
            session_attributes['metric_name_retry_count'] = int(
                session_attributes['metric_name_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               {'metric_name': metric_name,
                                   'user_type': user_type},
                               'metric_name',
                               "The Metric {} is not available in Collibra.<br><br>Please make sure that you have entered the correct Metric Name.".format(metric_name))
        if len(metric) > 1 or not exact_match:
            response_card = build_response_card(metric, include_no=True)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'metric_name': metric[0],
                                           'user_type': user_type},
                                       'metric_name',
                                       "Are you looking for one of the following metrics ?",
                                       response_card)

        if not user_type:
            buttton = ["Definition", "Calculation",
                       "Inclusion Criteria/Exclusion Criteria"]
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'metric_name': metric[0],
                                           'user_type': user_type},
                                       'user_type',
                                       "You have entered <b> Metric Name – {} </b>. <br> Now, please choose one of the following options: <br>".format(
                                           metric[0].title()),
                                       response_card)
        try_ex(lambda: session_attributes.pop('metric_name_retry_count'))
        return delegate(session_attributes, {'metric_name': metric[0], 'user_type': user_type})
    response = fulfill_collibra_metric_information(session_attributes, slots)
    return close({}, 'Fulfilled', response)


def Greetings_intent(intent_request):
    logger.info(f"Func: Greetings_intent \n intent_request: {intent_request} ")
    """
      This function comes into action when user says "Hi" or some other trained greeting words to chatbot.
      Control passes to Greetings intent. It accepts just one parameter- intent_request.
      This function shows greeting message on the chatbot window and reroute to the other intents according to user inputs.
      
    """
    query_type = try_ex(
        lambda: intent_request['currentIntent']['slots']['queryType'])
    previous_status = try_ex(
        lambda: intent_request['sessionAttributes']['currentStatus'])

    if previous_status:
        previous_status = json.loads(previous_status)
    current_status = json.dumps({
        'queryType':  str(previous_status if previous_status is None else previous_status['queryType']) + str(query_type)
    })
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    session_attributes['currentStatus'] = current_status
    final_status = json.loads(
        try_ex(lambda: session_attributes['currentStatus']))
    try:
        nameUser = intent_request['userId'].split('_')[1]
    except:
        nameUser = "User"
        
    if final_status['queryType'] == "NoneNone":
        return elicit_slot_buttons(session_attributes, 'Greetings', {}, 'queryType', 'Hello {}!<br> I am Chatbot BLU. <br> Which of the following topics can I help you with today? <br>'.format(nameUser), build_response_card_dict(None, None, [
            {'text': 'Reports', 'value': 'reports'},
            {'text': 'System', 'value': 'system'},
            {'text': 'Metric', 'value': 'metric'},
            {'text': 'Study Team - Role', 'value': 'Study Contact'},
            {'text': 'Ask a question to CSAR', 'value': 'others'}
        ]))
    elif final_status['queryType'] == "Noneplanenrolment":
        return elicit_slot(
            session_attributes,
            "enrolment_flow",
            {},
            "study_number",
            'You have selected <b> % to Plan Enrollment </b>, Great! <br> Enter the Study number to proceed further: <br>')

    elif final_status['queryType'] == "Noneplanactivation":
        return elicit_slot(
            session_attributes,
            "activation_flow",
            {},
            "study_number",
            'You have selected <b> % to Plan Activation </b>, Great! <br> Enter the Study number to proceed further: <br>')

    elif final_status['queryType'] == "Nonestudiesmeetingplanenrolment":
        slots = {'year_information': None,
                 'month_information': None, 'country': None}
        count = fetch_meeting_flow('SUBJECT_ENROLLMENT', slots, 'year')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(
                session_attributes,
                "studies_meeting_enrolment",
                {},
                "year_information",
                "You have selected <b>Studies Meeting Plan Enrollment</b>, Perfect! <br> Next, select the year from the below options: <br>",
                response_card)

    elif final_status['queryType'] == "Nonestudiesmeetingplanactivation":
        slots = {'year_information': None,
                 'month_information': None, 'country': None}
        count = fetch_meeting_flow('SITE_ACTIVATION', slots, 'year')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(
                session_attributes,
                "studies_meeting_activation",
                {},
                "year_information",
                "You have selected <b>Studies Meeting Plan Activation</b>, Perfect! <br> Next, select the year from the below options: <br>",
                response_card)

    elif final_status['queryType'] == "Nonecountriesmeetingplanenrolement":
        slots = {'year_information': None,
                 'month_information': None, 'country': None}
        count = fetch_meeting_flow('SUBJECT_ENROLLMENT', slots, 'year')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(
                session_attributes,
                "countries_meeting_enrolment",
                {},
                "year_information",
                "You have selected <b> Countries Meeting Plan Enrollment </b>, Perfect! <br> Next, select the year from the below options: <br>",
                response_card)

    elif final_status['queryType'] == "Nonecountriesmeetingplanactivation":
        slots = {'year_information': None,
                 'month_information': None, 'country': None}
        count = fetch_meeting_flow('SITE_ACTIVATION', slots, 'year')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(
                session_attributes,
                "countries_meeting_activation",
                {},
                "year_information",
                "You have selected <b> Countries Meeting Plan Activation </b>, Perfect! <br> Next, select the year from the below options: <br>",
                response_card)

    elif final_status['queryType'] == "NoneNoneStudy Contact":
        return elicit_slot_buttons(
            session_attributes,
            "study_contact_information",
            {},
            "role_type",
            'You have selected <b> Study Team – Role </b>. Which of these can I assist you with? <br>', build_response_card_dict(None, None, [
                {'text': 'CPM', 'value': 'CPM'},
                {'text': 'LDM', 'value': 'LDM'},
                {'text': 'GCTM', 'value': 'Global Clinical Trial Manager'},
                {'text': 'RCTM', 'value': 'Regional Clinical Trial Manager'},
                {'text': 'CRA', 'value': 'CRA'},
                {'text': 'CTA', 'value': 'CTA'},
                {'text': 'Lead CTA', 'value': 'Lead Clinical Trial Associate'},
                {'text': 'Primary CRA', 'value': 'Primary CRA'},
                {'text': 'CDM Lead', 'value': 'CDM Lead'},
                {'text': 'CDM Manager', 'value': 'CDM Manager'},
                {'text': 'Other Roles', 'value': 'others'}

            ]))
    elif final_status['queryType'] == "NoneNonemetric":
        return elicit_slot_buttons(session_attributes, 'Greetings', {}, 'queryType', 'Thank you! <br> Please choose from the options below: <br> ', build_response_card_dict(None, None, [
            {'text': 'Metric Value', 'value': 'flowstart'},
            {'text': 'Metric Logic', 'value': 'logic'},
            {'text': 'Find a Metric', 'value': 'dashboard'},
            {'text': 'Ask a question', 'value': 'others'}

        ]))
    elif final_status['queryType'] == "NoneNonemetricflowstart":
        data = read_excel("MetricCombination.xlsx", "Sheet1")
        user_id = intent_request['userId'].split("_")[0]
        access_list = user_dashboard_access(user_id)
        dashboard_names = list(data['Dashboard Name'].unique())
        dashboard_access = list(set(dashboard_names) & set(access_list))
        
        logger.info(f"Func: Greetings_intent \n access_list: {access_list} \n dashboard_names : {dashboard_names} \n dashboard_access: {dashboard_access} ")

        if not dashboard_access:
            response = "You do not have access to DMT/SPAQ/Enrollment metrics.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly.<br>  "
            return close(session_attributes, 'Fulfilled', response)
        #data = data[data['Dashboard Name'].isin(dashboard_access)]
        options = list(data['Related to'].unique())
        options = [i for i in options if str(i) != 'nan']
        return elicit_slot_buttons({}, 'metric_flow', {}, 'options', 'Please choose from the options below: <br> ', build_response_card(options))

    elif final_status['queryType'] == "NoneNonemetriclogic":
        session_attributes['metric_name_retry_count'] = 0
        return elicit_slot(
            session_attributes,
            "collibra_metric_information",
            {},
            "metric_name",
            'You have selected <b> Metric Logic </b>. <br> Kindly enter the Metric Name as available in Collibra which I can assist you with: <br>')
    elif final_status['queryType'] == "NoneNonemetricdashboard":
        return elicit_slot(
            session_attributes,
            "collibra_metric_report_name",
            {},
            "metric_name",
            'You have selected <b> Find A Metric </b>. <br> Kindly enter the Metric Name as available in Collibra which I can assist you with: <br>')
    elif final_status['queryType'] == "NoneNonereports":
        return elicit_slot_buttons(session_attributes, 'Greetings', {}, 'queryType', 'You have selected <b> Reports </b>, Great! <br> Which of these options can I assist you with? <br>', build_response_card_dict(None, None, [
            {'text': 'Access', 'value': 'access'},
            {'text': 'CAP', 'value': 'cap'},
            {'text': 'Ask a question ', 'value': 'others'}
        ]))
    elif final_status['queryType'] == "NoneNonesystem":
        return elicit_slot_buttons(session_attributes, 'Greetings', {}, 'queryType', 'You have selected <b> System </b>, Got it! <br> Now, please choose one of the following systems I can assist you with - <br>', build_response_card_dict(None, None, [
            {'text': 'eClinical', 'value': 'eclinical'},
            {'text': 'Rave', 'value': 'rave'}
        ]))
    elif final_status['queryType'] in ["NoneNonesystemfirm", "NoneNonesystemlift", "NoneNonesystemeclinical", "NoneNonesystemrave"]:
        return elicit_slot_buttons(session_attributes, 'Greetings', {}, 'queryType', 'Great! Is your query related to Access or any other question? <br>', build_response_card_dict(None, None, [
            {'text': 'Access', 'value': 'access'},
            {'text': 'Ask a question ', 'value': 'others'}
        ]))
    elif final_status['queryType'] == "NoneNonesystemfirmaccess":
        return close({}, 'Fulfilled', 'Please check to see if you are on the management tab for those studies in e-Clinical. If you are and still do not see them in FIRM, you will need to open a ticket with the IS Helpdesk. ')
    elif final_status['queryType'] == "NoneNonesystemliftaccess":
        return close({}, 'Fulfilled', 'Please take the following LMS Courses (Introduction to LIFT report training 1.0 (168595-1.0), Introduction to LIFT report training for CRA’s 1.0(168596-1.0)). If you need read only access, to access all studies, then you need to make sure that you have completed the non-CRA LMS course. However, when you run reports you will not have the links to NA or comment. If you need access to all studies, and require the NA links to appear, you will need to take the non-CRA LMS course and upon completion, request “business admin” access from the helpdesk. ')
    elif final_status['queryType'] == "NoneNonesystemraveaccess":
        return close({}, 'Fulfilled', 'Please send in your request to EDC provisioning team<a href="mailto: edc-account-provisioning@amgen.com"> <b><u> edc-account-provisioning@amgen.com</b></u> </a>, they should be able to help you with your request.')
    elif final_status['queryType'] == "NoneNonesystemeclinicalaccess":
        return close({}, 'Fulfilled', ' In order to get access to eClinical you will need to complete the required LMS Course, please send an email to CTE Training team (<a href="mailto:cte-training@amgen.com?subject=Amgen Blu:"> <b>cte-training@amgen.com</b></a>) asking them to assign the relevant trainings.<br>The access to eClinical is usually granted within 48-72 hours after completion of LMS eClinical trainings.<br>If you still do not receive access after 72 hours , please raise a service request with your local helpdesk and ensure that you have added <b>"APP-ECLIN Resolver Group" </b> in the Subject/Summary in order for the ticket to be assigned to the correct group. <br>In order to reactivate your eClinical account, please raise a service request with your local helpdesk and ensure that you have added <b>"APP-ECLIN Resolver Group"</b> in the Subject/Summary in order for the ticket to be assigned to the correct group.')

    elif final_status['queryType'] == "NoneNonereportsaccess":
        return elicit_slot_buttons(session_attributes, 'Greetings', {}, 'queryType', 'You have selected <b> Access </b>, Got it! <br> Now, please choose one of the following platforms:<br> ', build_response_card_dict(None, None, [
            {'text': 'Spotfire', 'value': 'spotfire'},
            {'text': 'Cognos', 'value': 'cognos'}
        ]))
    elif final_status['queryType'] == "NoneNonereportsaccessspotfire":
        return close({}, 'Fulfilled', '<b> GDO Reports :</b> <br>Please raise a service request with your local helpdesk. They will be able to provide you with the link to MyAccess Portal and the steps to raise access for spotfire application.<br>For any other queries  Please reach out to <a href="mailto:caas@amgen.com?subject=Amgen Blu:"> <b> caas@amgen.com </b> </a><br> <b>Please ensure that you have added "Amgen blu: " in subject line</b>.<br> <br> <b> Patient Data Report :</b> <br> For study Baseline Package (L2\L3 reviews) or Clean Patient Tracker, please submit a request on below link: <br> <a href=" https://amgen.sharepoint.com/sites/CDMSys-513171/Ops/clinicalreporting/Spotfire/Lists/Spotfire%20Self%20Service%20Requests/NewForm.aspx?RootFolder"  target="_blank"> <b> <u> https://amgen.sharepoint.com/sites/CDMSys-513171/Ops/clinicalreporting/Spotfire/Lists/Spotfire%20Self%20Service%20Requests/NewForm.aspx?RootFolder </u> </b> </a> ')
    elif final_status['queryType'] == "NoneNonereportsaccesscognos":
        return close({}, 'Fulfilled', 'Please send in your request to Cognos admins <a href="mailto:DL-Cognos-adminCTS@amgen.com"> <b><u> DL-Cognos-adminCTS@amgen.com</b></u> </a>, they should be able to help you with your question.')
    elif final_status['queryType'] == "NoneNonereportsaccessexisting":
        return close({}, 'Fulfilled',  ' Please reach out to CSAR Mailbox- <a href="mailto:caas@amgen.com?subject=Amgen Blu:"> <b> caas@amgen.com </b> </a>')
    elif final_status['queryType'] == "NoneNonereportscap":
        return elicit_slot(
            {},
            "cap_rule_information",
            {},
            "business_rule",
            'You have selected <b> CAP  </b> , Great! <br> Kindly enter the CAP rule which I can assist you with: <br>')
    elif final_status['queryType'] in ["NoneNonemetricothers", "NoneNoneothers", "NoneNonereportsothers", "NoneNonesystemeclinicalothers", "NoneNonesystemraveothers", "NoneNonesystemliftothers", "NoneNonesystemfirmothers"]:
        return just_close(
            {},

            "Fulfilled",
            'Great! <br> Next, Type in your question (or phrase) and i will try to get you an answer.<br>')

    else:
        response = "Aw Snap!<br> I am not able to find a response, I am in a  learning phase. <br> Meanwhile if you still have questions, you can write to <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> with subject line as <b>” Amgen Blu ” </b>. <br> Alternatively, I can have one of our reps contact you directly, what would you prefer? <br> "
        return close({}, 'Fulfilled', response)


def yes_no_intent(intent_request):
    logger.info(f"Func: yes_no_intent \n intent_request: {intent_request} ")
    """
     When the user wants to continue with chatbot after having a proper response from chatbot. Control passes to yes_no_intent function. 
     If, user chooses "Yes" then the flow starts again for further enquiries.
     If, user chooses "No" then chatbot shows a feedback message to log user's experience with chatbot.
     It accepts one parameter - intent_request.
       
    """
    status = try_ex(lambda: intent_request['sessionAttributes']['status'])
    yes_no = try_ex(lambda: intent_request['currentIntent']['slots']['Yes_No'])
    happy = try_ex(lambda: intent_request['currentIntent']['slots']['happy'])
    session_attributes = {}
    current_status = json.dumps({
        'queryType':  "NoneNone"
    })
    session_attributes['currentStatus'] = current_status
    try:
        nameUser = intent_request['userId'].split('_')[1]
    except:
        nameUser = 'User'
    
    if yes_no == "None of these":
        session_attributes['status'] = 'closing'
        response_card = build_response_card(
            ["Yes", "No"], title=None, subtitle=None)
        response = {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Fulfilled',
                'message': {'contentType': 'PlainText', 'content': "Is there anything else that you want assistance with? "},
                'responseCard': response_card
            }
        }
        return response

    if status == 'asking feedback' and yes_no == 'No':
        return {
            'sessionAttributes': {},
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Fulfilled',
                'message': {'contentType': 'PlainText', 'content': 'Thank You.. <br> Have a wonderful rest of the day {}! <br>'.format(nameUser)}
            }
        }

    if status == 'asking feedback' and yes_no == 'Yes':
        try_ex(lambda: session_attributes.pop('status'))
        return {
            'sessionAttributes': {"feedback": "yes"},
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Fulfilled',
                'message': {'contentType': 'PlainText', 'content': 'Please update your feedback to us in the opened mailbox.<br> Have a wonderful rest of the day {}! <br>'.format(nameUser)}
            }
        }
    if status == 'closing from metric flow' and yes_no == 'Yes':
        try_ex(lambda: session_attributes.pop('status'))
        return {
            'sessionAttributes': {},
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Fulfilled',
                'message': {'contentType': 'PlainText', 'content': 'You may frame your question using the following parameters : <br>- Study number<br>- Site Number<br>- Country<br>- Time period <br> <br> Example:- Metric Value of Total Pages Outstanding for 20110203 in the Site 66001.'}
            }
        }
    if status == 'closing' and yes_no == 'Yes':
        try_ex(lambda: session_attributes.pop('status'))
        return elicit_slot_buttons(session_attributes, 'Greetings', {}, 'queryType', 'Please select one of the options below: <br>', build_response_card_dict(None, None, [
            {'text': 'Reports', 'value': 'reports'},
            {'text': 'System', 'value': 'system'},
            {'text': 'Metric', 'value': 'metric'},
            {'text': 'Study Team - Role', 'value': 'Study Contact'},
            {'text': 'Ask a question to CSAR', 'value': 'others'}
        ]))
    if happy:
        if happy == "happy":
            return {
                'sessionAttributes': {},
                'dialogAction': {
                    'type': 'Close',
                    'fulfillmentState': 'Fulfilled',
                    'message': {'contentType': 'PlainText', 'content': 'I am thrilled to know that I could be of help.<br> Have a wonderful rest of the day {}! <br>'.format(nameUser)}
                }
            }
        else:
            session_attributes['status'] = "asking feedback"

            return elicit_slot_buttons(session_attributes, intent_request['currentIntent']['name'], {}, 'Yes_No', 'I would really appreciate some details on how I could have helped you better. Would you like to elaborate? <br> <br><b> Note: Please enable pop-ups before clicking on <i> <strong>Yes</i></strong> </b><br>', build_response_card_dict(None, None, [
                {'text': 'Yes', 'value': 'Yes'},
                {'text': ' No', 'value': 'No'}
            ]))

            # return {
            #     'sessionAttributes': {"feedback":"yes"},
            #     'dialogAction': {
            #         'type': 'Close',
            #         'fulfillmentState': 'Fulfilled',
            #         'message': {'contentType': 'PlainText', 'content':'Sorry, I am learning constantly. Please update your feedback to us.<br> Have a wonderful rest of the day {}! <br>'.format(nameUser) }
            #     }
            # }

    else:
        return elicit_slot_buttons(session_attributes, intent_request['currentIntent']['name'], intent_request['currentIntent']['slots'], 'happy', 'Was I able to answer your questions today? <br> Your feedback is going to be valuable in my learning journey.<br>', build_response_card_dict(None, None, [
            {'text': 'Yes, You Did!', 'value': 'happy'},
            {'text': 'Yeah, Kind of!', 'value': 'neutral'},
            {'text': ' No, Not Really!', 'value': 'unhappy'}
        ]))


def collibra_metric_report_name_intent(intent_request):
    logger.info(f"Func: collibra_metric_report_name_intent \n intent_request: {intent_request} ")
    """
     This function validates all the Session attributes for their retry count for Find A Metric option.
     Also, reroute to find_metric_match and fulfill_collibra_metric_report_name accordingly. 
     It accepts one parameter (intent_request) from dispatch function.
       
    """
    metric_name = try_ex(lambda: intent_request['currentIntent']['slots']['metric_name'])
    if not metric_name:
        metric_name = try_ex(lambda : intent_request['sessionAttributes']['metric_name'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    metric_name_retry_count = try_ex(
        lambda: session_attributes['metric_name_retry_count'])
    session_attributes['metric_name_retry_count'] = 0 if not metric_name_retry_count else int(
        metric_name_retry_count)
    if session_attributes['metric_name_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('metric_name_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Metric Name.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if intent_request['invocationSource'] == 'DialogCodeHook':
        if not metric_name:
            session_attributes['metric_name_retry_count'] = int(
                session_attributes['metric_name_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               {'metric_name': metric_name},
                               'metric_name',
                               "Please type a metric name you want to do analysis on")
        metric, exact_match = find_metric_match(metric_name, "collibra", intent_request)
        if len(metric) == 0:
            session_attributes['metric_name_retry_count'] = int(
                session_attributes['metric_name_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               {'metric_name': metric_name},
                               'metric_name',
                               "The Metric {} is not available in Collibra.<br><br>Please make sure that you have entered the correct Metric Name.".format(metric_name))
        if len(metric) > 1 or not exact_match:
            response_card = build_response_card(metric, include_no=True)

            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'metric_name': metric[0]},
                                       'metric_name',
                                       "Are you looking for one of the following metrics ?",
                                       response_card)

        try_ex(lambda: session_attributes.pop('metric_name_retry_count'))
        return delegate(session_attributes, {'metric_name': metric[0]})
    response = fulfill_collibra_metric_report_name(session_attributes, slots)
    return close(session_attributes, 'Fulfilled', response)


def fulfill_enrolment_flow(session_attributes, slots):
    logger.info(f"Func: fulfill_enrolment_flow \n session_attributes: {session_attributes} \n slots : {slots} ")

    """
       This function is related to Enrollment & Activation metric. 
       It accepts two parameters - Session attributes & Slots.
       This funtcion assembles the session attributes which will be passed to SP site for visuals. 
       Also, it prepares Text message consists of all selected filters which will be shown of chatbot window.
       
    """
    month_dictionary = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05',
                        'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
    if session_attributes['metric_name'] == "% to Plan" and session_attributes['main_metric'] == "Subject Enrollment":
        enrolment_name = "% to Plan Enrollment"
    elif session_attributes['metric_name'] == "% to Plan" and session_attributes['main_metric'] == "Site Activation":
        enrolment_name = "% to Plan Site Activation"
    elif session_attributes['metric_name'] == "Studies Meeting Plan" and session_attributes['main_metric'] == "Site Activation":
        enrolment_name = "Studies Meeting Plan Site Activation"
    elif session_attributes['metric_name'] == "Studies Meeting Plan" and session_attributes['main_metric'] == "Subject Enrollment":
        enrolment_name = "Studies Meeting Plan Enrollment"
    elif session_attributes['metric_name'] == "Countries Meeting Plan" and session_attributes['main_metric'] == "Subject Enrollment":
        enrolment_name = "Countries Meeting Plan Enrollment"
    elif session_attributes['metric_name'] == "Countries Meeting Plan" and session_attributes['main_metric'] == "Site Activation":
        enrolment_name = "Countries Meeting Plan Site Activation"

    fillers = "<strong>" + "Metric name: " + \
        "</strong>"+" - "+enrolment_name+"<br><br>"
    dic = {}
    for k, v in slots.items():
        if v:
            fillers += "<strong>" + \
                k.replace("_", " ").title()+"</strong>" + " - " + v+"<br><br>"
            #attries +=  "'"+k.replace("_"," ").title()+"'" +":"+v+","
            if k == "plan_info":
                session_attributes["plan_info"] = v
            if k == "study_information":
                session_attributes["study_information"] = v
            if k == "country":
                dic["Country"] = v
            if k == "hub_info":
                dic["GMO Hub"] = v
            if k == "study_number":
                dic["Study Number"] = v
            if k == "year_information":
                dic["Year"] = v
            if k == "month_information":
                dic["Month"] = month_dictionary[v.lower()]
            if k == "gmo_info":
                dic["GMO Region"] = v
            if k == "gdo_info":
                if session_attributes['main_metric'] == "Subject Enrollment":
                    dic["Region"] = v
                else:
                    dic["GSO Region"] = v
        session_attributes["filter"] = json.dumps(dic)
        session_attributes["visual"] = "spotfire"
    #attries = attries[:-1]

    return (fillers)


def validate_enrolment_flow_intent(intent_request):
    logger.info(f"Func: validate_enrolment_flow_intent \n intent_request: {intent_request} ")
    """
    This function validates % to Plan Enrollment metric filters - Study number, Year, Month,Plan & Grains (Global, Hub, Region, Country)
    It accepts one parameter that is intent_request from enrolment_flow_intent function.
    
    """

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    user_query = intent_request['inputTranscript'].lower()
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    logger.info (" SLOTS : " + str(slots))
    study_number = slots['study_number'] if slots['study_number'] else re.findall(
        r'\d{8}(?:\.\d{1,2})?', user_query)[0] if re.findall(r'\d{8}(?:\.\d{1,2})?', user_query) else None
    logger.info("STUDY NUMBER : " + str(study_number))
    year_information = try_ex(
        lambda: intent_request['currentIntent']['slots']['year_information'])
    month_information = try_ex(
        lambda: intent_request['currentIntent']['slots']['month_information'])
    plan_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['plan_info'])
    grains_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['grains_info'])
    hub_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['hub_info'])
    region_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['region_info'])
    gmo_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['gmo_info'])
    gdo_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['gdo_info'])
    country = slots['country']
    time_period = slots['time_period']
    year = re.findall(r'\b(\d{4})\b', user_query)
    month = re.findall(
        r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may?|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)', user_query)
    table = "SUBJECT_ENROLLMENT"

    if time_period or year:
        year = str(year[0])if len(year) > 0 else None
        month = str(month[0])if len(month) > 0 else None
        if time_period is not None:
            month_dict = {'01': 'jan', '02': 'feb', '03': 'mar', '04': 'apr', '05': 'may', '06': 'jun',
                          '07': 'jul', '08': 'aug', '09': 'sep', '10': 'oct', '11': 'nov', '12': 'dec'}
            year_time_period = str(time_period[:4])
            month_time_period = str(
                time_period[time_period.find("-")+1:time_period.find("-")+3])
            month_time_period = month_dict.get(month_time_period)
            year_information = year_time_period if year is None else year
            month_information = month_time_period if month is None else month

        time_period = str(year_information)+"-"+str(month_information)

    if gdo_info:
        new_gdo_info = find_metric_match(gdo_info, "enrollment gdo")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_gdo_info:
            if len(new_gdo_info) > 1:
                response_card = build_response_card(new_gdo_info)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'gdo_info',
                                           "These are the closest names which I can find from your query, please choose from the buttons below : ",
                                           response_card)
            else:
                slots['gdo_info'] = new_gdo_info[0]
                gdo_info = new_gdo_info[0]
        count = validation_query_creator(table, 'GDO_REGION', gdo_info.upper())
        if (count) == 0:
            session_attributes['gdo_retry_count'] = int(
                session_attributes['gdo_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'gdo_info',
                               "You have entered incorrect <b> GDO Region – {} </b>. Please enter correct GDO Region to proceed further. <br>".format(gdo_info))
    if gmo_info:
        if gmo_info.lower() in ['us', 'usa', 'united state']:
            gmo_info = "United States"
        new_gmo_info = find_metric_match(gmo_info, "enrollment gmo")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_gmo_info:
            if len(new_gmo_info) > 1:
                response_card = build_response_card(new_gmo_info)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'gmo_info',
                                           "These are the closest names which I can find from your query, please choose from the buttons below : ",
                                           response_card)
            else:
                slots['gmo_info'] = new_gmo_info[0]
                gmo_info = new_gmo_info[0]
        count = validation_query_creator(table, 'GMO_REGION', gmo_info.upper())
        if (count) == 0:
            session_attributes['gmo_retry_count'] = int(
                session_attributes['gmo_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'gmo_info',
                               "You have entered incorrect <b> GMO Region – {} </b>. Please enter correct GMO Region to proceed further. <br>".format(gmo_info))
    if study_number:
        count = validation_query_creator(table, 'study_number', study_number)
        if (count) == 0:
            session_attributes['study_number_retry_count'] = int(
                session_attributes['study_number_retry_count'])+1

            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'study_number',
                               "You have entered incorrect <b> Study Number – {} </b>. Please enter correct Study Number to proceed further. <br>".format(study_number))
    if country:
        if country.lower() in ['us', 'usa', 'united state']:
            country = "United States"
        if country.lower() in ['uk', 'united kingdoms']:
            country = "United Kingdom"
        new_country = find_metric_match(country, "country")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_country:
            if len(new_country) > 1:
                response_card = build_response_card(new_country)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'country',
                                           "These are the closest names which I can find from your query, please choose from the buttons below : ",
                                           response_card)
            else:
                slots['country'] = new_country[0]
                country = new_country[0]
        count = validation_query_creator(table, 'country', country.upper())
        if (count) == 0:
            session_attributes['country_retry_count'] = int(
                session_attributes['country_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'country',
                               "You have entered incorrect <b> Country – {} </b>. Please enter correct Country to proceed further. <br>".format(country))
    if hub_info:
        if hub_info.lower() in ['us', 'usa', 'united state']:
            hub_info = "United States"
        if hub_info.lower() in ['uk', 'united kingdoms']:
            hub_info = "UK Hub"
        new_hub_info = find_metric_match(hub_info, "enrollment hub")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_hub_info:
            if len(new_hub_info) > 1:
                response_card = build_response_card(new_hub_info)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'hub_info',
                                           "These are the closest names which I can find from your query, please choose from the buttons below :",
                                           response_card)
            else:
                slots['hub_info'] = new_hub_info[0]
                hub_info = new_hub_info[0]
        count = validation_query_creator(table, 'hub', hub_info.upper())
        logger.info(f"Func: validate_enrolment_flow_intent \n validation_query_creator count: {count} ")

        if (count) == 0:
            session_attributes['hub_retry_count'] = int(
                session_attributes['hub_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'hub_info',
                               "You have entered incorrect <b> Hub – {} </b>. Please enter correct Hub name to proceed further. <br>".format(hub_info))
    if not study_number:
        return elicit_slot(
            session_attributes,
            intent_request['currentIntent']['name'],
            slots,
            "study_number",
            'You have selected <b> % to Plan Enrollment </b>, Great! <br> Enter the Study number to proceed further: <br>')

    if not year_information:
        count = fetch_enrolment_flow(table, study_number, slots, 'year')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       'year_information',
                                       "You have entered <b> Study number - {} </b>. <br> Next, select year from below options: <br>".format(
                                           study_number),
                                       response_card)
    if not month_information:
        count = fetch_enrolment_flow(table, study_number, slots, 'month')
        if len(count) > 0:
            buttton = count.split(",")
            buttton = sorted(buttton, key=lambda m: datetime.strptime(m, "%b"))
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'study_number': study_number,
                                           'year_information': year_information},
                                       'month_information',
                                       "You have selected the <b> Year - {} </b>. <br>Next, select month from below options: <br>".format(
                                           year_information),
                                       response_card)
    if not plan_info:
        buttton = ["Original", "Latest"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'study_number': study_number, 'year_information': year_information,
                                       'month_information': month_information},
                                   'plan_info',
                                   "You have selected the <b> Month - {} </b>. <br> Next, select which enrollment plan you would like to consider: <br>".format(
                                       month_information),
                                   response_card)
    if not grains_info:
        buttton = ["Global", "Region", "Hub", "Country"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'study_number': study_number, 'year_information': year_information,
                                       'month_information': month_information, 'plan_info': plan_info},
                                   'grains_info',
                                   "You have selected <b> Plan -  {} </b>. <br> Next, select any of the options below to proceed further: <br>".format(
                                       plan_info),
                                   response_card)

    if grains_info == "Global":
        session_attributes['vis'] = "spotfire"
        if intent_request['currentIntent']['name'] == "enrolment_flow":
            session_attributes['main_metric'] = "Subject Enrollment"
            session_attributes['metric_name'] = "% to Plan"
        response = fulfill_enrolment_flow(session_attributes, slots)

    elif grains_info == "Country" and not country:
        # session_attributes['country_retry_count']=int(session_attributes['country_retry_count'])+1
        return elicit_slot(
            session_attributes,
            intent_request['currentIntent']['name'],
            {'study_number': study_number, 'year_information': year_information,
                'month_information': month_information, 'plan_info': plan_info, 'grains_info': grains_info},
            "country",
            'Alright, You have selected <b> Country </b>. <br> Next, enter the Country name to proceed further: <br>')
    elif grains_info == "Hub" and not hub_info:
        return elicit_slot(
            session_attributes,
            intent_request['currentIntent']['name'],
            {'study_number': study_number, 'year_information': year_information,
                'month_information': month_information, 'plan_info': plan_info, 'grains_info': grains_info},
            "hub_info",
            'You have selected <b> Hub </b>, Great! <br> Kindly enter the Hub name next: <br>')
    elif grains_info == "Region" and not region_info:
        buttton = ["GMO", "GDO"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'study_number': study_number, 'year_information': year_information,
                                       'month_information': month_information, 'plan_info': plan_info, 'grains_info': grains_info},
                                   'region_info',
                                   "Great! You have selected <b> Region </b>. <br> Next, select any one of the options below: <br>",
                                   response_card)

    if region_info == "GMO" and not gmo_info:
        slots = {'year_information': year_information,
                 'month_information': month_information}
        count = fetch_enrolment_flow(table, study_number, slots, 'GMO_REGION')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(
                session_attributes,
                intent_request['currentIntent']['name'],
                {'study_number': study_number, 'year_information': year_information, 'month_information': month_information,
                    'plan_info': plan_info, 'grains_info': grains_info, 'region_info': region_info},
                "gmo_info",
                'You have selected <b> GMO </b> , Perfect! <br>  Kindly select the GMO region name to proceed further: <br>',
                response_card)

    elif region_info == "GDO" and not gdo_info:
        slots = {'year_information': year_information,
                 'month_information': month_information}
        count = fetch_enrolment_flow(table, study_number, slots, 'GDO_REGION')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(
                session_attributes,
                intent_request['currentIntent']['name'],
                {'study_number': study_number, 'year_information': year_information, 'month_information': month_information,
                    'plan_info': plan_info, 'grains_info': grains_info, 'region_info': region_info},
                "gdo_info",
                'You have selected <b> GDO </b> , Perfect! <br>  Kindly select the GDO region name to proceed further: <br>',
                response_card)

    return delegate(session_attributes, slots)


def enrolment_flow_intent(intent_request):
    logger.info(f"Func: enrolment_flow_intent \n intent_request: {intent_request} ")

    """
     This function validates all the Session attributes for their retry count for % to Plan enrollment Metric.
     Also, reroute to validate_enrolment_flow_intent and fulfill_enrolment_flow accordingly.
     It accepts one parameter (intent_request) from dispatch function.
       
    """

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    study_number_retry_count = try_ex(
        lambda: session_attributes['study_number_retry_count'])
    session_attributes['study_number_retry_count'] = 0 if not study_number_retry_count else int(
        study_number_retry_count)
    country_retry_count = try_ex(
        lambda: session_attributes['country_retry_count'])
    session_attributes['country_retry_count'] = 0 if not country_retry_count else int(
        country_retry_count)
    hub_retry_count = try_ex(lambda: session_attributes['hub_retry_count'])
    session_attributes['hub_retry_count'] = 0 if not hub_retry_count else int(
        hub_retry_count)
    gmo_retry_count = try_ex(lambda: session_attributes['gmo_retry_count'])
    session_attributes['gmo_retry_count'] = 0 if not gmo_retry_count else int(
        gmo_retry_count)
    gdo_retry_count = try_ex(lambda: session_attributes['gdo_retry_count'])
    session_attributes['gdo_retry_count'] = 0 if not gdo_retry_count else int(
        gdo_retry_count)

    response = "none"
    if session_attributes['study_number_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Study Number.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['country_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Country.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['hub_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Hub.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['gdo_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect GDO region.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['gmo_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect GMO region.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if intent_request['invocationSource'] == 'DialogCodeHook':
        return validate_enrolment_flow_intent(intent_request)
    try_ex(lambda: session_attributes.pop('study_number_retry_count'))
    try_ex(lambda: session_attributes.pop('country_retry_count'))
    try_ex(lambda: session_attributes.pop('hub_retry_count'))
    try_ex(lambda: session_attributes.pop('gdo_retry_count'))
    try_ex(lambda: session_attributes.pop('gmo_retry_count'))
    session_attributes['vis'] = "spotfire"
    if intent_request['currentIntent']['name'] == "enrolment_flow":
        session_attributes['main_metric'] = "Subject Enrollment"
        session_attributes['metric_name'] = "% to Plan"
    response = fulfill_enrolment_flow(session_attributes, slots)
    return close(session_attributes, 'Fulfilled', response)


def validate_activation_flow_intent(intent_request):
    logger.info(f"Func: validate_activation_flow_intent \n intent_request: {intent_request} ")
    """
    This function validates % to Plan Activation metric filters - Study number, Grains (Global, Hub, Country)
    It accepts one parameter that is intent_request from activation_flow_intent function.
    
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    user_query = intent_request['inputTranscript'].lower()
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    study_number = slots['study_number'] if slots['study_number'] else re.findall(
        r'\d{8}(?:\.\d{1,2})?', user_query)[0] if re.findall(r'\d{8}(?:\.\d{1,2})?', user_query) else None
    grains_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['grains_info'])
    hub_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['hub_info'])
    country = slots['country']
    table = "SITE_ACTIVATION"

    if study_number:
        count = validation_query_creator(table, 'study_number', study_number)
        if (count) == 0:
            session_attributes['study_number_retry_count'] = int(
                session_attributes['study_number_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'study_number',
                               "You have entered incorrect <b> Study Number – {} </b>. Please enter correct Study Number to proceed further. <br>".format(study_number))
    if country:
        if country.lower() in ['us', 'usa', 'united state']:
            country = "United States"
        if country.lower() in ['uk', 'united kingdoms']:
            country = "United Kingdom"
        new_country = find_metric_match(country, "country")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_country:
            if len(new_country) > 1:
                response_card = build_response_card(new_country)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'country',
                                           "These are the closest names which I can find from your query, please choose from the buttons below :",
                                           response_card)
            else:
                slots['country'] = new_country[0]
                country = new_country[0]
        count = validation_query_creator(table, 'country', country.upper())
        if (count) == 0:
            session_attributes['country_retry_count'] = int(
                session_attributes['country_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'country',
                               "You have entered incorrect <b> Country – {} </b>. Please enter correct Country Name to proceed further. <br>".format(country))
    if hub_info:
        if hub_info.lower() in ['us', 'usa', 'united state']:
            hub_info = "United States"
        if hub_info.lower() in ['uk', 'united kingdoms']:
            hub_info = "UK Hub"
        new_hub_info = find_metric_match(hub_info, "enrollment hub")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_hub_info:
            if len(new_hub_info) > 1:
                response_card = build_response_card(new_hub_info)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'hub_info',
                                           "These are the closest names which I can find from your query, please choose from the buttons below : ",
                                           response_card)
            else:
                slots['hub_info'] = new_hub_info[0]
                hub_info = new_hub_info[0]

        count = validation_query_creator(table, 'hub', hub_info.upper())
        if (count) == 0:
            session_attributes['hub_retry_count'] = int(
                session_attributes['hub_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'hub_info',
                               "You have entered incorrect <b> Hub – {} </b>. Please enter correct Hub Name to proceed further. <br>".format(hub_info))

    if not study_number:
        return elicit_slot(session_attributes,
                           intent_request['currentIntent']['name'],
                           slots,
                           'study_number',
                           "You have selected <b> % to Plan Activation </b>, Great! <br> Enter the Study number to proceed further: <br>")
    if not grains_info:
        buttton = ["Global", "Hub", "Country"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'study_number': study_number},
                                   'grains_info',
                                   "You have entered <b> Study number - {} </b>. <br> Next, select year from below options: <br>".format(
                                       study_number),
                                   response_card)

    if grains_info == "Global":
        session_attributes['vis'] = "spotfire"
        if intent_request['currentIntent']['name'] == "activation_flow":
            session_attributes['main_metric'] = "Site Activation"
            session_attributes['metric_name'] = "% to Plan"
        response = fulfill_enrolment_flow(session_attributes, slots)
    elif grains_info == "Country" and not country:
        # session_attributes['country_retry_count']=int(session_attributes['country_retry_count'])+1
        return elicit_slot(
            session_attributes,
            intent_request['currentIntent']['name'],
            {'study_number': study_number, 'grains_info': grains_info},
            "country",
            'Alright, You have selected <b> Country </b>. <br> Next, enter the Country name to proceed further: <br>')
    elif grains_info == "Hub" and not hub_info:
        return elicit_slot(
            session_attributes,
            intent_request['currentIntent']['name'],
            {'study_number': study_number, 'grains_info': grains_info},
            "hub_info",
            'You have selected <b> Hub </b>, Great! <br> Kindly enter the Hub name next: <br>')
    return delegate(session_attributes, slots)


def activation_flow_intent(intent_request):
    logger.info(f"Func: activation_flow_intent \n intent_request: {intent_request} ")
    """
     This function validates all the Session attributes for their retry count for % to Plan Activation Metric.
     Also, reroute to validate_activation_flow_intent and fulfill_enrolment_flow accordingly.
     It accepts one parameter (intent_request) from dispatch function.
       
    """

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    study_number_retry_count = try_ex(
        lambda: session_attributes['study_number_retry_count'])
    session_attributes['study_number_retry_count'] = 0 if not study_number_retry_count else int(
        study_number_retry_count)
    country_retry_count = try_ex(
        lambda: session_attributes['country_retry_count'])
    session_attributes['country_retry_count'] = 0 if not country_retry_count else int(
        country_retry_count)
    hub_retry_count = try_ex(lambda: session_attributes['hub_retry_count'])
    session_attributes['hub_retry_count'] = 0 if not hub_retry_count else int(
        hub_retry_count)
    response = "none"
    if session_attributes['study_number_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Study Number.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['country_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Country.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['hub_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('study_number_retry_count'))
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Hub.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if intent_request['invocationSource'] == 'DialogCodeHook':
        return validate_activation_flow_intent(intent_request)
    try_ex(lambda: session_attributes.pop('study_number_retry_count'))
    try_ex(lambda: session_attributes.pop('country_retry_count'))
    try_ex(lambda: session_attributes.pop('hub_retry_count'))
    session_attributes['vis'] = "spotfire"
    if intent_request['currentIntent']['name'] == "activation_flow":
        session_attributes['main_metric'] = "Site Activation"
        session_attributes['metric_name'] = "% to Plan"
    response = fulfill_enrolment_flow(session_attributes, slots)
    return close(session_attributes, 'Fulfilled', response)


def validate_studies_meeting_flow_intent(intent_request):
    logger.info(f"Func: validate_studies_meeting_flow_intent \n intent_request: {intent_request} ")
    """
    This function validates Studies Meeting Enrollment and Activation metric filters - Study number, Year, Month, Plan, Study Type & Grains (Global, Hub, Region, Country)
    It accepts one parameter that is intent_request from studies_meeting_flow_intent function.
    
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    user_query = intent_request['inputTranscript'].lower()
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    year_information = try_ex(
        lambda: intent_request['currentIntent']['slots']['year_information'])
    month_information = try_ex(
        lambda: intent_request['currentIntent']['slots']['month_information'])
    plan_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['plan_info'])
    grains_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['grains_info'])
    hub_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['hub_info'])
    region_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['region_info'])
    study_information = try_ex(
        lambda: intent_request['currentIntent']['slots']['study_information'])
    gmo_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['gmo_info'])
    gdo_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['gdo_info'])
    country = slots['country']
    time_period = slots['time_period']
    year = re.findall(r'\b(\d{4})\b', user_query)
    month = re.findall(
        r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may?|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)', user_query)

    if intent_request['currentIntent']['name'] == "studies_meeting_activation":
        table = "SITE_ACTIVATION"
    elif intent_request['currentIntent']['name'] == "studies_meeting_enrolment":
        table = "SUBJECT_ENROLLMENT"

    if time_period or year:

        year = str(year[0])if len(year) > 0 else None
        month = str(month[0])if len(month) > 0 else None
        if time_period is not None:
            month_dict = {'01': 'jan', '02': 'feb', '03': 'mar', '04': 'apr', '05': 'may', '06': 'jun',
                          '07': 'jul', '08': 'aug', '09': 'sep', '10': 'oct', '11': 'nov', '12': 'dec'}
            year_time_period = str(time_period[:4])
            month_time_period = str(
                time_period[time_period.find("-")+1:time_period.find("-")+3])
            month_time_period = month_dict.get(month_time_period)
            year_information = year_time_period if year is None else year
            month_information = month_time_period if month is None else month
        time_period = str(year_information)+"-"+str(month_information)

    if country:
        if country.lower() in ['us', 'usa', 'united state']:
            country = "United States"
        if country.lower() in ['uk', 'united kingdoms']:
            country = "United Kingdom"
        new_country = find_metric_match(country, "country")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_country:
            if len(new_country) > 1:
                response_card = build_response_card(new_country)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'country',
                                           "These are the closest names which I can find from your query, please choose from the buttons below: ",
                                           response_card)
            else:
                slots['country'] = new_country[0]
                country = new_country[0]
        count = validation_query_creator(table, 'country', country.upper())
        if (count) == 0:
            session_attributes['country_retry_count'] = int(
                session_attributes['country_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'country',
                               "You have entered incorrect <b> Country – {} </b>. Please enter correct Country Name to proceed further. <br>".format(country))

    if hub_info:
        if hub_info.lower() in ['us', 'usa', 'united state']:
            hub_info = "United States"
        if hub_info.lower() in ['uk', 'united kingdoms']:
            hub_info = "UK Hub"
        new_hub_info = find_metric_match(hub_info, "enrollment hub")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_hub_info:
            if len(new_hub_info) > 1:
                response_card = build_response_card(new_hub_info)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'hub_info',
                                           "These are the closest names which I can find from your query, please choose from the buttons below: ",
                                           response_card)
            else:
                slots['hub_info'] = new_hub_info[0]
                hub_info = new_hub_info[0]
        count = validation_query_creator(table, 'hub', hub_info.upper())
        logger.info(f"Func: validate_study_contact_information_intent \n validation_query_creator count: {count} ")
        if (count) == 0:
            session_attributes['hub_retry_count'] = int(
                session_attributes['hub_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'hub_info',
                               "You have entered incorrect <b> Hub – {} </b>. Please enter correct Hub Name to proceed further. <br>".format(hub_info))
    if gdo_info:
        new_gdo_info = find_metric_match(gdo_info, "enrollment gdo")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_gdo_info:
            if len(new_gdo_info) > 1:
                response_card = build_response_card(new_gdo_info)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'gdo_info',
                                           "These are the closest names which I can find from your query, please choose from the buttons below : ",
                                           response_card)
            else:
                slots['gdo_info'] = new_gdo_info[0]
                gdo_info = new_gdo_info[0]
        count = validation_query_creator(table, 'GDO_REGION', gdo_info.upper())
        if (count) == 0:
            session_attributes['gdo_retry_count'] = int(
                session_attributes['gdo_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'gdo_info',
                               "You have entered incorrect <b> GDO Region – {} </b>. Please enter correct GDO Region to proceed further. <br>".format(gdo_info))
    if gmo_info:
        if gmo_info.lower() in ['us', 'usa', 'united state']:
            gmo_info = "United States"
        new_gmo_info = find_metric_match(gmo_info, "enrollment gmo")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_gmo_info:
            if len(new_gmo_info) > 1:
                response_card = build_response_card(new_gmo_info)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'gmo_info',
                                           "These are the closest names which I can find from your query, please choose from the buttons below : ",
                                           response_card)
            else:
                slots['gmo_info'] = new_gmo_info[0]
                gmo_info = new_gmo_info[0]
        count = validation_query_creator(table, 'GMO_REGION', gmo_info.upper())
        if (count) == 0:
            session_attributes['gmo_retry_count'] = int(
                session_attributes['gmo_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'gmo_info',
                               "You have entered incorrect <b> GMO Region – {} </b>. Please enter correct GMO Region to proceed further. <br>".format(gmo_info))
    if not year_information:
        #slots = {'year_information':None,'month_information':None,'country':None}
        count = fetch_meeting_flow(table, slots, 'year')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       "year_information",
                                       "You have selected <b> Studies Meeting Plan </b>, Perfect! <br> Next, select the year from the below options: <br>",
                                       response_card)

    if not month_information:
        count = fetch_meeting_flow(table, slots, 'month')
        if len(count) > 0:
            buttton = count.split(",")
            buttton = sorted(buttton, key=lambda m: datetime.strptime(m, "%b"))
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information},
                                       'month_information',
                                       "You have selected the <b> year - {} </b>. <br>Next, select month from below options: <br>".format(
                                           year_information),
                                       response_card)

    if not study_information:
        buttton = ["ALL", "CPP"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'year_information': year_information,
                                       'month_information': month_information},
                                   'study_information',
                                   "You have selected the <b> Month - {} </b>. <br> Next, select any one of the options below to proceed further: <br>".format(
                                       month_information),
                                   response_card)

    if not plan_info and intent_request['currentIntent']['name'] == 'studies_meeting_enrolment':
        buttton = ["Original", "Latest"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'year_information': year_information, 'month_information': month_information,
                                       'study_information': study_information},
                                   'plan_info',
                                   "Next, select which enrollment plan you would like to consider: <br>",
                                   response_card)
    if not grains_info:
        if intent_request['currentIntent']['name'] == 'studies_meeting_enrolment':
            buttton = ["Global", "Region", "Hub", "Country"]
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information, 'month_information': month_information,
                                           'study_information': study_information, 'plan_info': plan_info},
                                       'grains_info',
                                       "Next, select any one of the Grains below to proceed further: <br>",
                                       response_card)
        else:
            buttton = ["Global", "Hub", "Country"]
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information, 'month_information': month_information,
                                           'study_information': study_information},
                                       'grains_info',
                                       "Next, select any one of the Grains below to proceed further: <br>",
                                       response_card)

    if grains_info == 'Global':
        session_attributes['vis'] = "spotfire"
        if intent_request['currentIntent']['name'] == "studies_meeting_activation":
            session_attributes['main_metric'] = "Site Activation"
            session_attributes['metric_name'] = "Studies Meeting Plan"
        elif intent_request['currentIntent']['name'] == "studies_meeting_enrolment":
            session_attributes['main_metric'] = "Subject Enrollment"
            session_attributes['metric_name'] = "Studies Meeting Plan"
        response = fulfill_enrolment_flow(session_attributes, slots)

    elif grains_info == "Hub" and not hub_info:
        if intent_request['currentIntent']['name'] == 'studies_meeting_enrolment':
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                {'year_information': year_information, 'month_information': month_information,
                    'study_information': study_information, 'plan_info': plan_info, 'grains_info': grains_info},
                "hub_info",
                'You have selected <b> Hub </b>, Great! <br> Kindly enter the Hub name next: <br>')
        else:
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                {'year_information': year_information, 'month_information': month_information,
                    'study_information': study_information, 'grains_info': grains_info},
                "hub_info",
                'You have selected <b> Hub </b>, Great! <br> Kindly enter the Hub name next: <br>')

    elif grains_info == "Country" and not country:
        # session_attributes['country_retry_count']=int(session_attributes['country_retry_count'])+1
        if intent_request['currentIntent']['name'] == 'studies_meeting_enrolment':
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                {'year_information': year_information, 'month_information': month_information,
                    'study_information': study_information, 'plan_info': plan_info, 'grains_info': grains_info},
                "country",
                'Alright, You have selected <b> Country </b>. <br> Next, enter the Country name to proceed further: <br>')
        else:
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                {'year_information': year_information, 'month_information': month_information,
                    'study_information': study_information, 'grains_info': grains_info},
                "country",
                'Alright, You have selected <b> Country </b>. <br> Next, enter the Country name to proceed further: <br>')

    elif grains_info == "Region" and not region_info:
        buttton = ["GMO", "GDO"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'year_information': year_information, 'month_information': month_information,
                                       'study_information': study_information, 'plan_info': plan_info, 'grains_info': grains_info},
                                   'region_info',
                                   "Great! You have selected <b> Region </b>. <br> Next, select any one of the options below: <br>",
                                   response_card)

    if region_info == "GMO" and not gmo_info:
        slots = {'year_information': year_information,
                 'month_information': month_information}
        count = fetch_meeting_flow(table, slots, 'GMO_REGION')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information, 'month_information': month_information, 'study_information': study_information,
                                           'plan_info': plan_info, 'grains_info': grains_info, 'region_info': region_info},
                                       'gmo_info',
                                       "You have selected <b> GMO </b> , Perfect! <br>  Kindly select the GMO region name to proceed further: <br>",
                                       response_card)

    if region_info == "GDO" and not gdo_info:
        slots = {'year_information': year_information,
                 'month_information': month_information}
        count = fetch_meeting_flow(table, slots, 'GDO_REGION')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information, 'month_information': month_information, 'study_information': study_information,
                                           'plan_info': plan_info, 'grains_info': grains_info, 'region_info': region_info},
                                       'gdo_info',
                                       "You have selected <b> GDO </b> , Perfect! <br>  Kindly select the GDO region name to proceed further: <br>",
                                       response_card)

    return delegate(session_attributes, slots)


def studies_meeting_flow_intent(intent_request):
    logger.info(f"Func: studies_meeting_flow_intent \n intent_request: {intent_request} ")
    """
     This function validates all the Session attributes for their retry count for Studies Meeting Enrollment and Activation Metric.
     Also, reroute to validate_studies_meeting_flow_intent and fulfill_enrolment_flow accordingly.
     It accepts one parameter (intent_request) from dispatch function.
       
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    country_retry_count = try_ex(
        lambda: session_attributes['country_retry_count'])
    session_attributes['country_retry_count'] = 0 if not country_retry_count else int(
        country_retry_count)
    hub_retry_count = try_ex(lambda: session_attributes['hub_retry_count'])
    session_attributes['hub_retry_count'] = 0 if not hub_retry_count else int(
        hub_retry_count)
    gmo_retry_count = try_ex(lambda: session_attributes['gmo_retry_count'])
    session_attributes['gmo_retry_count'] = 0 if not gmo_retry_count else int(
        gmo_retry_count)
    gdo_retry_count = try_ex(lambda: session_attributes['gdo_retry_count'])
    session_attributes['gdo_retry_count'] = 0 if not gdo_retry_count else int(
        gdo_retry_count)
    response = "none"
    if session_attributes['gdo_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect GDO region.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['gmo_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect GMO region.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['country_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Country.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['hub_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('country_retry_count'))
        try_ex(lambda: session_attributes.pop('hub_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect Hub.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if intent_request['invocationSource'] == 'DialogCodeHook':
        return validate_studies_meeting_flow_intent(intent_request)
    try_ex(lambda: session_attributes.pop('country_retry_count'))
    try_ex(lambda: session_attributes.pop('hub_retry_count'))
    try_ex(lambda: session_attributes.pop('gdo_retry_count'))
    try_ex(lambda: session_attributes.pop('gmo_retry_count'))
    session_attributes['vis'] = "spotfire"
    if intent_request['currentIntent']['name'] == "studies_meeting_activation":
        session_attributes['main_metric'] = "Site Activation"
        session_attributes['metric_name'] = "Studies Meeting Plan"
    elif intent_request['currentIntent']['name'] == "studies_meeting_enrolment":
        session_attributes['main_metric'] = "Subject Enrollment"
        session_attributes['metric_name'] = "Studies Meeting Plan"
    response = fulfill_enrolment_flow(session_attributes, slots)
    return close(session_attributes, 'Fulfilled', response)


def validate_countries_meeting_flow_intent(intent_request):
    logger.info(f"Func: validate_countries_meeting_flow_intent \n intent_request: {intent_request} ")
    """
    This function validates countries Meeting Enrollment and Activation metric filters - Study number, Year, Month, Plan, Study Type & Grains (Global, Hub, Region, Country)
    It accepts one parameter that is intent_request from countries_meeting_flow_intent function.
    
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    user_query = intent_request['inputTranscript'].lower()
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    year_information = try_ex(
        lambda: intent_request['currentIntent']['slots']['year_information'])
    month_information = try_ex(
        lambda: intent_request['currentIntent']['slots']['month_information'])
    plan_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['plan_info'])
    grains_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['grains_info'])
    region_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['region_info'])
    study_information = try_ex(
        lambda: intent_request['currentIntent']['slots']['study_information'])
    gmo_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['gmo_info'])
    gdo_info = try_ex(
        lambda: intent_request['currentIntent']['slots']['gdo_info'])
    time_period = slots['time_period']
    year = re.findall(r'\b(\d{4})\b', user_query)
    month = re.findall(
        r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may?|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)', user_query)

    #table = "EDT_COUNTRY_TABLE"
    if intent_request['currentIntent']['name'] == "countries_meeting_activation":
        table = "SITE_ACTIVATION"
    elif intent_request['currentIntent']['name'] == "countries_meeting_enrolment":
        table = "SUBJECT_ENROLLMENT"

    if time_period or year:
        year = str(year[0])if len(year) > 0 else None
        month = str(month[0])if len(month) > 0 else None
        if time_period is not None:
            month_dict = {'01': 'jan', '02': 'feb', '03': 'mar', '04': 'apr', '05': 'may', '06': 'jun',
                          '07': 'jul', '08': 'aug', '09': 'sep', '10': 'oct', '11': 'nov', '12': 'dec'}
            year_time_period = str(time_period[:4])
            month_time_period = str(
                time_period[time_period.find("-")+1:time_period.find("-")+3])
            month_time_period = month_dict.get(month_time_period)
            year_information = year_time_period if year is None else year
            month_information = month_time_period if month is None else month
        time_period = str(year_information)+"-"+str(month_information)

    if gdo_info:
        new_gdo_info = find_metric_match(gdo_info, "enrollment gdo")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_gdo_info:
            if len(new_gdo_info) > 1:
                response_card = build_response_card(new_gdo_info)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'gdo_info',
                                           "These are the closest names which I can find from your query, please choose from the buttons below : ",
                                           response_card)
            else:
                slots['gdo_info'] = new_gdo_info[0]
                gdo_info = new_gdo_info[0]
        count = validation_query_creator(table, 'GDO_REGION', gdo_info.upper())
        if (count) == 0:
            session_attributes['gdo_retry_count'] = int(
                session_attributes['gdo_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'gdo_info',
                               "We don't have this GDO region {}, please type again.".format(gdo_info))
    if gmo_info:
        if gmo_info.lower() in ['us', 'usa', 'united state']:
            gmo_info = "United States"
        new_gmo_info = find_metric_match(gmo_info, "enrollment gmo")
        data = read_excel("Enrollment.xlsx", "Sheet1")
        if new_gmo_info:
            if len(new_gmo_info) > 1:
                response_card = build_response_card(new_gmo_info)
                return elicit_slot_buttons(session_attributes,
                                           intent_request['currentIntent']['name'],
                                           slots,
                                           'gmo_info',
                                           "These are the closest names which I can find from your query, please choose from the buttons below : ",
                                           response_card)
            else:
                slots['gmo_info'] = new_gmo_info[0]
                gmo_info = new_gmo_info[0]
        count = validation_query_creator(table, 'GMO_REGION', gmo_info.upper())
        if (count) == 0:
            session_attributes['gmo_retry_count'] = int(
                session_attributes['gmo_retry_count'])+1
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               'gmo_info',
                               "We don't have this GMO region {}, please type again.".format(gmo_info))
    if not year_information:
        count = fetch_meeting_flow(table, slots, 'year')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       slots,
                                       "year_information",
                                       "You have selected <b> Countries Meeting Plan </b>, Perfect! <br> Next, select the year from the below options: <br>",
                                       response_card)

    if not month_information:
        count = fetch_meeting_flow(table, slots, 'month')
        if len(count) > 0:
            buttton = count.split(",")
            buttton = sorted(buttton, key=lambda m: datetime.strptime(m, "%b"))
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information},
                                       'month_information',
                                       "You have selected the <b> Year - {} </b>. <br>Next, select month from below options: <br>".format(
                                           year_information),
                                       response_card)

    if not study_information:

        buttton = buttton = ["ALL", "CPP"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'year_information': year_information,
                                       'month_information': month_information},
                                   'study_information',
                                   "You have selected the <b> Month -  {} </b>. <br> Next, select any one of the options below to proceed further: <br>".format(
                                       month_information),
                                   response_card)

    if not plan_info and intent_request['currentIntent']['name'] == 'countries_meeting_enrolment':
        buttton = ["Original", "Latest"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'year_information': year_information, 'month_information': month_information,
                                       'study_information': study_information},
                                   'plan_info',
                                   "Next, select which enrollment plan you would like to consider: <br>",
                                   response_card)
    if not grains_info:
        if intent_request['currentIntent']['name'] == 'countries_meeting_enrolment':
            buttton = ["Global", "Region"]
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information, 'month_information': month_information,
                                           'study_information': study_information, 'plan_info': plan_info},
                                       'grains_info',
                                       "Next, select any one of the Grains below: <br>",
                                       response_card)
        else:
            buttton = ["Global"]
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information, 'month_information': month_information,
                                           'study_information': study_information},
                                       'grains_info',
                                       "Next, select any one of the Grains below: <br>",
                                       response_card)

    if grains_info == 'Global':
        session_attributes['vis'] = "spotfire"
        if intent_request['currentIntent']['name'] == "countries_meeting_activation":
            session_attributes['main_metric'] = "Site Activation"
            session_attributes['metric_name'] = "Countries Meeting Plan"
        elif intent_request['currentIntent']['name'] == "countries_meeting_enrolment":
            session_attributes['main_metric'] = "Subject Enrollment"
            session_attributes['metric_name'] = "Countries Meeting Plan"
        response = fulfill_enrolment_flow(session_attributes, slots)

    elif grains_info == "Region" and not region_info:
        buttton = ["GMO", "GDO"]
        response_card = build_response_card(buttton)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {'year_information': year_information, 'month_information': month_information,
                                       'study_information': study_information, 'plan_info': plan_info, 'grains_info': grains_info},
                                   'region_info',
                                   "Great! You have selected <b> Region </b>. <br> Next, select any one of the options below: <br>",
                                   response_card)

    if region_info == "GMO" and not gmo_info:
        slots = {'year_information': year_information,
                 'month_information': month_information}
        count = fetch_meeting_flow(table, slots, 'GMO_REGION')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information, 'month_information': month_information, 'study_information': study_information,
                                           'plan_info': plan_info, 'grains_info': grains_info, 'region_info': region_info},
                                       'gmo_info',
                                       "You have selected <b> GMO </b> , Perfect! <br>  Kindly select the GMO region name to proceed further: <br>",
                                       response_card)

    elif region_info == "GDO" and not gdo_info:
        slots = {'year_information': year_information,
                 'month_information': month_information}
        count = fetch_meeting_flow(table, slots, 'GDO_REGION')
        if len(count) > 0:
            buttton = count.split(",")
            response_card = build_response_card(buttton)
            return elicit_slot_buttons(session_attributes,
                                       intent_request['currentIntent']['name'],
                                       {'year_information': year_information, 'month_information': month_information, 'study_information': study_information,
                                           'plan_info': plan_info, 'grains_info': grains_info, 'region_info': region_info},
                                       'gdo_info',
                                       "You have selected <b> GDO </b> , Perfect! <br>  Kindly select the GDO region name to proceed further: <br>",
                                       response_card)

    return delegate(session_attributes, slots)


def countries_meeting_flow_intent(intent_request):
    logger.info(f"Func: countries_meeting_flow_intent \n intent_request: {intent_request} ")
    """
     This function validates all the Session attributes for their retry count for Countries Meeting Enrollment and Activation Metric.
     Also, reroute to validate_countries_meeting_flow_intent and fulfill_enrolment_flow accordingly.
     It accepts one parameter (intent_request) from dispatch function.
       
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    slots = try_ex(lambda: intent_request['currentIntent']['slots'])
    gmo_retry_count = try_ex(lambda: session_attributes['gmo_retry_count'])
    session_attributes['gmo_retry_count'] = 0 if not gmo_retry_count else int(
        gmo_retry_count)
    gdo_retry_count = try_ex(lambda: session_attributes['gdo_retry_count'])
    session_attributes['gdo_retry_count'] = 0 if not gdo_retry_count else int(
        gdo_retry_count)
    response = "none"
    if session_attributes['gdo_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect GDO region.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if session_attributes['gmo_retry_count'] >= 3:
        try_ex(lambda: session_attributes.pop('gmo_retry_count'))
        try_ex(lambda: session_attributes.pop('gdo_retry_count'))
        response = "Sorry, it looks like you have entered the incorrect GMO region.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly. <br>Thank you!"
        return close(session_attributes, 'Fulfilled', response)
    if intent_request['invocationSource'] == 'DialogCodeHook':
        return validate_countries_meeting_flow_intent(intent_request)
    try_ex(lambda: session_attributes.pop('gdo_retry_count'))
    try_ex(lambda: session_attributes.pop('gmo_retry_count'))
    session_attributes['vis'] = "spotfire"
    if intent_request['currentIntent']['name'] == "countries_meeting_activation":
        session_attributes['main_metric'] = "Site Activation"
        session_attributes['metric_name'] = "Countries Meeting Plan"
    elif intent_request['currentIntent']['name'] == "countries_meeting_enrolment":
        session_attributes['main_metric'] = "Subject Enrollment"
        session_attributes['metric_name'] = "Countries Meeting Plan"
    response = fulfill_enrolment_flow(session_attributes, slots)
    return close(session_attributes, 'Fulfilled', response)


def metric_flow_intent(intent_request):
    logger.info(f"Func: metric_flow_intent \n intent_request: {intent_request} ")
    """
       This function accepts one parameter - intent_request.
       It reads the excel file "MetricCombination" from S3 bucket and creates multiple Metric name options and sub- options accordingly under Metric Value.
    
    """
    data = read_excel("MetricCombination.xlsx", "Sheet1")
    
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
    }
    #metric_options = try_ex(lambda: intent_request['currentIntent']['slots']['options'])

    metric_options = intent_request['inputTranscript']
    logger.info(metric_options)
    related_to = try_ex(lambda: session_attributes['related_to'])
    main_metric = try_ex(lambda: session_attributes['main_metric'])
    choice_1 = try_ex(lambda: session_attributes['choice_1'])
    choice_2 = try_ex(lambda: session_attributes['choice_2'])
    if not related_to:
        session_attributes['related_to'] = metric_options
    if not main_metric and related_to:
        session_attributes['main_metric'] = metric_options
    if not choice_1 and main_metric and related_to:
        session_attributes['choice_1'] = metric_options
    if not choice_2 and choice_1 and main_metric and related_to:
        session_attributes['choice_2'] = metric_options
    related_to = try_ex(lambda: session_attributes['related_to'])
    main_metric = try_ex(lambda: session_attributes['main_metric'])
    choice_1 = try_ex(lambda: session_attributes['choice_1'])
    choice_2 = try_ex(lambda: session_attributes['choice_2'])

    if related_to:
        data = data[data['Related to'] == related_to]
        options = list(data['Main Metric'].unique())
        options = [i for i in options if str(i) != 'nan']
    if main_metric:
        data = data[data['Main Metric'] == main_metric]
        options = list(data['Choice 1'].unique())
        options = [i for i in options if str(i) != 'nan']
    if choice_1:
        data = data[data['Choice 1'] == choice_1]
        options = list(data['Choice 2'].unique())
        options = [i for i in options if str(i) != 'nan']
    if choice_2:
        data = data[data['Choice 2'] == choice_2]
    metric_name = list(data['Metric Name'].unique())
    metric_name = [i for i in metric_name if str(i) != 'nan']

    if len(metric_name) == 0:
        response = "I did not find a perfect match for this metric.<br><br>Please reach out to the CSAR team - <a href='mailto:caas@amgen.com?subject=Amgen Blu:'> <b> caas@amgen.com </b> </a> for further assistance. They will review your request and help you accordingly.<br>  "
        return close(session_attributes, 'Fulfilled', response)
    if len(metric_name) > 1:
        response_card = build_response_card(options)
        return elicit_slot_buttons(session_attributes,
                                   intent_request['currentIntent']['name'],
                                   {},
                                   'options',
                                   "Please choose from the options below:<br>",
                                   response_card)

    if metric_name[0] == "Enrolment":
        return elicit_slot_buttons(session_attributes, 'Greetings', {}, 'queryType', 'You have selected <b>Enrollment</b>, Perfect! <br>Which of the following options can I assist you with?<br> ', build_response_card_dict(None, None, [
            {'text': '% to Plan', 'value': 'planenrolment'},
            {'text': 'Studies Meeting Plan Enrollment',
                'value': 'studiesmeetingplanenrolment'},
            {'text': 'Countries Meeting Plan Enrollment',
                'value': 'countriesmeetingplanenrolement'}
        ]))
    if metric_name[0] == "Activation":
        return elicit_slot_buttons(session_attributes, 'Greetings', {}, 'queryType', 'You have selected <b> Activation</b>, Perfect! <br>Which of the following options can I assist you with?<br> ', build_response_card_dict(None, None, [
            {'text': '% to Plan Activation', 'value': 'planactivation'},
            {'text': 'Studies Meeting Plan Activation',
                'value': 'studiesmeetingplanactivation'},
            {'text': 'Countries Meeting Plan Activation',
                'value': 'countriesmeetingplanactivation'}
        ]))

    metric_name = metric_name[0]

    tableMapper = {'total unforecasted unsubmitted pages': 'UNFORECASTED_UNSUBMITTED_PAGES', 'total unforecasted unsubmitted site pages': 'UNFORECASTED_UNSUBMITTED_PAGES', 'total unforecasted unsubmitted  non-site pages': 'UNFORECASTED_UNSUBMITTED_PAGES', 'in activated pages non-site entered data not present': 'INACTIVATED_PAGES', 'queries >50 days open to answered/closed': 'ANSWERED_QUERIES', 'in activated pages non-site entered data present': 'INACTIVATED_PAGES', 'in activated pages site entered data not present': 'INACTIVATED_PAGES', 'in activated pages site entered data present': 'INACTIVATED_PAGES', 'total signatures outstanding': 'SUMMARY_OF_OUTSTANDING_INV_SIG', '% signature complete (all types)': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'milestone signatures outstanding': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'visit signatures outstanding': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'other signatures outstanding': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total signatures outstanding zero to thirty days': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total signatures outstanding thirtyone to sixty days': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total signatures outstanding sixty one to ninety days': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total signatures outstanding greater than ninety days': 'SUMMARY_OF_OUTSTANDING_INV_SIG', 'total milestone forms signed': 'MILESTONE_SIGNATURES', 'average number of days for total milestone forms signed': 'MILESTONE_SIGNATURES', '% of milestone forms signed <= 3 days': 'MILESTONE_SIGNATURES', 'milestone forms signed less than or equal to three days': 'MILESTONE_SIGNATURES', 'milestone forms signed four to six days': 'MILESTONE_SIGNATURES', 'milestone forms signed seven to ten days': 'MILESTONE_SIGNATURES', 'milestone forms signed greater than ten days': 'MILESTONE_SIGNATURES', 'visit signatures total signed': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures % signed <= 30 days': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures signed less than or equal to thirty days': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures signed thirty one to sixty days': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures signed sixtyone to ninety days': 'VISIT_SIGNATURES_DETAILED_TABL', 'visit signatures signed greater than ninety days': 'VISIT_SIGNATURES_DETAILED_TABL', 'in active logline on active page non-site entered data not present': 'INACTIVE_LOGLINES_ON_ACTIVE_PA', 'in active logline on active page non-site entered data present': 'INACTIVE_LOGLINES_ON_ACTIVE_PA',
                   'in active logline on active page site entered data not present': 'INACTIVE_LOGLINES_ON_ACTIVE_PA', 'in active logline on active page site entered data present': 'INACTIVE_LOGLINES_ON_ACTIVE_PA', 'total pages outstanding': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding (site)': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding (non-site)': 'OUTSTANDING_PAGES_TABLE', 'total pages to be inactivated': 'OUTSTANDING_PAGES_TABLE', 'total outstanding blank pages': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding zero to five days': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding six to fifteen days': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding sixteen to thirty days': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding greater than thirty days': 'OUTSTANDING_PAGES_TABLE', 'total pages outstanding percentage greater than thirty days': 'OUTSTANDING_PAGES_TABLE', 'total outstanding queries': 'QUERIES_OUTSTANDING_TABLE', 'total open queries': 'QUERIES_OUTSTANDING_TABLE', 'total answered queries': 'QUERIES_OUTSTANDING_TABLE', 'total query': 'ANSWERED_QUERIES', 'total outstanding (re-queries)': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding (ipd queries)': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries zero to seven days': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries eight to thirteen days': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries fourteen to twenty days': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries twenty one to fifty days': 'QUERIES_OUTSTANDING_TABLE', 'total outstanding queries greater than fifty days': 'QUERIES_OUTSTANDING_TABLE', 'percentage of total outstanding queries greater than fifty days': 'QUERIES_OUTSTANDING_TABLE', 'total pages forecasted': 'FORECASTED_PAGES_TABLE', 'total pages forecasted (site)': 'FORECASTED_PAGES_TABLE', 'total pages forecasted (non-site)': 'FORECASTED_PAGES_TABLE', 'total pages forecasted to be inactivated': 'FORECASTED_PAGES_TABLE', 'total forecasted blank pages': 'FORECASTED_PAGES_TABLE', 'total submitted pages': 'SUBMITTED_PAGES', 'pages submitted <=7days': 'SUBMITTED_PAGES', 'pages submitted <=15 days': 'SUBMITTED_PAGES', 'pages submitted >90 days': 'SUBMITTED_PAGES', 'queries <=7days open to answer/closed': 'ANSWERED_QUERIES', 'queries 8-13 days open to answered/closed': 'ANSWERED_QUERIES', 'queries 14-20 days open to answered/closed': 'ANSWERED_QUERIES', 'queries 21-50 days open to answered/closed': 'ANSWERED_QUERIES'}
    session_attributes['table_name'] = tableMapper[metric_name]
    session_attributes['from_intent'] = 'metric_flow'
    response = fulfill_dashboard_metric_value(
        session_attributes, {'metric_name': metric_name})
    return close(session_attributes, 'Fulfilled', response)

def assign_correct_study_number(event):
    logger.info(f"Func: assign_correct_study_number \n event: {event} ")
    slots = try_ex(lambda: event['currentIntent']['slots'])
    original_study_number = try_ex(lambda: event['currentIntent']['slotDetails']['study_number']['originalValue'])

    if original_study_number:
        resolutions = re.findall(r'\d{8}(?:\.\d{1,2})?', original_study_number)
        if len(resolutions)>= 1:
            original_study_number = resolutions[0]
            event['currentIntent']['slots']['study_number'] = original_study_number
    return event
    
def assign_correct_metric_name(event):
    """ 
    Function is called when metric_name slot is elicited and lex returns a value. Lex sometimes internally updates
    the value of metric_name in 'original_value'. Function assigns the inputTranscript as the original value to mitigate
    error
    Input : event - the intent request json structure
    Output : event - the intent request json structure with updated value for originalValue of metric_name 
    """
    logger.info(f"Func: assign_correct_metric_name \n event: {event} ")
    input_transcript =  try_ex(lambda: event['inputTranscript'])
    original_metric_name = try_ex(lambda: event['currentIntent']['slotDetails']['metric_name']['originalValue'])
    if original_metric_name:
        event['currentIntent']['slotDetails']['metric_name']['originalValue'] = input_transcript
        event['currentIntent']['slots']['metric_name'] = input_transcript
    return event


def dispatch(intent_request):
    logger.info(f"Func: dispatch \n intent_request: {intent_request} ")
    """
      This function accepts one parameter as intent_request from lambda_handler.
      Later, passes the control over to intents according to the user input.
    """

    slot_to_elicit = try_ex(lambda: intent_request['recentIntentSummaryView'][0]['slotToElicit'])
    logger.info(f"Func: dispatch \n recentIntentSummaryView: {intent_request['recentIntentSummaryView']} ")
    if slot_to_elicit:
        logger.info(f"Func: dispatch \n slot_to_elicit: {slot_to_elicit} ")
        intent_request['sessionAttributes'][slot_to_elicit] = intent_request['inputTranscript']
        
    slot_elicited = try_ex(lambda: intent_request['sessionAttributes']['slot_elicited'])
    if slot_elicited == 'study_number':
        intent_request = assign_correct_study_number(intent_request)
    elif slot_elicited == 'metric_name':
        intent_request = assign_correct_metric_name(intent_request)
    intent_name = intent_request['currentIntent']['name']
    
    
    

    if intent_name == 'faq_fall_back':
        return faq_fall_back_intent(intent_request)
    if intent_name == 'FAQ':
        return faq_fall_back_intent(intent_request)
    if intent_name == 'collibra_metric_information':
        return collibra_metric_information_intent(intent_request)
    if intent_name == 'dashboard_metric_value':
        return dashboard_metric_value_intent(intent_request)
    if intent_name == 'study_contact_information':
        return study_contact_information_intent(intent_request)
    if intent_name == 'cap_rule_information':
        return cap_rule_information_intent(intent_request)
    if intent_name == 'collibra_metric_report_name':
        return collibra_metric_report_name_intent(intent_request)
    if intent_name == 'Greetings':
        return Greetings_intent(intent_request)
    if intent_name == 'yes_no_intent':
        return yes_no_intent(intent_request)
    if intent_name == 'metric_flow':
        return metric_flow_intent(intent_request)
    if intent_request['currentIntent']['name'] == 'enrolment_flow':
        return enrolment_flow_intent(intent_request)
    if intent_request['currentIntent']['name'] == 'activation_flow':
        return activation_flow_intent(intent_request)
    if intent_request['currentIntent']['name'] == 'studies_meeting_enrolment':
        return studies_meeting_flow_intent(intent_request)
    if intent_request['currentIntent']['name'] == 'studies_meeting_activation':
        return studies_meeting_flow_intent(intent_request)
    if intent_request['currentIntent']['name'] == 'countries_meeting_enrolment':
        return countries_meeting_flow_intent(intent_request)
    if intent_request['currentIntent']['name'] == 'countries_meeting_activation':
        return countries_meeting_flow_intent(intent_request)


def lambda_handler(event, context):
    logger.info(f"Func: lambda_handler \n event: {event} \n context : {context}")
    """
      This is the very first function in Lambda. 
      It accepts two parameters - event and context. Later, passes event to dispatch for further processing.
    """
    dispatch_event = dispatch(event)
    logger.info(f"Func: lambda_handler RETURN \n dispatch_event: {dispatch_event} \n context : {context}")
    return dispatch_event
