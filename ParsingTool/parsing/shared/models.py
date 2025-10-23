from dataclasses import dataclass
from typing import Optional


@dataclass
class BatchRow:
    Requested_By: str = ""
    Date_Requested: str = ""
    Picking_Request_Number: str = ""
    Delivery_Number: str = ""
    OLAM_Ref_Number: str = ""
    Batch_Number: str = ""
    SSCC_Qty: str = ""  # "X PAL" if matches, else ""
    Customer_Delivery_Date: str = ""  # DD/MM/YYYY
    Customer: str = ""
    Customer_Delivery_Address: str = ""
    Date_of_Pick_Up: str = ""
    Total_Days_In_Transit: str = ""
    Plant_Storage_Location: str = ""
    Inspection_Type: str = ""
    Inspection_progress: str = ""
    Inspection_Status: str = ""
    Inspection_Date: str = ""
    Variety: str = ""
    Grade: str = ""
    Size: str = ""
    Packaging: str = ""
    Total_Gross_Weight: str = ""  # standardised name
    Pallet: str = ""  # always blank (override later)
    Comments: str = ""
    Non_Conformance: str = ""


@dataclass
class SSCCRow:
    Delivery_Number: str
    Batch_Number: str
    SSCC: str
    Variety: str
    Grade: str
    Size: str
    Packaging: str
