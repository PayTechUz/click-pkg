from typing import Optional
from dataclasses import dataclass


@dataclass
class ClickShopApiResponse:
    """
    Represents a payment transaction in the CLICK system.

    Attributes:
        click_trans_id (int): The unique Payment ID in the CLICK system.
        merchant_trans_id (str):
            The Order ID, personal account,
            or login in the supplier's billing system.
        merchant_confirm_id (Optional[int]):
            The Transaction ID used to complete
            the payment in the billing system.
            This may be NULL if not applicable.
        error (int):
            The status code indicating the result of the payment.
            0 indicates success, while other codes indicate an error.
        error_note (Optional[str]):
            A description or note corresponding to the error code,
            providing additional context.
    """
    error: int
    click_trans_id: int
    merchant_trans_id: str
    error_note: Optional[str] = None
    merchant_confirm_id: Optional[int] = None

    @classmethod
    def as_resp(cls):
        """
        returns response click shop api
        """
        return {
            "error": cls.error,
            "click_trans_id": cls.click_trans_id,
            "merchant_trans_id": cls.merchant_trans_id,
            "error_note": cls.error_note,
            "merchant_confirm_id": cls.merchant_confirm_id
        }
