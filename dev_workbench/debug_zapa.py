from ParsingTool.parsing.export_orders.pipeline import parse_export_pdf
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

df = parse_export_pdf('input/0080605769_ZAPA.pdf')
print(df)
print("\nVariety:", df['Variety'].iloc[0])
print("Grade:", df['Grade'].iloc[0])
print("Packaging:", df['Packaging'].iloc[0])
