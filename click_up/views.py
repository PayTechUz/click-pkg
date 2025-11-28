import logging
import hashlib

from django.conf import settings
from django.utils.module_loading import import_string

from rest_framework.views import APIView
from rest_framework.response import Response

from click_up import exceptions
from click_up.const import Action
from click_up.models import ClickTransaction
from click_up.typing.request import ClickShopApiRequest


logger = logging.getLogger(__name__)
AccountModel = import_string(settings.CLICK_ACCOUNT_MODEL)


# pylint: disable=W1203,E1101,W0707


class ClickWebhook(APIView):
    """
    API endpoint for handling incoming CLICK webhooks.
    """
    def post(self, request):
        """
        Check if request is valid
        """
        # check 1 validation
        result = None
        params: ClickShopApiRequest = self.serialize(request)
        account = self.fetch_account(params)

        # check 2 check perform transaction
        existing_transaction = self.check_perform_transaction(account, params)

        # If transaction already paid, return success response
        if existing_transaction:
            return Response({
                "click_trans_id": params.click_trans_id,
                "merchant_trans_id": existing_transaction.account_id,
                "merchant_prepare_id": existing_transaction.id,
                "error": 0,
                "error_note": "success"
            })

        if params.action == Action.PREPARE:
            result = self.create_transaction(account, params)

        elif params.action == Action.COMPLETE:
            result = self.perform_transaction(account, params)

        return Response(result)

    def serialize(self, request):
        """
        serialize request data to object
        """
        request_data = {
            'click_trans_id': request.POST.get('click_trans_id'),
            'service_id': request.POST.get('service_id'),
            'click_paydoc_id': request.POST.get('click_paydoc_id'),
            'merchant_trans_id': request.POST.get('merchant_trans_id'),
            'amount': request.POST.get('amount'),
            'action': request.POST.get('action'),
            'error': request.POST.get('error'),
            'sign_time': request.POST.get('sign_time'),
            'sign_string': request.POST.get('sign_string'),
            'error_note': request.POST.get('error_note'),
            'merchant_prepare_id': request.POST.get('merchant_prepare_id'),
        }

        try:
            request_data = ClickShopApiRequest(**request_data)
            self.check_auth(request_data)

            request_data.is_valid()
            return request_data

        except exceptions.errors_whitelist as exc:
            raise exc

        except Exception as exc:
            logger.error(f"error in request data: {exc}")
            raise exceptions.BadRequest("error in request from click")

    def check_auth(self, params, service_id=None, secret_key=None):
        """
        Verifies the authenticity of the transaction using the secret key.

        :return: True if the signature is valid,
            otherwise raises an AuthFailed exception.
        """
        # by default it should be get from settings
        # in the another case u can override
        if not secret_key or not service_id:
            service_id = settings.CLICK_SERVICE_ID
            secret_key = settings.CLICK_SECRET_KEY

        if not all([service_id, secret_key]):
            error = "Missing required CLICK_SETTINGS: service_id, secret_key, or merchant_id" # noqa
            raise exceptions.AuthFailed(error)

        text_parts = [
            params.click_trans_id,
            service_id,
            secret_key,
            params.merchant_trans_id,
            params.merchant_prepare_id or "",
            params.amount,
            params.action,
            params.sign_time,
        ]
        text = ''.join(map(str, text_parts))

        calculated_hash = hashlib.md5(text.encode('utf-8')).hexdigest()

        if calculated_hash != params.sign_string:
            raise exceptions.AuthFailed("invalid signature")

    def fetch_account(self, params: ClickShopApiRequest):
        """
        fetching account for given merchant transaction id
        """
        try:
            return AccountModel.objects.get(id=params.merchant_trans_id)

        except AccountModel.DoesNotExist:
            raise exceptions.AccountNotFound("Account not found")

    def check_amount(self, account: AccountModel,
                     params: ClickShopApiRequest):  # type: ignore
        """
        Validate the received amount, considering optional commission percent.
        """
        received_amount = float(params.amount)
        base_amount = float(getattr(account, settings.CLICK_AMOUNT_FIELD))
        commission_percent = getattr(settings, "CLICK_COMMISSION_PERCENT", 0)

        expected_amount = round(base_amount * (1 + commission_percent / 100), 2) # noqa

        if abs(received_amount - expected_amount) > 0.01:
            raise exceptions.IncorrectAmount("Incorrect parameter amount")

    def check_dublicate_transaction(self, params: ClickShopApiRequest):  # type: ignore # noqa
        """
        check if transaction already exist
        """
        existing_transaction = ClickTransaction.objects.filter(
            account_id=params.merchant_trans_id,
            state=ClickTransaction.SUCCESSFULLY
        ).first()

        if existing_transaction:
            return existing_transaction
        return None

    def check_transaction_cancelled(self, params: ClickShopApiRequest):
        """
        check if transaction cancelled
        """
        if ClickTransaction.objects.filter(
            account_id=params.merchant_trans_id,
            state=ClickTransaction.CANCELLED
        ).exists() or int(params.error) < 0:
            raise exceptions.TransactionCancelled("Transaction cancelled")

    def check_perform_transaction(self, account: AccountModel,
                                  params: ClickShopApiRequest):  # type: ignore
        """
        Check perform transaction with CLICK system
        """
        self.check_amount(account, params)
        existing_transaction = self.check_dublicate_transaction(params)
        if existing_transaction:
            return existing_transaction
        self.check_transaction_cancelled(params)
        return None

    def create_transaction(self, account: AccountModel,
                           params: ClickShopApiRequest):  # type: ignore
        """
        create transaction in your system
        """
        transaction = ClickTransaction.get_or_create(
            account_id=account.id,
            amount=params.amount,
            transaction_id=params.click_trans_id
        )

        # callback event
        self.created_payment(params)

        return {
            "click_trans_id": params.click_trans_id,
            "merchant_trans_id": account.id,
            "merchant_prepare_id": transaction.id,
            "error": 0,
            "error_note": "success"
        }

    def perform_transaction(self, account: AccountModel,
                            params: ClickShopApiRequest):  # type: ignore
        """
        perform transaction with CLICK system
        """
        state = ClickTransaction.SUCCESSFULLY

        if params.error is not None:
            if int(params.error) < 0:
                state = ClickTransaction.CANCELLED

        transaction = ClickTransaction.update_or_create(
            account_id=account.id,
            amount=params.amount,
            transaction_id=params.click_trans_id,
            state=state
        )

        # callback event
        if state == ClickTransaction.SUCCESSFULLY:
            self.successfully_payment(params)

        elif state == ClickTransaction.CANCELLED:
            self.cancelled_payment(params)

        return {
            "click_trans_id": params.click_trans_id,
            "merchant_trans_id": transaction.account_id,
            "merchant_prepare_id": transaction.id,
            "error": params.error,
            "error_note": params.error_note
        }

    def created_payment(self, params):
        """
        created payment method process you can ovveride it
        """

    def successfully_payment(self, params):
        """
        successfully payment method process you can ovveride it
        """
        print(f"payment successful params: {params}")

    def cancelled_payment(self, params):
        """
        cancelled payment method process you can ovveride it
        """
        print(f"payment cancelled params: {params}")
