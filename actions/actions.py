from gettext import NullTranslations
from operator import truediv
import os
import json
import re
from typing import Dict, Text, Any, List
import logging
from urllib import response
from dateutil import parser
import sqlalchemy as sa
import sqlite3
from numpy import random
import actions.mysql as mysql

import twilio
from twilio.rest import Client

import pymongo

import spacy
import en_core_web_sm
import nltk
from nltk.corpus import wordnet
from bltk.langtools import PosTagger
from bltk.langtools import Tokenizer

import bangla
from banglanum2words import num_convert
from num2words import num2words

import datetime
from datetime import date

from rasa_sdk.events import ReminderScheduled

#Global variable is here
#-----------------------------------------------------
nlp = en_core_web_sm.load()
nlu = spacy.load("en_core_web_sm")
UserText = None
GlobalList = []
flag = False
#-----------------------------------------------------

from rasa_sdk.events import SlotSet, ActionReverted, UserUttered, Form, BotUttered
from rasa_sdk.forms import REQUESTED_SLOT

from rasa_sdk.interfaces import Action
from rasa_sdk.events import (
    SlotSet,
    EventType,
    ActionExecuted,
    SessionStarted,
    Restarted,
    FollowupAction,
    UserUtteranceReverted,
    AllSlotsReset,
)
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher

from actions.parsing import (
    parse_duckling_time_as_interval,
    parse_duckling_time,
    get_entity_details,
    parse_duckling_currency,
)

from actions.profile_db import create_database, ProfileDB

from actions.custom_forms import CustomFormValidationAction
from rasa_sdk.types import DomainDict
from actions.converter import is_ascii, BnToEn_Word, BnToEn, amount_in_word, numberTranslate

db_manager = mysql.DBManager()
logger = logging.getLogger(__name__)

# The profile database is created/connected to when the action server starts
# It is populated the first time `ActionSessionStart.run()` is called.

PROFILE_DB_NAME = os.environ.get("PROFILE_DB_NAME", "profile")
PROFILE_DB_URL = os.environ.get("PROFILE_DB_URL", f"sqlite:///{PROFILE_DB_NAME}.db")
ENGINE = sa.create_engine(PROFILE_DB_URL)
create_database(ENGINE, PROFILE_DB_NAME)

profile_db = ProfileDB(ENGINE)

FORM_SLOT_UTTER = {
    'check_balance_form': 'utter_ask_account_number',
    'bKash_form': 'utter_ask_account_number',
    'Card_Activation_form': 'utter_ask_card_number',
    'Card_DeActivation_form': 'utter_ask_card_number',
    'Credit_card_limit_form': 'utter_ask_card_number',
    'cheque_form': 'utter_ask_cheque_number',
}
class ActionSessionStart(Action):
    """Executes at start of session"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_session_start"

    @staticmethod
    def _slot_set_events_from_tracker(
        tracker: "Tracker",
    ) -> List["SlotSet"]:
        """Fetches SlotSet events from tracker and carries over keys and values"""

        # when restarting most slots should be reset
        relevant_slots = ["currency"]

        return [
            SlotSet(
                key=event.get("name"),
                value=event.get("value"),
            )
            for event in tracker.events
            if event.get("event") == "slot" and event.get("name") in relevant_slots
        ]

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
        """Executes the custom action"""
        # the session should begin with a `session_started` event
        events = [SessionStarted()]

        events.extend(self._slot_set_events_from_tracker(tracker))

        # create a mock profile by populating database with values specific to tracker.sender_id
        profile_db.populate_profile_db(tracker.sender_id)
        currency = profile_db.get_currency(tracker.sender_id)

        #-----------------------------------------Session Id Exists or Not-------------------------------
        
        sv=tracker.current_slot_values()
        sv_json_object = json.dumps(sv, indent = 4)
        phone = tracker.get_slot("phone_number")
        print("session started and set everything Null to DB initially")
        account = db_manager.set_session_id(
                tracker.sender_id, phone, sv_json_object
            )
        print(account)
        
        #---------------------------------------------------------------------------------------------------------------

        # initialize slots from mock profile
        events.append(SlotSet("currency", currency))

        # add `action_listen` at the end
        events.append(ActionExecuted("action_listen"))

        return events


class ActionRestart(Action):
    """Executes after restart of a session"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_restart"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
        """Executes the custom action"""
        return [Restarted(), FollowupAction("action_session_start")]

class ActionResetSlots(Action):
    """action_reset_all_slots"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_reset_all_slots"
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print ("slots are being reset")
        return [AllSlotsReset()]

# class ResetCardNumber(Action):
#     """action_reset_card_number"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_reset_card_number"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         """Executes the action"""
#         print("Reset Slot Function Called.")
#         return[
#                 SlotSet("card_number", None),
#                 SlotSet("Incomplete_Story", True),
#             ]

# class ActionCallCut(Action):
#     """Action_Call_Cut"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "Action_Call_Cut"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         res = tracker.latest_message['intent'].get('name')
#         print(f"intent from user is {res}")
#         """Executes the action"""
#         print("Action_Call_Cut")
#         if tracker.latest_message['intent'].get('name') == "affirm":
#             print(tracker.latest_message['intent'].get('name'))
#             dispatcher.utter_message(text="CC")
#         if tracker.latest_message['intent'].get('name') == "deny":
#             print(tracker.latest_message['intent'].get('name'))
#             dispatcher.utter_message(text="CC")
#         return[AllSlotsReset()]

# class ResetAmount(Action):
#     """action_reset_AMOUNT"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_reset_AMOUNT"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         """Executes the action"""
#         print("Reset Slot Function Called.")
#         return[
#                 SlotSet("amount-of-money", None),
#                 SlotSet("Incomplete_Story", True),
#             ]
# class AffirmOrDenyCardNumber(Action):
#     """action_check_response"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_check_response"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
        
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check Function Called.")

#         if tracker.latest_message['intent'].get('name') == "affirm":
#             print("Got, Yes")
#             print(tracker.latest_message['intent'].get('name'))
#             return []
#         if tracker.latest_message['intent'].get('name') == "deny":
#             tracker.slots["card_number"] = None
#             print(tracker.slots["card_number"])
#             print(tracker.latest_message['intent'].get('name'))
#             # return [FollowupAction('card_bill_form_c_number')]
#             return [SlotSet("card_number", None), SlotSet("card_check", True), Form("card_bill_form_c_number")]

# class ActionCardnumberCard(FormValidationAction):
#     """validate_card_bill_form_c_number"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "validate_card_bill_form_c_number"

#     async def validate_card_number(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         """Executes the action"""
        
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
        
        
#         print("validate card number")
#         card = tracker.get_slot("card_number")
#         print("card Number is : ", card)
        
        
#         #BANGLA Check Here
#         if (not is_ascii(card)):  #If Bangla then enter here. is_ascii(otp) True for English
#             cn = None
#             if card.isnumeric():
#                 cn = BnToEn(card)
#                 print(str(cn))
#                 card = str(cn)
#                 print("card Number is ", card)
#                 tracker.slots["card_number"] = card
#                 if len(card)!=10 or card == None:
#                     dispatcher.utter_message(response="utter_invalidCARDnumber")
#                     return [
#                             SlotSet("card_number", None),
#                             SlotSet("Incomplete_Story", True),
#                             ]
#                 else:
#                     print("Correct card Number")
#                     # account = db_manager.set_slot_value(tracker.sender_id, "card_number", card)
#                     return [
#                             SlotSet("card_number", card),
#                             SlotSet("Incomplete_Story", True),
#                             FollowupAction('action_tell_CardNumber'),
#                             ]
#         else:
#             if len(card)!=10 or card == None:
#                 dispatcher.utter_message(response="utter_invalidCARDnumber")
#                 return [
#                         SlotSet("card_number", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#             else:
#                 print("Correct card Number")
#                 # account = db_manager.set_slot_value(tracker.sender_id, "card_number", card)
                
#                 return [
#                         SlotSet("card_number", card),
#                         SlotSet("Incomplete_Story", True),
#                         FollowupAction('action_tell_CardNumber'),
#                         ]


# class ActionValidateAMOUNT(FormValidationAction):

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "validate_card_bill_form_amount"
#     async def validate_amount_of_money(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
    
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
        
#         print("CCV in amount validation:", tracker.get_slot("CCV"))
#         amount = tracker.get_slot("amount-of-money")
#         print("amount inside function: ", amount)

#         account_balance = profile_db.get_account_balance(tracker.sender_id)

#         number = None
#         #BANGLA Check Here
#         if(not is_ascii(amount)):  #If Bangla then enter here
#             print("Hello, Check Bangla")
#             if amount.isnumeric():
#                 number = BnToEn(amount)
#                 amount = str(number)
#                 print("Number : ", number)
#                 print(amount)
#                 if(int(amount)<=0):
#                     dispatcher.utter_message(response="utter_invalidAMOUNT")
#                     # print("1")
#                     return[
#                             SlotSet("amount-of-money", None),
#                             SlotSet("Incomplete_Story", True),
#                             ]
#                 else:
#                     # print("2")
#                     # account = db_manager.set_slot_value(tracker.sender_id, 'amount-of-money', amount)
#                     return[
#                             SlotSet("amount-of-money", None),
#                             SlotSet("Incomplete_Story", True),
#                             ]
#             else:
#                 # print("3")
#                 return[ SlotSet("amount-of-money", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#         else:
#             # print("4")
#             if(int(amount)<=0):
#                 # print("5")
#                 dispatcher.utter_message(response="utter_invalidAMOUNT")
#                 # return {"amount-of-money": None}
#                 return[
#                         SlotSet("amount-of-money", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#             else:
#                 # account = db_manager.set_slot_value(tracker.sender_id, 'amount-of-money', amount)
#                 print("Amount is ", amount)
#                 return[
#                         SlotSet("amount-of-money", None),
#                         SlotSet("Incomplete_Story", True),
#                         ActionExecuted("action_tell_Amount"),
#                         ]
#                 # return[SlotSet("amount-of-money", None), FollowupAction('action_tell_Amount')]

class ResetACNumber(Action):
    """action_reset_account_number"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_reset_account_number"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        """Executes the action"""
        print("Reset Slot Function Called.")
        return[
                SlotSet("account_number", None),
                SlotSet("Incomplete_Story", True),
            ]
class ResetPIN(Action):
    """action_reset_PIN"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_reset_PIN"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        print(tracker.latest_message['intent'].get('name'))
        """Executes the action"""
        print("Reset Slot Function Called.")
        return[
                SlotSet("PIN", None),
                SlotSet("Incomplete_Story", True),
            ]

class ResetPINandACnumer(Action):
    """action_reset_PINandACnumer"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_reset_PINandACnumer"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        print(tracker.latest_message['intent'].get('name'))
        """Executes the action"""
        print("Reset AC number and PIN Function Called.")
        story_status = tracker.get_slot("Incomplete_Story")
        print(f"Story Incomplete: {story_status}")

        if story_status == True:
            # return [Form(None), SlotSet("requested_slot", None)]
            return [UserUtteranceReverted()]
        # return[
        #         SlotSet("PIN", None),
        #         SlotSet("account_number", None),
        #     ]
        return[
                SlotSet("PIN", None),
                SlotSet("Incomplete_Story", True),
                SlotSet("account_number_confirm", None),
                SlotSet("PIN_confirm", None),
                SlotSet("ACtext", None),
                SlotSet("PIN_Text", None),
            ]

class WeatherAction(Action):
    """action_weather"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_weather"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        currentloop = tracker.active_loop.get('name')
        print(f"Loop name: {currentloop}")

        story_status = tracker.get_slot("Incomplete_Story")
        print(f"Story Incomplete: {story_status}")

        # if currentloop == None:
        #     dispatcher.utter_message(response = "utter_weather_query")
        #     return []
        #     # return [FollowupAction('action_tell_ACNumber')]
        if story_status != True:
            dispatcher.utter_message(response = "utter_weather_query")
            # return [Form(None), SlotSet("requested_slot", None)]
            return []
            
        else:
            pass
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            # return [FollowupAction('action_check_AC_Number')]
            return [UserUtteranceReverted()]

# class OtherInformationPin(Action):
#     """action_Other_Utter_PIN"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_Other_Utter_PIN"
    
#     # @staticmethod
#     # def start_story_events(story_intent):
#     #     # type: (Text) -> List[Dict]
#     #     return [ActionExecuted("action_listen")] + [UserUttered("/" + story_intent, {
#     #         "intent": {"name": story_intent, "confidence": 1.0},
#     #         "entities": {}
#     #     })]

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check Function Called.")

#         if tracker.latest_message['intent'].get('name') == "affirm":
#             print("Got, Yes")
#             # return self.start_story_events("request.check_balance")
#             # return [FollowupAction('action_tell_ACNumber')]
#             currentloop = tracker.active_loop.get('name')
#             if currentloop != None:
#                 return [Form(currentloop)]
#             else:
#                 return [Form("check_Balance_PIN_form")]
#         elif tracker.latest_message['intent'].get('name') == "deny":
#             print(tracker.latest_message['intent'].get('name'))
#             dispatcher.utter_message(response="utter_ask_whatelse")
#             # return [FollowupAction('card_bill_form_c_number')]
#             return [
#                     SlotSet("Incomplete_Story", False),
#                     Form(None), 
#                     SlotSet("requested_slot", None),
#                     ]
#         else:
#             pass
        
#         return []

# class OtherInformation(Action):
#     """action_Other_Utter"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_Other_Utter"
    
#     # @staticmethod
#     # def start_story_events(story_intent):
#     #     # type: (Text) -> List[Dict]
#     #     return [ActionExecuted("action_listen")] + [UserUttered("/" + story_intent, {
#     #         "intent": {"name": story_intent, "confidence": 1.0},
#     #         "entities": {}
#     #     })]

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check Function Called.")

#         if tracker.latest_message['intent'].get('name') == "affirm":
#             print("Got, Yes")
#             # return self.start_story_events("request.check_balance")
#             # return [FollowupAction('action_tell_ACNumber')]
#             currentloop = tracker.active_loop.get('name')
#             if currentloop != None:
#                 return [Form(currentloop)]
#             else:
#                 return [Form("check_Balance_ACnum_form")]
#         elif tracker.latest_message['intent'].get('name') == "deny":
#             print(tracker.latest_message['intent'].get('name'))
#             dispatcher.utter_message(response="utter_ask_whatelse")
#             # return [FollowupAction('card_bill_form_c_number')]
#             return [
#                     SlotSet("Incomplete_Story", False),
#                     Form(None), 
#                     SlotSet("requested_slot", None),
#                     ]
#         else:
#             pass
        
#         return []

# class OtherInformationAC(Action):
#     """action_Other_Utter_AC_Num"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_Other_Utter_AC_Num"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check Function Called.")

#         if tracker.latest_message['intent'].get('name') == "explain":
#             dispatcher.utter_message(response = "utter_explain_account_number")
#             # return [FollowupAction('action_tell_ACNumber')]
#         else:
#             dispatcher.utter_message(response = "utter_ask_continue_form")
#             # return [Form(None), SlotSet("requested_slot", None)]
#             return [ActionExecuted('action_listen')]

# class OtherInformationFORpin(Action):
#     """action_Other_check_Intent"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_Other_check_Intent"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check Function Called.")

#         if tracker.latest_message['intent'].get('name') == "explain":
#             dispatcher.utter_message(response = "utter_explain_account_number")
#             # return [FollowupAction('action_tell_ACNumber')]
#         else:
#             dispatcher.utter_message(response = "utter_ask_continue_form")
#             # return [Form(None), SlotSet("requested_slot", None)]
#             return [ActionExecuted('action_listen')]

# class AffirmOrDenyACNumber(Action):
#     """action_check_AC_Number"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_check_AC_Number"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check Function Called.")

#         if tracker.latest_message['intent'].get('name') == "affirm":
#             print("Got, Yes")
#             print(tracker.latest_message['intent'].get('name'))
#             # return[Form("check_Balance_PIN_form")]
#             return []
#         elif tracker.latest_message['intent'].get('name') == "deny":
#             tracker.slots["account_number"] = None
#             print(tracker.slots["account_number"])
#             print(tracker.latest_message['intent'].get('name'))
#             # return [FollowupAction('card_bill_form_c_number')]
#             return [
#                     SlotSet("account_number", None),
#                     SlotSet("account_check",True),
#                     Form("check_Balance_ACnum_form"),
#                     ]
#         # if tracker.latest_message['intent'].get('name') == "weather":
#         else:
#             dispatcher.utter_message(response = "utter_ask_continue_form")
#             return[]
#             # return [FollowupAction('action_tell_ACNumber')]

# class AffirmOrDenyACNumberBkash(Action):
#     """action_check_AC_Number_Bkash"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_check_AC_Number_Bkash"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check Function Called.")

#         if tracker.latest_message['intent'].get('name') == "affirm":
#             print("Got, Yes")
#             print(tracker.latest_message['intent'].get('name'))
#             return[Form("phone_number_form")]
#         elif tracker.latest_message['intent'].get('name') == "deny":
#             tracker.slots["account_number"] = None
#             print(tracker.slots["account_number"])
#             print(tracker.latest_message['intent'].get('name'))
#             # return [FollowupAction('card_bill_form_c_number')]
#             return [SlotSet("account_number", None), SlotSet("account_check",True), Form("check_Balance_ACnum_form")]
#         # if tracker.latest_message['intent'].get('name') == "weather":
#         else:
#             dispatcher.utter_message(response = "utter_ask_continue_form")
#             return[]
#             # return [FollowupAction('action_tell_ACNumber')]


# class ActionACnumber(FormValidationAction):
#     """validate_check_Balance_ACnum_form"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "validate_check_Balance_ACnum_form"

#     async def validate_account_number(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
    
#         """Executes the action"""
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
        
#         print("validate_account_number")
#         ac = tracker.get_slot("account_number")
#         print("AC Number is : ", ac)
        
#         #BANGLA Check Here
#         if (not is_ascii(ac)):  #If Bangla then enter here. is_ascii(otp) True for English
#             cn = None
#             if ac.isnumeric():
#                 cn = BnToEn(ac)
#                 print(str(cn))
#                 ac = str(cn)
#                 print("account Number is ", ac)
#                 tracker.slots["account_number"] = ac
#                 if len(ac)!=8 or ac == None:
#                     dispatcher.utter_message(response="utter_invalidACNumber")
#                     return [SlotSet("account_number", None),
#                             SlotSet("Incomplete_Story", True),
#                             ]
#                     # return {"account_number": None}
#                 else:
#                     print("Correct account Number")
#                     account = db_manager.set_slot_value(tracker.sender_id, "account_number", ac)
#                     # return {"account_number": ac}
#                     return [
#                             SlotSet("account_number", ac),
#                             SlotSet("Incomplete_Story", True),
#                             FollowupAction('action_tell_ACNumber'),
#                             ]
#         else:
#             if len(ac)!=8 or ac == None:
#                 dispatcher.utter_message(response="utter_invalidACNumber")
#                 return [
#                         SlotSet("account_number", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#                 # return {"account_number": None}
#             else:
#                 print("Correct account Number")
#                 # if tracker.get_slot('account_number') in domain['slots']['account_number']['value']:
#                 #     return [SlotSet("account_number", ac), FollowupAction('action_tell_ACNumber'), SlotSet("account_check","False")]
#                 # account = db_manager.set_slot_value(tracker.sender_id, "account_number", ac)
#                 # return {"account_number": ac}
#                 # ActionTellACnumber.run(self, dispatcher, tracker, domain)
#                 return [
#                         SlotSet("account_number", ac),
#                         SlotSet("Incomplete_Story", True),
#                         FollowupAction('action_tell_ACNumber'),
#                         ]

# class ActionTellACnumber(Action):

#     def name(self) -> Text:
#         return "action_tell_ACNumber"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         # tell_ACNumber = next(tracker.get_latest_entity_values("account_number"), None)
#         tell_ACNumber = tracker.get_slot("account_number")
#         check = True
#         if tracker.get_slot("account_check")=="False":
#             check = False
#         number=['জিরো','ওয়ান','টু','থ্রি','ফোর','ফাইভ','সিক্স','সেভেন','এইট','নাইন']
#         if(tell_ACNumber!=None):
#             wr=''
#             for c in tell_ACNumber:
#                 wr=wr+' '+number[int(c)]

#         wr2 = wr.split(" ")
#         for i in range(len(wr2)):
#             wr2[i] = wr2[i]+","
#         wr = ' '.join(wr2)
#         if not tell_ACNumber:
#             msg = f"দুঃখিত, আপনার কথাটি বুঝতে পারিনি ।"
#             dispatcher.utter_message(text=msg)
#             return []
        
#         msg = f"আপনি বলেছেন, {wr} । সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।"
#         wr_r=wr.split(',') # reverse text for last 3 digit
#         else_msg = f"লাস্ট ডিজিট {','.join(wr_r[-4:-1])}, কি আপনার একাউন্ট নাম্বার। ঠিক হলে বলুন, হ্যা ঠিক আছে ।"
#         print('আপনি বলেছেন,', {wr}, '। সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।')
#         print(check)
#         print(type(check))
#         if check:
#             dispatcher.utter_message(text=msg)
#             return [SlotSet("account_check","False")]
#         else:
#             dispatcher.utter_message(text=else_msg)
#             return []

class ActionCustomFallback(Action):
    """Executes at fallBack"""
    
    def name(self) -> Text:
        return "action_custom_fallback"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:

        fall_counter = tracker.get_slot("fallback_counter")
        fall_counter = int(fall_counter) + 1

        if fall_counter > 3:
            return [FollowupAction("action_session_start")]
            # return [Restarted(), FollowupAction("action_session_start")]
        
        print("fallback")
        print(fall_counter)
        if tracker.get_slot("Incomplete_Story") == True:
            print("You are inside a story.")
            return[SlotSet("fallback_counter", float(fall_counter)), UserUtteranceReverted()]

        dispatcher.utter_message(response="utter_default")
        return [SlotSet("fallback_counter", float(fall_counter))]

# class AffirmOrDenyPIN(Action):
#     """action_check_PIN"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_check_PIN"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check Function Called.")

#         if tracker.latest_message['intent'].get('name') == "affirm":
#             print("Got, Yes")
#             print(tracker.latest_message['intent'].get('name'))
#             return []
#         elif tracker.latest_message['intent'].get('name') == "deny":
#             tracker.slots["PIN"] = None
#             print(tracker.slots["PIN"])
#             print(tracker.latest_message['intent'].get('name'))
#             return [SlotSet("PIN", None), Form("check_Balance_PIN_form")]
#         else:
#             dispatcher.utter_message(response = "utter_ask_continue_form")
#             return []


# class ActionAccountCnumber(FormValidationAction):
#     """validate_check_Balance_PIN_form"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "validate_check_Balance_PIN_form"

#     async def validate_PIN(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         """Executes the action"""
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
        
#         print("validate_PIN")
#         pin = tracker.get_slot("PIN")
#         print("PIN Number is : ", pin)
        
#         #BANGLA Check Here
#         if (not is_ascii(pin)):  #If Bangla then enter here. is_ascii(otp) True for English
#             cn = None
#             if pin.isnumeric():
#                 cn = BnToEn(pin)
#                 print(str(cn))
#                 pin = str(cn)
#                 print("pin Number is ", pin)
#                 tracker.slots["PIN"] = pin
#                 if len(pin)!=4 or pin == None:
#                     dispatcher.utter_message(response="utter_invalidPIN")
#                     return [
#                             SlotSet("PIN", None),
#                             SlotSet("Incomplete_Story", True),
#                             ]
#                     # return {"PIN": None}
#                 else:
#                     print("Correct pin Number")
#                     # account = db_manager.set_slot_value(tracker.sender_id, "PIN", pin)
#                     return [
#                             SlotSet("PIN", pin),
#                             SlotSet("Incomplete_Story", True),
#                             ]
#         else:
#             if len(pin)!=4 or pin == None:
#                 dispatcher.utter_message(response="utter_invalidPIN")
#                 return [
#                         SlotSet("PIN", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#                 # return {"PIN": None}
#             else:
#                 print("Correct pin Number")
#                 # account = db_manager.set_slot_value(tracker.sender_id, "PIN", pin)
#                 return [
#                         SlotSet("PIN", pin),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#                 # return {"PIN": pin}

class ActionShowBalance(Action):
    """Shows the balance of bank or credit card accounts"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_show_balance"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        # ac = tracker.get_slot("account_number")
        # # ac_con = tracker.get_slot("account_number_confirm")
        # pin = tracker.get_slot("PIN")
        # # pin_con = tracker.get_slot("PIN_confirm")

        # if ac == None or pin == None:
        #     return [FollowupAction("check_balance_form")]
        
        """Executes the custom action"""
        account_balance=106000
        account_balance=str(int(account_balance))
        amount = tracker.get_slot("amount_transferred")
        if amount:
            amount = float(tracker.get_slot("amount_transferred"))
            init_account_balance = account_balance + amount
            dispatcher.utter_message(
                response="utter_changed_account_balance",
                init_account_balance=f"{init_account_balance:.2f}",
                account_balance=f"{account_balance:.2f}",
            )
        else:
            bangla_numeric_string = bangla.convert_english_digit_to_bangla_digit(account_balance)
            print(bangla_numeric_string)

            account_balance=num_convert.number_to_bangla_words(bangla_numeric_string)
            dispatcher.utter_message(response="utter_account_balance", init_account_balance=account_balance)

        return [
            SlotSet("Incomplete_Story", False),
            SlotSet("PIN", None),
            SlotSet("PIN_confirm", None),
            SlotSet("account_number_confirm", None),
            Form(None),
            SlotSet("requested_slot", None),
        ]
        


# class ActionTellPIN(Action):

#     def name(self) -> Text:
#         return "action_tell_pin"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         tell_pin = tracker.get_slot("PIN")
#         number=['জিরো','ওয়ান','টু','থ্রি','ফোর','ফাইভ','সিক্স','সেভেন','এইট','নাইন']
#         wr=''
#         if(tell_pin!=None):
#             for c in tell_pin:
#                 wr=wr+' '+number[int(c)]
        
#         wr2 = wr.split(" ")
#         for i in range(len(wr2)):
#             wr2[i] = wr2[i]+","
#         wr = ' '.join(wr2)
    
#         if not tell_pin:
#             msg = f"দুঃখিত, আপনার কথাটি বুঝতে পারিনি ।"
#             dispatcher.utter_message(text=msg)
#             return []

#         msg = f"আপনি বলেছেন, {wr} । সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।"
#         print('আপনি বলেছেন,', {wr}, '। সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।')
#         dispatcher.utter_message(text=msg)
#         return []

class ResetBkashTransectionVALUES(Action):
    """action_reset_BkashTransectionVALUES"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_reset_BkashTransectionVALUES"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        """Executes the action"""
        print("Reset bKash related info.")

        currentloop = tracker.active_loop.get('name')
        print(f"Loop name: {currentloop}")

        story_status = tracker.get_slot("Incomplete_Story")
        print(f"Story Incomplete: {story_status}")

        if story_status == True or currentloop != None:
            print("loop is active")
            return[]
            # dispatcher.utter_message(response="utter_ask_continue_form")
            # return [ActionExecuted("action_listen")]
        return[
                SlotSet("account_number_confirm", None),
                SlotSet("phone_number", None),
                SlotSet("phone_number_confirm", None),
                SlotSet("amount-of-money", None),
                SlotSet("amount_confirm", None),
                SlotSet("Incomplete_Story", True),
                SlotSet("NumberInWord", None),
                SlotSet("amountBengaliWord", None),
                SlotSet("ACtext", None),
                SlotSet("PhoneText", None),
            ]
# class ActionValidatePhoneNumber(FormValidationAction):

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "validate_phone_number_form"

#     async def validate_phone_number(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         """Executes the action"""
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
        
#         print("validate_phone_number")
#         phone = tracker.get_slot("phone_number")
#         print("phone Number is : ", phone)
        
#         #BANGLA Check Here
#         if (not is_ascii(phone)):  #If Bangla then enter here. is_ascii(otp) True for English
#             cn = None
#             if phone.isnumeric():
#                 cn = BnToEn(phone)
#                 print(str(cn))
#                 phone = str(cn)
#                 print("phone Number is ", phone)
#                 tracker.slots["phone_number"] = phone
#                 if len(phone)!=11 or phone == None:
#                     dispatcher.utter_message(response="utter_invalidphone")
#                     # return {"phone_number": None}
#                     return [
#                             SlotSet("phone_number", None),
#                             SlotSet("Incomplete_Story", True),
#                             ]
#                 else:
#                     print("Correct phone Number")
#                     # account = db_manager.set_slot_value(tracker.sender_id, "phone_number", phone)
#                     # return {"phone_number": phone}
#                     return [
#                             SlotSet("phone_number", phone),
#                             SlotSet("Incomplete_Story", True),
#                             ]
#         else:
#             if len(phone)!=11 or phone == None:
#                 dispatcher.utter_message(response="utter_invalidphone")
#                 # return {"phone_number": None}
#                 return [
#                         SlotSet("phone_number", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#             else:
#                 print("Correct phone Number")
#                 # account = db_manager.set_slot_value(tracker.sender_id, "phone_number", phone)
#                 # return {"phone_number": phone}
#                 return [
#                         SlotSet("phone_number", phone),
#                         SlotSet("Incomplete_Story", True),
#                         ]

# class ActionTellphone(Action):

#     def name(self) -> Text:
#         return "action_tell_PhoneNumber"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
            
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         tell_phone = next(tracker.get_latest_entity_values("phone_number"), None)
#         number=['জিরো','ওয়ান','টু','থ্রি','ফোর','ফাইভ','সিক্স','সেভেন','এইট','নাইন']
#         if(tell_phone!=None):
#             wr=''
#             for c in tell_phone:
#                 wr=wr+' '+number[int(c)]

#         wr2 = wr.split(" ")
#         for i in range(len(wr2)):
#             wr2[i] = wr2[i]+","
#         wr = ' '.join(wr2)

#         if not tell_phone:
#             msg = f"দুঃখিত, আপনার কথাটি বুঝতে পারিনি ।"
#             dispatcher.utter_message(text=msg)
#             return []

#         msg = f"আপনি বলেছেন, {wr} । সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।"
#         print('আপনি বলেছেন,', {wr}, '। সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।')
#         dispatcher.utter_message(text=msg)
#         return []

# class AffirmOrDenyPhoneNumber(Action):
#     """action_check_phone_Number"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_check_phone_Number"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check phone Function Called.")

#         if tracker.latest_message['intent'].get('name') == "affirm":
#             print("Got, Yes")
#             print(tracker.latest_message['intent'].get('name'))
#         if tracker.latest_message['intent'].get('name') == "deny":
#             # tracker.slots["phone_number"] = None
#             # print(tracker.slots["phone_number"])
#             # print(tracker.latest_message['intent'].get('name'))
#             # return [FollowupAction('card_bill_form_c_number')]
#             return [
#                     SlotSet("phone_number", None),
#                     Form("phone_number_form"),
#                     ]

# class ActionTellamount(Action):

#     def name(self) -> Text:
#         return "action_tell_Amount"

#     def run(
#             self, 
#             dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any],
#     ) -> List[Dict]:
        
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         tell_amount = next(tracker.get_latest_entity_values("amount-of-money"), None)

#         if tell_amount != None:
#             bangla_numeric_string = bangla.convert_english_digit_to_bangla_digit(tell_amount)
#             print(bangla_numeric_string)
#             print(type(bangla_numeric_string))
#             print('bangla_numeric_string: ', len(str(bangla_numeric_string)))
#             if(len(str(bangla_numeric_string))>8):
#                 amount=bangla_numeric_string
#             else:
#                 amount = num_convert.number_to_bangla_words(bangla_numeric_string)

#         if not tell_amount:
#             msg = f"দুঃখিত, আপনার কথাটি বুঝতে পারিনি ।"
#             dispatcher.utter_message(text=msg)
#             return []

#         msg = f"আপনি বলেছেন, {amount} টাকা। সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।"
#         print('আপনি বলেছেন,', {amount}, 'টাকা। সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।')
#         dispatcher.utter_message(text=msg)
#         return []

# class AffirmOrDenyAmount(Action):

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "action_check_amount"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         """Executes the action"""
#         print("response check amount Function Called.")

#         if tracker.latest_message['intent'].get('name') == "affirm":
#             print("Got, Yes")
#             print(tracker.latest_message['intent'].get('name'))
#             return [SlotSet("Incomplete_Story", False)]
#         if tracker.latest_message['intent'].get('name') == "deny":
#             tracker.slots["amount-of-money"] = None
#             print(tracker.slots["amount-of-money"])
#             print(tracker.latest_message['intent'].get('name'))
#             # return [FollowupAction('card_bill_form_c_number')]
#             return [
#                     SlotSet("amount-of-money", None),
#                     SlotSet("Incomplete_Story", False),
#                     Form("card_bill_form_amount"),
#                     ]
class ResetCardActivationInfo(Action):
    """action_reset_Card_Activation_Info"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_reset_Card_Activation_Info"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        global UserText
        print(tracker.latest_message['intent'].get('name'))
        UserText = tracker.latest_message.get('text')
        print(f"User Input: {UserText}")
        """Executes the action"""
        print("Reset Card Activation Related Information Function Called.")
        currentloop = tracker.active_loop.get('name')
        print(f"Loop name: {currentloop}")

        story_status = tracker.get_slot("Incomplete_Story")
        print(f"Story Incomplete: {story_status}")

        if story_status == True or currentloop != None:
            # dispatcher.utter_message(response="utter_ask_continue_form")
            return [ActionExecuted("action_listen")]

        # if story_status == True:
        #     return [UserUtteranceReverted()]
        else:
            return[
                    SlotSet("card_number_confirm", None),
                    SlotSet("Father_Name", None),
                    SlotSet("Mother_Name", None),
                    SlotSet("Birth_Date", None),
                    SlotSet("Incomplete_Story", True),
                    SlotSet("NumberInWord", None),
                    SlotSet("amountBengaliWord", None),
                    SlotSet("CardText", None),
                    ]
class ResetPINandCARDnumer(Action):
    """action_reset_PINandCARDnumer"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_reset_PINandCARDnumer"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        global UserText
        print(tracker.latest_message['intent'].get('name'))
        UserText = tracker.latest_message.get('text')
        print(f"User Input: {UserText}")
        """Executes the action"""
        print("Reset card number and PIN Function Called.")
        currentloop = tracker.active_loop.get('name')
        print(f"Loop name: {currentloop}")

        story_status = tracker.get_slot("Incomplete_Story")
        print(f"Story Incomplete: {story_status}")

        if story_status == True or currentloop != None:
            # dispatcher.utter_message(response="utter_ask_continue_form")
            return [ActionExecuted("action_listen")]

        # if story_status == True:
        #     return [UserUtteranceReverted()]
        
        return[
                SlotSet("PIN", None),
                SlotSet("Incomplete_Story", True),
                SlotSet("NumberInWord", None),
                SlotSet("card_number_confirm", None),
                SlotSet("PIN_confirm", None),
                SlotSet("PIN_Text", None),
                SlotSet("CardText", None),
            ]

# class ActionTellCardNumber(Action):

#     def name(self) -> Text:
#         return "action_tell_CardNumber"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         tell_card = tracker.get_slot("card_number")
#         C_check = True
#         if tracker.get_slot("card_check")=="False":
#             C_check = False
#         number=['জিরো','ওয়ান','টু','থ্রি','ফোর','ফাইভ','সিক্স','সেভেন','এইট','নাইন']
#         if(tell_card!=None):
#             wr=''
#             for c in tell_card:
#                 wr=wr+' '+number[int(c)]

#         wr2 = wr.split(" ")
#         for i in range(len(wr2)):
#             wr2[i] = wr2[i]+","
#         wr = ' '.join(wr2)
        
#         if not tell_card:
#             msg = f"দুঃখিত, আপনার কথাটি বুঝতে পারিনি ।"
#             dispatcher.utter_message(text=msg)
#             return []

#         msg = f"আপনি বলেছেন, {wr} । সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।"
#         wr_r=wr.split(',') # reverse text for last 3 digit
#         else_msg = f"লাস্ট ডিজিট {','.join(wr_r[-5:-1])}, কি আপনার কার্ড নাম্বার। ঠিক হলে বলুন, হ্যা ঠিক আছে ।"
#         print('আপনি বলেছেন,', {wr}, '। সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।')
        
#         if C_check:
#             dispatcher.utter_message(text=msg)
#             return [SlotSet("card_check","False")]
#         else:
#             dispatcher.utter_message(text=else_msg)
#             return []

class OutOfScope(Action):
    """Action_out_of_scope"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "Action_out_of_scope"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        # global counter
        counter=0
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        """Executes the action"""
        print("out_of_scope")
        Input = tracker.latest_message.get('text')
        print(f"User Input was:{Input}")
        print(type(Input))
        if(counter>1):
            dispatcher.utter_message(response="utter_AT")
            counter=0
            return []
            
        if tracker.latest_message['intent'].get('name') == "out_of_scope":
            counter=counter+1
            if "কি মেয়ে নাকি ছেলে" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_1")
            elif "ঘুরতে যাবে" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_2")
            elif "তোমার প্রেমে" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_3")
            elif "বিবাহিত" in Input or "বিয়ে" in Input or "অবিবাহিত" in Input or "আনমেরিড" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_4")
            elif "দিনটা কেমন" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_5")
            elif "কি বুদ্ধিমান" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_6")
            elif "প্রিয় পিকআপ লাইন" in Input or "পিকআপ লাইন" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_7")
            elif "কখনো প্রেমে পরেছ" in Input or "প্রেমে পরেছ" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_8")
            elif "আজকে জন্মদিন" in Input or "জন্মদিন" in Input or "বার্থডে" in Input or "জন্মদিন আজকে" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_9")
            elif "এলিয়েন" in Input or "এলিয়েন কি সত্যি" in Input or "মহাজাগতিক প্রানী" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_10")
            elif "সিরি" in Input or "সিরি কে" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_Siri")
            elif "করটানা" in Input or "কর্টানা" in Input or "করটানা কে" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_Cortana")
            elif "আলেক্সা" in Input or "এলেক্সা কে" in Input or "আলেক্সা কে" in Input or "এলেক্সা" in Input:
                dispatcher.utter_message(response="utter_Out_of_scope_funny_Alexa")
            else:
                dispatcher.utter_message(response="utter_out_of_scope")
        else:
            dispatcher.utter_message(response="utter_default")
        
        return []

class CreditCardLimitInformation(Action):
    """Action_Card_limit_info"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "Action_Card_limit_info"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        global UserText
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        """Executes the action"""
        print(f"User Input was:{UserText}")
        print(type(UserText))
        if "লিমিট" in UserText:
            dispatcher.utter_message(response="utter_card_limit")
            return [
                    SlotSet("PIN", None),
                    SlotSet("Incomplete_Story", False),
                    SlotSet("requested_slot", None),
                    Form(None),
                    ]
        elif "কার্ড ব্যালেন্স" in UserText or "ব্যালেন্স" in UserText or "এভেইলেবল এমাউন্ট" in UserText:
            dispatcher.utter_message(response="utter_card_balance")
            return [
                    SlotSet("PIN", None),
                    SlotSet("Incomplete_Story", False),
                    SlotSet("requested_slot", None),
                    Form(None),
                    ]
        elif "আউটস্টেন্ডং" in UserText or "খরচ" in UserText or "ডিউ" in UserText or "বিল" in UserText:
            dispatcher.utter_message(response="utter_card_outstanding")
            return [
                    SlotSet("PIN", None),
                    SlotSet("Incomplete_Story", False),
                    SlotSet("requested_slot", None),
                    Form(None),
                    ]
        else:
            dispatcher.utter_message(response="utter_card_info")
            return [
                    SlotSet("PIN", None),
                    SlotSet("Incomplete_Story", False),
                    SlotSet("requested_slot", None),
                    Form(None),
                    ]

class actionDateTime(Action):
    """Action_Current_DateTime"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "Action_Current_DateTime"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        text = tracker.latest_message.get('text')
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        """Executes the action"""
        print(f"User Input was:{text}")
        months = ["জানুয়ারি", "ফেব্রুয়ারী", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগষ্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
        today = date.today()
        now = datetime.datetime.now()
        DATE = today.strftime("%B %d, %Y")
        print("DATE =", DATE)
        year = today.strftime("%Y")
        Y = bangla.convert_english_digit_to_bangla_digit(str(year))
        Y = num_convert.number_to_bangla_words(Y)
        print(Y)
        month = today.strftime("%m")
        month = int(month) - 1
        print("before loop month: ", month)
        Mon = months[month]
        print(Mon)
        day = today.strftime("%d")
        D = bangla.convert_english_digit_to_bangla_digit(str(day))
        D = num_convert.number_to_bangla_words(D)
        print(D)
        print(f"Year: {year}, month: {month}, day: {day}")
        time = now.strftime("%H:%M:%S")
        print("time =", time)

        hour = now.strftime("%H")
        minutes = now.strftime("%M")

        print (f"hour: {hour} and minute: {minutes}")
        if(int(hour)>12):
            hour=str(int(hour) - 12)
        H = bangla.convert_english_digit_to_bangla_digit(str(hour))
        hour = num_convert.number_to_bangla_words(H)
        M = bangla.convert_english_digit_to_bangla_digit(str(minutes))
        Minutes = num_convert.number_to_bangla_words(M)
        
        

        d_msg = f"আজকের তারিখ হচ্ছে, {D}, {Mon}, {Y} ।"
        msg = f"এখন সময়, {hour} টা বেজে {Minutes} মিনিট।"
        message = f"এখন সময়, {hour} টা বেজে {Minutes} মিনিট। আজকের তারিখ হচ্ছে, {D}, {Mon}, {Y} ।"
        dispatcher.utter_message(text = message)

        if "তারিখ" in text:
            pass
            # dispatcher.utter_message(text = d_msg)
        if "সময়" in text:
            pass
            # dispatcher.utter_message(response="utter_card_balance")
        # else:
        #     dispatcher.utter_message(response="utter_card_info")
        
        return []

# class ActionChequeNumber(FormValidationAction):
#     """validate_cheque_form"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "validate_cheque_form"

    # async def validate_cheque_number(
    #     self,
    #     slot_value: Any,
    #     dispatcher: CollectingDispatcher,
    #     tracker: Tracker,
    #     domain: Dict[Text, Any],
    # ) -> List[Dict]:
    
    #     """Executes the action"""
    #     print(tracker.latest_message['intent'].get('name'))
    #     print(tracker.latest_message['intent']['confidence'])
    #     active_loop = tracker.active_loop.get('name')
    #     print(f"active loop is, {active_loop}")
    #     SLT = tracker.slots.get('name')
    #     print(f"the rasa is requesting for {SLT}")
        
    #     print("validate_cheque_number")
    #     cheque = tracker.get_slot("cheque_number")
    #     print("cheque Number is : ", cheque)
        
    #     #BANGLA Check Here
    #     if (not is_ascii(cheque)):  #If Bangla then enter here. is_ascii(otp) True for English
    #         cn = None
    #         if cheque.isnumeric():
    #             cn = BnToEn(cheque)
    #             print(str(cn))
    #             cheque = str(cn)
    #             print("cheque Number is ", cheque)
    #             tracker.slots["cheque_number"] = cheque
    #             if len(cheque)!=6 or cheque == None:
    #                 dispatcher.utter_message(response="utter_invalidCHEQUEnumber")
    #                 # return {"cheque_number": None}
    #                 return [
    #                         SlotSet("cheque_number", None),
    #                         SlotSet("Incomplete_Story", True),
    #                         ]
    #             else:
    #                 print("Correct cheque Number")
    #                 # account = db_manager.set_slot_value(tracker.sender_id, "cheque_number", cheque)
    #                 return [
    #                         SlotSet("cheque_number", cheque),
    #                         SlotSet("Incomplete_Story", True),
    #                         FollowupAction('action_tell_ChequeNumber'),
    #                         ]
    #     else:
    #         if len(cheque)!=6 or cheque == None:
    #             dispatcher.utter_message(response="utter_invalidCHEQUEnumber")
    #             return [
    #                     SlotSet("cheque_number", None),
    #                     SlotSet("Incomplete_Story", True),
    #                     ]
    #         else:
    #             print("Correct cheque Number")
    #             # account = db_manager.set_slot_value(tracker.sender_id, "cheque_number", cheque)
    #             # return [SlotSet("cheque_number", cheque), FollowupAction('action_tell_ChequeNumber')]
    #             return [
    #                     SlotSet("cheque_number", cheque),
    #                     SlotSet("Incomplete_Story", True),
    #                     FollowupAction('action_tell_ChequeNumber'),
    #                     ]

# class ActionTellChequeNumber(Action):

#     def name(self) -> Text:
#         return "action_tell_ChequeNumber"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         tell_ACNumber = next(tracker.get_latest_entity_values("cheque_number"), None)
        
#         number=['জিরো','ওয়ান','টু','থ্রি','ফোর','ফাইভ','সিক্স','সেভেন','এইট','নাইন']
#         if(tell_ACNumber!=None):
#             wr=''
#             for c in tell_ACNumber:
#                 wr=wr+' '+number[int(c)]

#         wr2 = wr.split(" ")
#         for i in range(len(wr2)):
#             wr2[i] = wr2[i]+","
#         wr = ' '.join(wr2)
#         if not tell_ACNumber:
#             msg = f"দুঃখিত, আপনার কথাটি বুঝতে পারিনি ।"
#             dispatcher.utter_message(text=msg)
#             return []

#         msg = f"আপনি বলেছেন, {wr} । সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।"
#         print('আপনি বলেছেন,', {wr}, '। সেটা ঠিক হলে বলুন, হ্যা ঠিক আছে ।')
#         dispatcher.utter_message(text=msg)
#         return []

class BankLocation(Action):
    """action_bank_location"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_bank_location"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        """Executes the action"""
        location_name = tracker.get_slot("location")
        if location_name == None:
            dispatcher.utter_message(response = "utter_bank_location")
            return []
        else:
            if location_name == "মিরপুর":
                dispatcher.utter_message(response = "utter_bank_location_mirpur")
                return []
            elif location_name == "গুলশান":
                dispatcher.utter_message(response = "utter_bank_location_gulshan")
                return []
            else:
                dispatcher.utter_message(response = "utter_bank_location")
                return []

class ResetChequeANDamount(Action):
    """action_reset_ChequeANDamount"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_reset_ChequeANDamount"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        print(tracker.latest_message['intent'].get('name'))
        """Executes the action"""
        print("Reset Cheque number and amount-of-money Function Called.")
        currentloop = tracker.active_loop.get('name')
        print(f"Loop name: {currentloop}")

        story_status = tracker.get_slot("Incomplete_Story")
        print(f"Story Incomplete: {story_status}")

        if story_status == True or currentloop != None:
            # dispatcher.utter_message(response="utter_ask_continue_form")
            # return [UserUtteranceReverted()]
            return []
        # if story_status == True:
        #     # return [Form(None), SlotSet("requested_slot", None)]
        #     return [UserUtteranceReverted()]
        return[
                SlotSet("cheque_number", None),
                SlotSet("amount-of-money", None),
                SlotSet("Incomplete_Story", True),
                SlotSet("cheque_number_confirm", None),
                SlotSet("amount_confirm", None),
                SlotSet("ChequeNumberWord", None),
            ]

class E_Commerce_Request(Action):
    """action_E_Commerce_Request"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_E_Commerce_Request"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        print(tracker.latest_message['intent'].get('name'))
        """Executes the action"""

        story_status = tracker.get_slot("Incomplete_Story")
        print(f"Story Incomplete: {story_status}")

        if story_status == True:
            return [UserUtteranceReverted()]

        # dispatcher.utter_message(response="utter_E_Commerce_Request")
        return[
            SlotSet("Father_Name", None),
            SlotSet("Mother_Name", None),
            SlotSet("Birth_Date", None),
            SlotSet("Incomplete_Story", True),
        ]

class ActionCard_Close(Action):
    """action_Card_Close"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_Card_Close"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        print(tracker.latest_message['intent'].get('name'))
        """Executes the action"""
        # dispatcher.utter_message(response="utter_Card_Close")
        currentloop = tracker.active_loop.get('name')
        print(f"Loop name: {currentloop}")

        story_status = tracker.get_slot("Incomplete_Story")
        print(f"Story Incomplete: {story_status}")

        if story_status == True or currentloop != None:
            # dispatcher.utter_message(response="utter_ask_continue_form")
            return [ActionExecuted("action_listen")]
        else:
            return[
                    SlotSet("card_number_confirm", None),
                    SlotSet("Father_Name", None),
                    SlotSet("Mother_Name", None),
                    SlotSet("Birth_Date", None),
                    SlotSet("Incomplete_Story", True),
                    SlotSet("NumberInWord", None),
                    SlotSet("amountBengaliWord", None),
                    SlotSet("CardText", None),
                    ]

# class ActionGetParentsName(FormValidationAction):
#     """validate_get_parents_name_form"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "validate_get_parents_name_form"

#     async def validate_Father_Name(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
    
#         """Executes the action"""
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         active_loop = tracker.active_loop.get('name')
#         print(f"active loop is, {active_loop}")
#         SLT = tracker.slots.get('name')
#         print(f"the rasa is requesting for {SLT}")
        
#         print("validate_Father_Name")
#         Name = tracker.get_slot("Father_Name")
#         print("Name is in validate form and it is ", Name)

#         #NAME can't be a number
#         for character in Name:
#             if character.isdigit():
#                 dispatcher.utter_message(response="utter_invalidNAME")
#                 return [
#                         SlotSet("Father_Name", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#         if Name!=None:
#             if (len(Name) < 4):
#                 dispatcher.utter_message(response="utter_invalidNAME")
#                 # return {"Father_Name": None}
#                 return [
#                         SlotSet("Father_Name", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#             else:
#                 return [
#                         SlotSet("Father_Name", Name),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#         else:
#             dispatcher.utter_message(response="utter_invalidNAME")
#             # return {"Father_Name": None}
#             return [
#                     SlotSet("Father_Name", None),
#                     SlotSet("Incomplete_Story", True),
#                     ]
#     async def validate_Mother_Name(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
    
#         """Executes the action"""
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         active_loop = tracker.active_loop.get('name')
#         print(f"active loop is, {active_loop}")
#         SLT = tracker.slots.get('name')
#         print(f"the rasa is requesting for {SLT}")
        
#         print("validate_Mother_Name")
#         Name = tracker.get_slot("Mother_Name")
#         print("Name is in validate form and it is ",Name)

#         #USERNAME can't be a number
#         for character in Name:
#             if character.isdigit():
#                 dispatcher.utter_message(response="utter_invalidNAME")
#                 return [
#                         SlotSet("Mother_Name", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#         if Name!=None:
#             if (len(Name) < 4):
#                 dispatcher.utter_message(response="utter_invalidNAME")
#                 # return {"Mother_Name": None}
#                 return [
#                         SlotSet("Mother_Name", None),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#             else:
#                 return [
#                         SlotSet("Mother_Name", Name),
#                         SlotSet("Incomplete_Story", True),
#                         ]
#         else:
#             dispatcher.utter_message(response="utter_invalidNAME")
#             # return {"Mother_Name": None}
#             return [
#                     SlotSet("Mother_Name", None),
#                     SlotSet("Incomplete_Story", True),
#                     ]

# class ActionGetBirthDate(FormValidationAction):
#     """validate_Birthdate_form"""

#     def name(self) -> Text:
#         """Unique identifier of the action"""
#         return "validate_Birthdate_form"

#     async def validate_Birth_Date(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict]:
    
#         """Executes the action"""
#         print(tracker.latest_message['intent'].get('name'))
#         print(tracker.latest_message['intent']['confidence'])
#         active_loop = tracker.active_loop.get('name')
#         print(f"active loop is, {active_loop}")
#         SLT = tracker.slots.get('name')
#         print(f"the rasa is requesting for {SLT}")
        
#         print("validate_Birth_Date")
#         Bdate = tracker.get_slot("Birth_Date")
#         print("Name is in validate form and it is ", Bdate)

#         if Bdate!=None:
#             return [
#                     SlotSet("Birth_Date", Bdate),
#                     SlotSet("Incomplete_Story", True),
#                     ]
#         else:
#             dispatcher.utter_message(response="utter_invalidBDATE")
#             # return {"Birth_Date": None}
#             return [
#                     SlotSet("Birth_Date", True),
#                     SlotSet("Incomplete_Story", True),
#                     ]

class ActionCardActivation(Action):
    """action_card_activation"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_card_activation"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        dispatcher.utter_message(response="utter_card_activation")

        return [
                SlotSet("Incomplete_Story", False),
                SlotSet("NumberInWord", None),
                SlotSet("card_number_confirm", None),
                ]

class ActionOKey(Action):
    """action_OK"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_OK"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        dispatcher.utter_message(response="utter_E_Commerce_Request")
        return [SlotSet("Incomplete_Story", False), Form(None), SlotSet("requested_slot", None)]
    
class ActionCloseCard(Action):
    """action_card_close_done"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_card_close_done"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        dispatcher.utter_message(response="utter_card_close_done")
        # return [
        #         SlotSet("Incomplete_Story", False),
        #         SlotSet("NumberInWord", None),
        #         SlotSet("amountBengaliWord", None),
        #         Form(None),
        #         SlotSet("requested_slot", None),
        #         ]
        return [
                SlotSet("Incomplete_Story", False),
                SlotSet("NumberInWord", None),
                SlotSet("amountBengaliWord", None),
                ]

class ActionGreet(Action):
    """action_greet"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_greet"
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        currentTime = datetime.datetime.now()
        currentTime.hour

        if 3<= currentTime.hour < 12:
           print('Good morning.')
           dispatcher.utter_message(response="utter_greet_morning")
        elif 12 <= currentTime.hour < 17:
            print('Good afternoon.')
            dispatcher.utter_message(response="utter_greet_afternoon")
        elif 17 <= currentTime.hour < 19:
            print('Good evening.')
            dispatcher.utter_message(response="utter_greet_evening")
        elif 19 <= currentTime.hour < 3:
            print('Good night.')
            dispatcher.utter_message(response="utter_greet_night")
        else:
            print('Good unknown time.')
            dispatcher.utter_message(response="utter_greet")

        return [SlotSet("Incomplete_Story", False)]


class ActionValidationbKash(FormValidationAction):
    """validate_bKash_form"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "validate_bKash_form"

    async def validate_account_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        
        print("validate_account_number")
        ac = tracker.get_slot("account_number")
        print("AC Number is : ", ac)
        
        #BANGLA Check Here
        if (not is_ascii(ac)):  #If Bangla then enter here. is_ascii(otp) True for English
            cn = None
            if ac.isnumeric():
                cn = BnToEn(ac)
                print(str(cn))
                ac = str(cn)
                print("account Number is ", ac)
                tracker.slots["account_number"] = ac
                if len(ac)!=8 or ac == None:
                    dispatcher.utter_message(response="utter_invalidACNumber")
                    return {"account_number": None}
                else:
                    print("Correct account Number")
                    # account = db_manager.set_slot_value(tracker.sender_id, "account_number", ac)
                    ACINword = numberTranslate(ac)
                    print(f"AC Number in Bangla: {ACINword}")
                    return {"account_number": ac, "ACtext": ACINword, "requested_slot": "account_number_confirm"}
                    # return [
                    #         SlotSet("account_number", ac),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
        else:
            if len(ac)!=8 or ac == None:
                dispatcher.utter_message(response="utter_invalidACNumber")
                return {"account_number": None, "requested_slot": "account_number"}

            else:
                print("Correct account Number")
                ACINword = numberTranslate(ac)
                print(f"AC Number in Bangla: {ACINword}")
                return {"account_number": ac, "ACtext": ACINword, "requested_slot": "account_number_confirm"}

    
    async def validate_account_number_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return{"account_number_confirm": "affirm", "ACtext": None, "account_check": False}
            # return [
            #         SlotSet("account_number_confirm", "affirm"),
            #         SlotSet("Incomplete_Story", True),
            #         SlotSet("ACtext", None),
            #         ]
        elif intent == "deny":
            print("account number is not correct.")
            return {"account_number_confirm": None, "account_number": None, "ACtext": None, "requested_slot": "account_number"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"account_number_confirm": None, "requested_slot": "account_number_confirm"}

    
    async def validate_phone_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        
        print("validate_phone_number")
        phone = tracker.get_slot("phone_number")
        print("phone Number is : ", phone)
        
        #BANGLA Check Here
        if (not is_ascii(phone)):  #If Bangla then enter here. is_ascii(otp) True for English
            cn = None
            if phone.isnumeric():
                cn = BnToEn(phone)
                print(str(cn))
                phone = str(cn)
                print("phone Number is ", phone)
                tracker.slots["phone_number"] = phone
                if len(phone)!=11 or phone == None:
                    dispatcher.utter_message(response="utter_invalidphone")
                    return {"phone_number": None, "requested_slot":"phone_number"}
                else:
                    print("Correct phone Number")
                    # account = db_manager.set_slot_value(tracker.sender_id, "phone_number", phone)
                    PhoneINword = numberTranslate(phone)
                    print(f"Phone Number in Bangla: {PhoneINword}")
                    return {"phone_number": phone, "PhoneText": PhoneINword, "requested_slot": "phone_number_confirm"}
                    # return [
                    #         SlotSet("phone_number", phone),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
        else:
            if len(phone)!=11 or phone == None:
                dispatcher.utter_message(response="utter_invalidphone")
                return {"phone_number": None, "requested_slot":"phone_number"}
            else:
                print("Correct phone Number")
                PhoneINword = numberTranslate(phone)
                print(f"Phone Number in Bangla: {PhoneINword}")
                return {"phone_number": phone, "PhoneText": PhoneINword, "requested_slot": "phone_number_confirm"}
    
    async def validate_phone_number_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return {"phone_number_confirm": "affirm", "PhoneText": None}
            # return [
            #         SlotSet("phone_number_confirm", "affirm"),
            #         SlotSet("Incomplete_Story", True),
            #         SlotSet("PhoneText", None)
            #         ]
        elif intent == "deny":
            print("phone number is not correct.")
            return {"phone_number_confirm": None, "phone_number": None, "PhoneText": None, "requested_slot": "phone_number"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"phone_number_confirm": None, "requested_slot": "phone_number_confirm"}

    async def validate_amount_of_money(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        amount = tracker.get_slot("amount-of-money")
        print("amount inside function: ", amount)

        account_balance = profile_db.get_account_balance(tracker.sender_id)

        number = None
        #BANGLA Check Here
        if(not is_ascii(amount)):  #If Bangla then enter here
            print("Hello, Check Bangla")
            if amount.isnumeric():
                number = BnToEn(amount)
                amount = str(number)
                print("Number : ", number)
                print(amount)
                if(int(amount)<=0):
                    dispatcher.utter_message(response="utter_invalidAMOUNT")
                    # print("1")
                    return {"amount-of-money": None}
                    # return[
                    #         SlotSet("amount-of-money", None),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
                else:
                    # print("2")
                    # account = db_manager.set_slot_value(tracker.sender_id, 'amount-of-money', amount)
                    amountBengaliWord = amount_in_word(amount)
                    print(f"amount is {amountBengaliWord}")
                    return {"amount-of-money": amount, "amountBengaliWord": amountBengaliWord, "requested_slot": "amount_confirm"}
                    # return[
                    #         SlotSet("amount-of-money", None),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
            else:
                # print("3")
                return {"amount-of-money": None}
                # return[ SlotSet("amount-of-money", None),
                #         SlotSet("Incomplete_Story", True),
                #         ]
        else:
            # print("4")
            if(int(amount)<=0):
                # print("5")
                dispatcher.utter_message(response="utter_invalidAMOUNT")
                return {"amount-of-money": None, "requested_slot": "amount-of-money"}
                # return[
                #         SlotSet("amount-of-money", None),
                #         SlotSet("Incomplete_Story", True),
                #         ]
            else:
                # account = db_manager.set_slot_value(tracker.sender_id, 'amount-of-money', amount)
                print("Amount is ", amount)
                amountBengaliWord = amount_in_word(amount)
                print(f"amount is {amountBengaliWord}")
                return {"amount-of-money": amount, "amountBengaliWord": amountBengaliWord, "requested_slot": "amount_confirm"}
                # return[
                #         SlotSet("amount-of-money", amount),
                #         SlotSet("amountBengaliWord", amountBengaliWord),
                #         ]
    
    async def validate_amount_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""

        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return{"amount_confirm": "affirm", "amountBengaliWord": None}
            # return [
            #         SlotSet("amount_confirm", "affirm"),
            #         SlotSet("Incomplete_Story", True),
            #         SlotSet("amountBengaliWord", None),
            #         ]
        elif intent == "deny":
            print("amount is not correct.")
            return {"amount_confirm": None, "amount-of-money": None, "amountBengaliWord": None, "requested_slot": "amount-of-money"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"amount_confirm": None, "requested_slot": "amount_confirm"}

class Actiontransfer(Action):
    """action_utter_transfer"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_utter_transfer"
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        dispatcher.utter_message(response="utter_transfer")

        return [
                SlotSet("Incomplete_Story", False),
                SlotSet("account_number_confirm", None),
                SlotSet("phone_number_confirm", None),
                SlotSet("amount_confirm", None),
                SlotSet("NumberInWord", None),
                SlotSet("amountBengaliWord", None),
                ]

class ActionContinue(Action):
    """action_ask_continue"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_ask_continue"
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        intent = tracker.latest_message['intent'].get('name')

        currentloop = tracker.active_loop.get('name')
        print(f"Loop name: {currentloop}")

        story_status = tracker.get_slot("Incomplete_Story")
        print(f"Story Incomplete: {story_status}")

        if intent == "inform":
            if currentloop != None:
                print('here')
                if(currentloop in FORM_SLOT_UTTER):
                    dispatcher.utter_message(response=FORM_SLOT_UTTER[currentloop])
                return [UserUtteranceReverted()]


        if story_status == True or currentloop != None:
            if intent == "explain":
                dispatcher.utter_message(response="utter_explain_and_continue")
                return [SlotSet("Continue", True)]
            dispatcher.utter_message(response="utter_ask_continue_form")
            return [SlotSet("Continue", True)]
        else:
            intent = tracker.latest_message['intent'].get('name')
            return [SlotSet("Continue", False)]

class ActionContinueResponse(Action):
    """action_continue_response"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_continue_response"
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        intent = tracker.latest_message['intent'].get('name')
        currentloop = tracker.active_loop.get('name')
        print(f"Loop name: {currentloop}")
        print(type(currentloop))
        if intent == "affirm":
            return [SlotSet("Continue", False), FollowupAction(currentloop)]
        elif intent == "deny":
            dispatcher.utter_message(response = "utter_ask_whatelse")
            return [Form(None), SlotSet("requested_slot", None), SlotSet("Incomplete_Story", False), SlotSet("Continue", False)]
        else:
            # return [ActionReverted()]
            return [SlotSet("Continue", False), UserUtteranceReverted()]

class ActionValidationCardActivation(FormValidationAction):
    """validate_Card_Activation_form"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "validate_Card_Activation_form"

    async def validate_card_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        
        
        print("validate card number")
        card = tracker.get_slot("card_number")
        print("card Number is : ", card)
        
        
        #BANGLA Check Here
        if (not is_ascii(card)):  #If Bangla then enter here. is_ascii(otp) True for English
            cn = None
            if card.isnumeric():
                cn = BnToEn(card)
                print(str(cn))
                card = str(cn)
                print("card Number is ", card)
                tracker.slots["card_number"] = card
                if len(card)!=10 or card == None:
                    dispatcher.utter_message(response="utter_invalidCARDnumber")
                    return {"card_number": None}
                    # return [
                    #         SlotSet("card_number", None),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
                else:
                    print("Correct card Number")
                    CardINword = numberTranslate(card)
                    print(f"card Number in Bangla: {CardINword}")
                    return {"card_number": card, "CardText": CardINword, "requested_slot": "card_number_confirm"}
        else:
            if len(card)!=10 or card == None:
                dispatcher.utter_message(response="utter_invalidCARDnumber")
                return {"card_number": None, "requested_slot": "card_number"}
            else:
                print("Correct card Number")
                # account = db_manager.set_slot_value(tracker.sender_id, "card_number", card)
                CardINword = numberTranslate(card)
                print(f"card Number in Bangla: {CardINword}")
                return {"card_number": card, "CardText": CardINword, "requested_slot": "card_number_confirm"}

    
    async def validate_card_number_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return {"card_number_confirm": "affirm", "CardText": None, "card_check": False}
            # return [
            #         SlotSet("card_number_confirm", "affirm"),
            #         SlotSet("Incomplete_Story", True),
            #         SlotSet("CardText", None),
            #         ]
        elif intent == "deny":
            print("account number is not correct.")
            return {"card_number_confirm": None, "card_number": None, "CardText": None, "requested_slot": "card_number"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"card_number_confirm": None, "requested_slot": "card_number_confirm"}
    
    async def validate_Father_Name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        print(f"active loop is, {active_loop}")
        SLT = tracker.slots.get('name')
        print(f"the rasa is requesting for {SLT}")
        
        print("validate_Father_Name")
        Name = tracker.get_slot("Father_Name")
        print("Name is in validate form and it is ", Name)

        #NAME can't be a number
        for character in Name:
            if character.isdigit():
                dispatcher.utter_message(response="utter_invalidNAME")
                return {"Father_Name": None}
                # return [
                #         SlotSet("Father_Name", None),
                #         SlotSet("Incomplete_Story", True),
                #         ]
        if Name!=None:
            if (len(Name) < 4):
                dispatcher.utter_message(response="utter_invalidNAME")
                return {"Father_Name": None, "requested_slot":"Father_Name"}
            else:
                print("Correct Name")
                return {"Father_Name": Name}
        else:
            dispatcher.utter_message(response="utter_invalidNAME")
            return {"Father_Name": None, "requested_slot":"Father_Name"}
        
    async def validate_Mother_Name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        print(f"active loop is, {active_loop}")
        SLT = tracker.slots.get('name')
        print(f"the rasa is requesting for {SLT}")
        
        print("validate_Mother_Name")
        Name = tracker.get_slot("Mother_Name")
        print("Name is in validate form and it is ",Name)

        #USERNAME can't be a number
        for character in Name:
            if character.isdigit():
                dispatcher.utter_message(response="utter_invalidNAME")
                return {"Mother_Name": None, "requested_slot":"Mother_Name"}
        if Name!=None:
            if (len(Name) < 4):
                dispatcher.utter_message(response="utter_invalidNAME")
                # return {"Mother_Name": None}
                return {"Mother_Name": None, "requested_slot":"Mother_Name"}
            else:
                return {"Mother_Name": Name}
        else:
            dispatcher.utter_message(response="utter_invalidNAME")
            return {"Mother_Name": None, "requested_slot":"Mother_Name"}

    async def validate_Birth_Date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        print(f"active loop is, {active_loop}")
        SLT = tracker.slots.get('name')
        print(f"the rasa is requesting for {SLT}")
        
        print("validate_Birth_Date")
        Bdate = tracker.get_slot("Birth_Date")
        print("Name is in validate form and it is ", Bdate)

        newDate = Bdate.split("/")
        day = newDate[0]
        month = newDate[1]
        year = newDate[2]

        print(type(day))

        print(newDate)
        print(f"Day: {day}, month: {month}, year: {year}")
        month = int(month)
        if Bdate!=None:
            if month in range(1, 13):
                return {"Birth_Date": Bdate}
            else:
                dispatcher.utter_message(response="utter_invalidBDATE")
                return {"Birth_Date": None}
        else:
            dispatcher.utter_message(response="utter_invalidBDATE")
            return {"Birth_Date": None}

class ActionValidationCardDeactivation(FormValidationAction):
    """validate_Card_DeActivation_form"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "validate_Card_DeActivation_form"

    async def validate_card_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        
        
        print("validate card number")
        card = tracker.get_slot("card_number")
        print("card Number is : ", card)
        
        
        #BANGLA Check Here
        if (not is_ascii(card)):  #If Bangla then enter here. is_ascii(otp) True for English
            cn = None
            if card.isnumeric():
                cn = BnToEn(card)
                print(str(cn))
                card = str(cn)
                print("card Number is ", card)
                tracker.slots["card_number"] = card
                if len(card)!=10 or card == None:
                    dispatcher.utter_message(response="utter_invalidCARDnumber")
                    return {"card_number": None}
                    # return [
                    #         SlotSet("card_number", None),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
                else:
                    print("Correct card Number")
                    # account = db_manager.set_slot_value(tracker.sender_id, "card_number", card)
                    CardINword = numberTranslate(card)
                    print(f"card Number in Bangla: {CardINword}")
                    return {"card_number": card, "CardText": CardINword, "requested_slot": "card_number_confirm"}
        else:
            if len(card)!=10 or card == None:
                dispatcher.utter_message(response="utter_invalidCARDnumber")
                return {"card_number": None, "requested_slot": "card_number"}
            else:
                print("Correct card Number")
                # account = db_manager.set_slot_value(tracker.sender_id, "card_number", card)
                CardINword = numberTranslate(card)
                print(f"card Number in Bangla: {CardINword}")
                return {"card_number": card, "CardText": CardINword, "requested_slot": "card_number_confirm"}

    
    async def validate_card_number_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return{"card_number_confirm": "affirm", "CardText": None, "card_check": False}
            # return [
            #         SlotSet("card_number_confirm", "affirm"),
            #         SlotSet("Incomplete_Story", True),
            #         SlotSet("CardText", None),
            #         ]
        elif intent == "deny":
            print("account number is not correct.")
            return {"card_number_confirm": None, "card_number": None, "CardText": None, "requested_slot": "card_number"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"card_number_confirm": None, "requested_slot": "card_number_confirm"}
    
    async def validate_Father_Name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        print(f"active loop is, {active_loop}")
        SLT = tracker.slots.get('name')
        print(f"the rasa is requesting for {SLT}")
        
        print("validate_Father_Name")
        Name = tracker.get_slot("Father_Name")
        print("Name is in validate form and it is ", Name)

        #NAME can't be a number
        for character in Name:
            if character.isdigit():
                dispatcher.utter_message(response="utter_invalidNAME")
                return {"Father_Name": None}
                # return [
                #         SlotSet("Father_Name", None),
                #         SlotSet("Incomplete_Story", True),
                #         ]
        if Name!=None:
            if (len(Name) < 4):
                dispatcher.utter_message(response="utter_invalidNAME")
                return {"Father_Name": None, "requested_slot":"Father_Name"}
            else:
                print("Correct Name")
                return {"Father_Name": Name}
        else:
            dispatcher.utter_message(response="utter_invalidNAME")
            return {"Father_Name": None, "requested_slot":"Father_Name"}
        
    async def validate_Mother_Name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        print(f"active loop is, {active_loop}")
        SLT = tracker.slots.get('name')
        print(f"the rasa is requesting for {SLT}")
        
        print("validate_Mother_Name")
        Name = tracker.get_slot("Mother_Name")
        print("Name is in validate form and it is ",Name)

        #USERNAME can't be a number
        for character in Name:
            if character.isdigit():
                dispatcher.utter_message(response="utter_invalidNAME")
                return {"Mother_Name": None, "requested_slot":"Mother_Name"}
        if Name!=None:
            if (len(Name) < 4):
                dispatcher.utter_message(response="utter_invalidNAME")
                # return {"Mother_Name": None}
                return {"Mother_Name": None, "requested_slot":"Mother_Name"}
            else:
                return {"Mother_Name": Name}
        else:
            dispatcher.utter_message(response="utter_invalidNAME")
            return {"Mother_Name": None, "requested_slot":"Mother_Name"}

    async def validate_Birth_Date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        print(f"active loop is, {active_loop}")
        SLT = tracker.slots.get('name')
        print(f"the rasa is requesting for {SLT}")
        
        print("validate_Birth_Date")
        Bdate = tracker.get_slot("Birth_Date")
        print("Name is in validate form and it is ", Bdate)

        newDate = Bdate.split("/")
        day = newDate[0]
        month = newDate[1]
        year = newDate[2]

        print(type(day))

        print(newDate)
        print(f"Day: {day}, month: {month}, year: {year}")
        month = int(month)
        if Bdate!=None:
            if month in range(1, 13):
                return {"Birth_Date": Bdate}
            else:
                dispatcher.utter_message(response="utter_invalidBDATE")
                return {"Birth_Date": None}
        else:
            dispatcher.utter_message(response="utter_invalidBDATE")
            return {"Birth_Date": None}

class ActionValidationCardLimit(FormValidationAction):
    """validate_Credit_card_limit_form"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "validate_Credit_card_limit_form"

    async def validate_card_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        
        
        print("validate card number")
        card = tracker.get_slot("card_number")
        print("card Number is : ", card)
        
        
        #BANGLA Check Here
        if (not is_ascii(card)):  #If Bangla then enter here. is_ascii(otp) True for English
            cn = None
            if card.isnumeric():
                cn = BnToEn(card)
                print(str(cn))
                card = str(cn)
                print("card Number is ", card)
                tracker.slots["card_number"] = card
                if len(card)!=10 or card == None:
                    dispatcher.utter_message(response="utter_invalidCARDnumber")
                    return {"card_number": None}
                    # return [
                    #         SlotSet("card_number", None),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
                else:
                    print("Correct card Number")
                    # account = db_manager.set_slot_value(tracker.sender_id, "card_number", card)
                    CardINword = numberTranslate(card)
                    print(f"card Number in Bangla: {CardINword}")
                    return {"card_number": card, "CardText": CardINword, "requested_slot": "card_number_confirm"}
        else:
            if len(card)!=10 or card == None:
                dispatcher.utter_message(response="utter_invalidCARDnumber")
                return {"card_number": None, "requested_slot": "card_number"}
            else:
                print("Correct card Number")
                # account = db_manager.set_slot_value(tracker.sender_id, "card_number", card)
                CardINword = numberTranslate(card)
                print(f"card Number in Bangla: {CardINword}")
                return {"card_number": card, "CardText": CardINword, "requested_slot": "card_number_confirm"}

    
    async def validate_card_number_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return{"card_number_confirm": "affirm", "CardText": None, "card_check": False}
        elif intent == "deny":
            print("account number is not correct.")
            return {"card_number_confirm": None, "card_number": None, "CardText": None, "requested_slot": "card_number"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"card_number_confirm": None, "requested_slot": "card_number_confirm"}
    
    async def validate_PIN(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        
        print("validate_PIN")
        pin = tracker.get_slot("PIN")
        print("PIN Number is : ", pin)
        
        #BANGLA Check Here
        if (not is_ascii(pin)):  #If Bangla then enter here. is_ascii(otp) True for English
            cn = None
            if pin.isnumeric():
                cn = BnToEn(pin)
                print(str(cn))
                pin = str(cn)
                print("pin Number is ", pin)
                tracker.slots["PIN"] = pin
                if len(pin)!=4 or pin == None:
                    dispatcher.utter_message(response="utter_invalidPIN")
                    return{"PIN": None, "requested_slot":"PIN"}
                    # return [
                    #         SlotSet("PIN", None),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
                else:
                    print("Correct pin Number")
                    # account = db_manager.set_slot_value(tracker.sender_id, "PIN", pin)
                    pinINword = numberTranslate(pin)
                    print(f"card Number in Bangla: {pinINword}")
                    return {"PIN": pin, "PIN_Text": pinINword, "requested_slot":"PIN_confirm"}
                    # return [
                    #         SlotSet("PIN", pin),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
        else:
            if len(pin)!=4 or pin == None:
                dispatcher.utter_message(response="utter_invalidPIN")
                return{"PIN": None, "requested_slot":"PIN"}
                # return [
                #         SlotSet("PIN", None),
                #         SlotSet("Incomplete_Story", True),
                #         ]
            else:
                print("Correct pin Number")
                # account = db_manager.set_slot_value(tracker.sender_id, "PIN", pin)
                pinINword = numberTranslate(pin)
                print(f"card Number in Bangla: {pinINword}")
                return {"PIN": pin, "PIN_Text": pinINword, "requested_slot":"PIN_confirm"}

    async def validate_PIN_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return{"PIN_confirm": "affirm", "PIN_Text": None}
        elif intent == "deny":
            print("pin is not correct.")
            return {"PIN_confirm": None, "PIN": None, "PIN_Text": None, "requested_slot": "PIN"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"PIN_confirm": None, "requested_slot": "PIN_confirm"}

class ActionValidationCheckBalance(FormValidationAction):
    """validate_check_balance_form"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "validate_check_balance_form"

    async def validate_account_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        
        print("validate_account_number")
        ac = tracker.get_slot("account_number")
        print("AC Number is : ", ac)
        
        #BANGLA Check Here
        if (not is_ascii(ac)):  #If Bangla then enter here. is_ascii(otp) True for English
            cn = None
            if ac.isnumeric():
                cn = BnToEn(ac)
                print(str(cn))
                ac = str(cn)
                print("account Number is ", ac)
                tracker.slots["account_number"] = ac
                if len(ac)!=8 or ac == None:
                    dispatcher.utter_message(response="utter_invalidACNumber")
                    return {"account_number": None}
                else:
                    print("Correct account Number")
                    # account = db_manager.set_slot_value(tracker.sender_id, "account_number", ac)
                    ACINword = numberTranslate(ac)
                    print(f"AC Number in Bangla: {ACINword}")
                    return {"account_number": ac, "ACtext": ACINword, "requested_slot": "account_number_confirm"}
        else:
            if len(ac)!=8 or ac == None:
                dispatcher.utter_message(response="utter_invalidACNumber")
                return {"account_number": None, "requested_slot": "account_number"}

            else:
                print("Correct account Number")
                ACINword = numberTranslate(ac)
                print(f"AC Number in Bangla: {ACINword}")
                return {"account_number": ac, "ACtext": ACINword, "requested_slot": "account_number_confirm"}

    
    async def validate_account_number_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return{"account_number_confirm": "affirm", "ACtext": None, "account_check": False}
            # return [
            #         SlotSet("account_number_confirm", "affirm"),
            #         SlotSet("Incomplete_Story", True),
            #         SlotSet("ACtext", None),
            #         ]
        elif intent == "deny":
            print("account number is not correct.")
            return {"account_number_confirm": None, "account_number": None, "ACtext": None, "requested_slot": "account_number"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"account_number_confirm": None, "requested_slot": "account_number_confirm"}
    
    async def validate_PIN(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        
        print("validate_PIN")
        pin = tracker.get_slot("PIN")
        print("PIN Number is : ", pin)
        
        #BANGLA Check Here
        if (not is_ascii(pin)):  #If Bangla then enter here. is_ascii(otp) True for English
            cn = None
            if pin.isnumeric():
                cn = BnToEn(pin)
                print(str(cn))
                pin = str(cn)
                print("pin Number is ", pin)
                tracker.slots["PIN"] = pin
                if len(pin)!=4 or pin == None:
                    dispatcher.utter_message(response="utter_invalidPIN")
                    return{"PIN": None, "requested_slot":"PIN"}
                    # return [
                    #         SlotSet("PIN", None),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
                else:
                    print("Correct pin Number")
                    # account = db_manager.set_slot_value(tracker.sender_id, "PIN", pin)
                    pinINword = numberTranslate(pin)
                    print(f"card Number in Bangla: {pinINword}")
                    return {"PIN": pin, "PIN_Text": pinINword, "requested_slot":"PIN_confirm"}
                    # return [
                    #         SlotSet("PIN", pin),
                    #         SlotSet("Incomplete_Story", True),
                    #         ]
        else:
            if len(pin)!=4 or pin == None:
                dispatcher.utter_message(response="utter_invalidPIN")
                return{"PIN": None, "requested_slot":"PIN"}
                # return [
                #         SlotSet("PIN", None),
                #         SlotSet("Incomplete_Story", True),
                #         ]
            else:
                print("Correct pin Number")
                # account = db_manager.set_slot_value(tracker.sender_id, "PIN", pin)
                pinINword = numberTranslate(pin)
                print(f"card Number in Bangla: {pinINword}")
                return {"PIN": pin, "PIN_Text": pinINword, "requested_slot":"PIN_confirm"}

    async def validate_PIN_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            print("I'm HERE. inside PIN_CONFIRM")
            return {"PIN_confirm": "affirm", "PIN_Text": None}
        elif intent == "deny":
            print("pin is not correct.")
            return {"PIN_confirm": None, "PIN": None, "PIN_Text": None, "requested_slot": "PIN"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"PIN_confirm": None, "requested_slot": "PIN_confirm"}
        
class ActionValidationChequeCancel(FormValidationAction):
    """validate_cheque_form"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "validate_cheque_form"

    async def validate_cheque_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        print(f"active loop is, {active_loop}")
        SLT = tracker.slots.get('name')
        print(f"the rasa is requesting for {SLT}")
        
        print("validate_cheque_number")
        cheque = tracker.get_slot("cheque_number")
        print("cheque Number is : ", cheque)
        
        #BANGLA Check Here
        if (not is_ascii(cheque)):  #If Bangla then enter here. is_ascii(otp) True for English
            cn = None
            if cheque.isnumeric():
                cn = BnToEn(cheque)
                print(str(cn))
                cheque = str(cn)
                print("cheque Number is ", cheque)
                tracker.slots["cheque_number"] = cheque
                if len(cheque)!=6 or cheque == None:
                    dispatcher.utter_message(response="utter_invalidCHEQUEnumber")
                    return {"cheque_number": None, "requested_slot":"cheque_number"}
                else:
                    print("Correct cheque Number")
                    # account = db_manager.set_slot_value(tracker.sender_id, "cheque_number", cheque)
                    chequeINword = numberTranslate(cheque)
                    print(f"Cheque Number in Bangla: {chequeINword}")
                    return {"cheque_number": cheque, "ChequeNumberWord": chequeINword, "requested_slot":"cheque_number_confirm"}
        else:
            if len(cheque)!=6 or cheque == None:
                dispatcher.utter_message(response="utter_invalidCHEQUEnumber")
                return {"cheque_number": None, "requested_slot":"cheque_number"}
            else:
                print("Correct cheque Number")
                # account = db_manager.set_slot_value(tracker.sender_id, "cheque_number", cheque)
                chequeINword = numberTranslate(cheque)
                print(f"Cheque Number in Bangla: {chequeINword}")
                return {"cheque_number": cheque, "ChequeNumberWord": chequeINword, "requested_slot":"cheque_number_confirm"}
        
    async def validate_cheque_number_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return {"cheque_number_confirm": "affirm", "ChequeNumberWord": None}
        elif intent == "deny":
            print("phone number is not correct.")
            return {"cheque_number_confirm": None, "cheque_number": None, "ChequeNumberWord": None, "requested_slot": "cheque_number"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"cheque_number_confirm": None, "requested_slot": "cheque_number_confirm"}

    async def validate_amount_of_money(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        amount = tracker.get_slot("amount-of-money")
        print("amount inside function: ", amount)

        account_balance = profile_db.get_account_balance(tracker.sender_id)

        number = None
        #BANGLA Check Here
        if(not is_ascii(amount)):  #If Bangla then enter here
            print("Hello, Check Bangla")
            if amount.isnumeric():
                number = BnToEn(amount)
                amount = str(number)
                print("Number : ", number)
                print(amount)
                if(int(amount)<=0):
                    dispatcher.utter_message(response="utter_invalidAMOUNT")
                    # print("1")
                    return {"amount-of-money": None}
                else:
                    # print("2")
                    # account = db_manager.set_slot_value(tracker.sender_id, 'amount-of-money', amount)
                    amountBengaliWord = amount_in_word(amount)
                    print(f"amount is {amountBengaliWord}")
                    return {"amount-of-money": amount, "amountBengaliWord": amountBengaliWord, "requested_slot": "amount_confirm"}
            else:
                # print("3")
                return {"amount-of-money": None}
        else:
            # print("4")
            if(int(amount)<=0):
                # print("5")
                dispatcher.utter_message(response="utter_invalidAMOUNT")
                return {"amount-of-money": None, "requested_slot": "amount-of-money"}
            else:
                # account = db_manager.set_slot_value(tracker.sender_id, 'amount-of-money', amount)
                print("Amount is ", amount)
                amountBengaliWord = amount_in_word(amount)
                print(f"amount is {amountBengaliWord}")
                return {"amount-of-money": amount, "amountBengaliWord": amountBengaliWord, "requested_slot": "amount_confirm"}
    
    async def validate_amount_confirm(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""

        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])

        intent = tracker.latest_message['intent'].get('name')

        if intent == "affirm":
            return{"amount_confirm": "affirm", "amountBengaliWord": None}
        elif intent == "deny":
            print("amount is not correct.")
            return {"amount_confirm": None, "amount-of-money": None, "amountBengaliWord": None, "requested_slot": "amount-of-money"}
        else:
            print("something else.")
            # dispatcher.utter_message(response = "utter_ask_continue_form")
            return {"amount_confirm": None, "requested_slot": "amount_confirm"}

class ActionCancelCheque(Action):

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_Cheque_Cancel"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        
        dispatcher.utter_message(response = "utter_cheque_cancel_confirmed")

        return [
            SlotSet("Incomplete_Story", False),
            SlotSet("cheque_number", None),
            SlotSet("cheque_number_confirm", None),
            SlotSet("amount-of-money", None),
            SlotSet("amount_confirm", None),
            Form(None),
            SlotSet("requested_slot", None),
        ]

class ActionValidationecommerce(FormValidationAction):
    """validate_e_commerce_form"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "validate_e_commerce_form"
 
    async def validate_Father_Name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        print(f"active loop is, {active_loop}")
        SLT = tracker.slots.get('name')
        print(f"the rasa is requesting for {SLT}")
        
        print("validate_Father_Name")
        Name = tracker.get_slot("Father_Name")
        print("Name is in validate form and it is ", Name)

        #NAME can't be a number
        for character in Name:
            if character.isdigit():
                dispatcher.utter_message(response="utter_invalidNAME")
                return {"Father_Name": None}
        if Name!=None:
            if (len(Name) < 4):
                dispatcher.utter_message(response="utter_invalidNAME")
                return {"Father_Name": None, "requested_slot":"Father_Name"}
            else:
                print("Correct Name")
                return {"Father_Name": Name}
        else:
            dispatcher.utter_message(response="utter_invalidNAME")
            return {"Father_Name": None, "requested_slot":"Father_Name"}
        
    async def validate_Mother_Name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        print(tracker.latest_message['intent'].get('name'))
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        print(f"active loop is, {active_loop}")
        SLT = tracker.slots.get('name')
        print(f"the rasa is requesting for {SLT}")
        
        print("validate_Mother_Name")
        Name = tracker.get_slot("Mother_Name")
        print("Name is in validate form and it is ",Name)

        #USERNAME can't be a number
        for character in Name:
            if character.isdigit():
                dispatcher.utter_message(response="utter_invalidNAME")
                return {"Mother_Name": None, "requested_slot":"Mother_Name"}
        if Name!=None:
            if (len(Name) < 4):
                dispatcher.utter_message(response="utter_invalidNAME")
                # return {"Mother_Name": None}
                return {"Mother_Name": None, "requested_slot":"Mother_Name"}
            else:
                return {"Mother_Name": Name}
        else:
            dispatcher.utter_message(response="utter_invalidNAME")
            return {"Mother_Name": None, "requested_slot":"Mother_Name"}

    async def validate_Birth_Date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
    
        """Executes the action"""
        intent = tracker.latest_message['intent'].get('name')
        print(intent)
        print(tracker.latest_message['intent']['confidence'])
        active_loop = tracker.active_loop.get('name')
        
        
        print("validate_Birth_Date")
        Bdate = tracker.get_slot("Birth_Date")
        print("Name is in validate form and it is ", Bdate)

        newDate = Bdate.split("/")
        day = newDate[0]
        month = newDate[1]
        year = newDate[2]

        print(type(day))

        print(newDate)
        print(f"Day: {day}, month: {month}, year: {year}")
        month = int(month)
        if Bdate!=None:
            if month in range(1, 13):
                return {"Birth_Date": Bdate}
            else:
                dispatcher.utter_message(response="utter_invalidBDATE")
                return {"Birth_Date": None}
        else:
            dispatcher.utter_message(response="utter_invalidBDATE")
            return {"Birth_Date": None}
