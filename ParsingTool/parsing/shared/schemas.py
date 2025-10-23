# Shared CSV schemas for parsing pipelines
# Feel free to import these in your pipeline modules and writers

BATCHES_COLUMNS = [
    "Requested By",
    "Date Requested",
    "Picking Request Number",
    "Delivery Number",
    "OLAM Ref Number",
    "Batch Number",
    "SSCC Qty",
    "Customer Delivery Date",
    "Customer",
    "Customer/Delivery Address",
    "Date of Pick Up",
    "Total Days In Transit",
    "Plant/Storage Location",
    "Inspection Type",
    "Inspection progress",
    "Inspection Status",
    "Inspection Date",
    "Variety",
    "Grade",
    "Size",
    "Packaging",
    "Total Gross Weight",
    "Pallet",
    "Comments",
    "Non-Conformance",
]

SSCC_COLUMNS = [
    "Delivery Number",
    "Batch Number",
    "SSCC",
    "Variety",
    "Grade",
    "Size",
    "Packaging",
]

# Export pipeline (single-row CSV per PDF)
EXPORT_COLUMNS = [
    "Name",
    "Date Requested",
    "OLAM Ref Number",
    "Delivery Number",
    "Sale Order Number",
    "Batch Number",
    "SSCC Qty",
    "Vessel ETD",
    "Destination",
    "3rd Party Storage",
    "Variety",
    "Grade",
    "Size",
    "Packaging",
    "Pallet",
    "Fumigation",
    "Container",
]

# Common validations for Export (can be shared by qc.py)
EXPORT_VALID_GRADES = {"SSR", "Supr", "Xno1", "Rejects"}
