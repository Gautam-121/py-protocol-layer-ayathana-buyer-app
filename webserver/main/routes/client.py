from flask import request
from flask_restx import Namespace, Resource
from threading import Thread
from datetime import datetime , timezone
import uuid


from main.logger.custom_logging import log
from main.service.common import bpp_post_call, dump_request_payload, update_dumped_request_with_response
from main.service.search import gateway_search
from main.utils.validation import validate_payload_schema_based_on_version

client_namespace = Namespace('client', description='Client Namespace')


# Function to construct the /info payload from the /select payload
def construct_info_payload(select_payload):
    info_payload = {
        "context": {
            "domain": select_payload["context"].get("domain", "ONDC:RET10"),
            "country": select_payload["context"].get("country", "IND"),
            "city": select_payload["context"].get("city", "std:080"),
            "action": "info",
            "core_version": select_payload["context"].get("core_version", "1.2.0"),
            "bap_id": select_payload["context"]["bap_id"],
            "bap_uri": select_payload["context"]["bap_uri"],
            "bpp_id": select_payload["context"]["bpp_id"],
            "bpp_uri": select_payload["context"]["bpp_uri"],
            "transaction_id": select_payload["context"]["transaction_id"],
            "message_id": select_payload["context"]["message_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "key": "981foErFyRK5qdQ6ty9EbPuj9c0Y/a5aMEao0NgDFX0=",
            "ttl": select_payload["context"].get("ttl", "PT30S"),
        },
        "message": {
            "intent": {
                "descriptor": {
                    "code": "INFO"
                }
            }
        }
    }
    return info_payload


def create_callback_body(context):
    """
    Creates a callback body with the required structure and includes
    fallback values to ensure no 'NoneType' errors occur.
    """
    return {
        "context": {
            "domain": context.get("domain", "ONDC:RET14"),
            "action": "on_info",
            "country": "IND",
            "city": context.get("city", "std:080"),
            "core_version": "1.2.0",
            "bap_id": "preprod.xircular.io/preprod",
            "bap_uri": "https://3316-106-51-37-219.ngrok-free.app/protocol/v1",
            "transaction_id": context.get("transaction_id", str(uuid.uuid4())),
            "message_id": str(uuid.uuid4()),  # Generate a new message ID
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "bpp_id": context.get("bpp_id", "pramaan.ondc.org/alpha/mock-server"),
            "bpp_uri": context.get("bpp_uri", "https://pramaan.ondc.org/alpha/mock-server/buyer"),
            "key":"981foErFyRK5qdQ6ty9EbPuj9c0Y/a5aMEao0NgDFX0=",
            "ttl": "PT30S"
        },
        "message": {
            "info": {
                "type": "BAP",
                "entity": {
                    "gst": {
                        "legal_entity_name": "WITS ONDC TEST STORE Buyer App",
                        "business_address": "7/6, August Kranti Marg, Siri Fort Institutional Area, Siri Fort, New Delhi, 110049",
                        "city_code": ["std:080"],
                        "gst_no": "07AAACN2082N4Z7"
                    },
                    "pan": {
                        "name_as_per_pan": "WITS ONDC TEST STORE",
                        "pan_no": "ASDFP7657Q",
                        "date_of_incorporation": "23/06/1982"
                    },
                    "name_of_authorised_signatory": "Mayur Popli",
                    "address_of_authorised_signatory": "7/6, August Kranti Marg, Siri Fort Institutional Area, Siri Fort, New Delhi, 110049",
                    "email_id": "nobody@nomail.com",
                    "mobile_no": 9512332191,
                    "country": "IND",
                    "bank_details": {
                        "account_no": "392387650088712",
                        "ifsc_code": "SBIN0000691",
                        "beneficiary_name": "Mayur Popli",
                        "bank_name": "SBI",
                        "branch_name": "New Delhi Main"
                    }
                }
            }
        }
    }


@client_namespace.route("/search")
class GatewaySearch(Resource):

    def post(self):
        request_payload = request.get_json()
        # validate schema based on context version
        log(f"Got the search request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'search')
        if resp is None:
            entry_object_id = dump_request_payload("search", request_payload)
            resp = gateway_search(request_payload)
            log(f"Got the search response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/select")
class AddSelectRequest(Resource):

    def post(self):

        request_payload = request.get_json()
        log(f"Got the select requests payload {request_payload}!")

         # Step 1: Validate /select payload
        resp = validate_payload_schema_based_on_version(request_payload, 'select')

        if resp is None:

            # # Step 2: Construct /info payload and call /info
            info_payload = construct_info_payload(request_payload)
            log(f"Constructed /info payload: {info_payload}!")
            entry_object_id_info = dump_request_payload("info", request_payload)
            info_response = bpp_post_call("info", info_payload)
            log(f"Received /info response: {info_response}!")
            update_dumped_request_with_response(entry_object_id_info, info_response)

            # Step 3: call /select
            entry_object_id = dump_request_payload("select", request_payload)
            resp = bpp_post_call('select', request_payload)
            log(f"Got the select responses {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/init")
class AddInitRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the init request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'init')
        if resp is None:
            entry_object_id = dump_request_payload("init", request_payload)
            resp = bpp_post_call('init', request_payload)
            log(f"Got the init response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/confirm")
class AddConfirmRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the confirm request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'confirm')
        if resp is None:
            entry_object_id = dump_request_payload("confirm", request_payload)
            resp = bpp_post_call('confirm', request_payload)
            log(f"Got the confirm response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/cancel")
class AddCancelRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the cancel request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'cancel')
        if resp is None:
            entry_object_id = dump_request_payload("cancel", request_payload)
            resp = bpp_post_call('cancel', request_payload)
            log(f"Got the cancel response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/issue")
class AddIssueRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the issue request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'issue')
        if resp is None:
            entry_object_id = dump_request_payload("issue", request_payload)
            resp = bpp_post_call('issue', request_payload)
            log(f"Got the issue response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/issue_status")
class AddIssueStatusRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the issue_status request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'issue_status')
        if resp is None:
            entry_object_id = dump_request_payload("issue_status", request_payload)
            resp = bpp_post_call('issue_status', request_payload)
            log(f"Got the issue_status response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/rating")
class AddRatingRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the rating request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'rating')
        if resp is None:
            entry_object_id = dump_request_payload("rating", request_payload)
            resp = bpp_post_call('rating', request_payload)
            log(f"Got the rating response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp
        

@client_namespace.route("/status")
class AddStatusRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the status request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'status')
        if resp is None:
            entry_object_id = dump_request_payload("status", request_payload)
            resp = bpp_post_call('status', request_payload)
            log(f"Got the status response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/support")
class AddSupportRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the support request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'support')
        if resp is None:
            entry_object_id = dump_request_payload("support", request_payload)
            resp = bpp_post_call('support', request_payload)
            log(f"Got the support response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/track")
class AddTrackRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the track request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'track')
        if resp is None:
            entry_object_id = dump_request_payload("track", request_payload)
            resp = bpp_post_call('track', request_payload)
            log(f"Got the track response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp


@client_namespace.route("/update")
class AddUpdateRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the update request payload {request_payload}!")
        resp = validate_payload_schema_based_on_version(request_payload, 'update')
        if resp is None:
            entry_object_id = dump_request_payload("update", request_payload)
            resp = bpp_post_call('update', request_payload)
            log(f"Got the update response {resp}!")
            update_dumped_request_with_response(entry_object_id, resp)
            return resp
        else:
            return resp
        

@client_namespace.route("/v1/info")
class AddUpdateRequest(Resource):
    def post(self):
        try:
            # Get request payload
            request_payload = request.get_json()
            log(f"Got the info request payload from seller side {request_payload}!")
            entry_object_info_id = dump_request_payload("info_seller", request_payload)

             # Validate payload
            validation_resp = validate_payload_schema_based_on_version(request_payload, 'info')
            if validation_resp is not None:
                update_dumped_request_with_response(entry_object_info_id, validation_resp)
                return validation_resp

            # Extract context from payload
            context = request_payload.get('context', {})
            # Create callback body
            callback_body = create_callback_body(context)

            # Prepare immediate ACK response
            ack_response = {
                "message": {
                    "ack": {
                        "status": "ACK"
                    }
                }
            }

            # Start callback in a separate thread
            def make_callback():
                try:

                    # Store request payload
                    entry_object_id = dump_request_payload("on_info_seller", callback_body)
                    callback_resp, status_code = bpp_post_call('on_info', callback_body)
                    log(f"Got the on_info callback response that we have send on seller info {callback_resp}!")
                    update_dumped_request_with_response(entry_object_id, callback_resp)

                    if status_code not in (200, 201, 202):
                        log(f"Callback failed with status {status_code}")

                except Exception as e:
                    log(f"Error in callback: {str(e)}")

            # Start the callback in background
            Thread(target=make_callback).start()

            update_dumped_request_with_response(entry_object_info_id, ack_response)
            # Return immediate ACK response
            return ack_response, 200

        except Exception as e:
            log(f"Error processing info request: {str(e)}")
            error_response = {
                "message": {
                    "ack": {
                        "status": "NACK",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": str(e)
                        }
                    }
                }
            }
            return error_response, 500
    

@client_namespace.route("/get_cancellation_reason")
class AddUpdateRequest(Resource):

    def post(self):
        request_payload = request.get_json()
        log(f"Got the get_cancellation_reason request payload {request_payload}!")
        # resp = validate_payload_schema_based_on_version(request_payload, 'update')
        # if resp is None:
            # entry_object_id = dump_request_payload("update", request_payload)
        resp = bpp_post_call('cancel', request_payload)
        log(f"Got the get_cancellation_reason response {resp}!")
        # update_dumped_request_with_response(entry_object_id, resp)
        return resp
        # else:
            # return resp