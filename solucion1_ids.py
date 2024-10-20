# -*- coding: utf-8 -*-
"""
@author: juburiti

"""

import pandas as pd
import os

path = os.getcwd()
pdfs = [i for i in os.listdir(os.path.join(path,'data')) if i.endswith(".pdf")]

data=[]
for pdf in pdfs:
    id_pagare = int(pdf.split(".")[0])
    data.append([id_pagare, "", "", "", "", "", "", "", "", "", "", ""])

columns = ["ID","nombre","ciudad","anio","mes","dia","valor","intereses","tasa_intereses","id_cliente","tipo_documento","firmado"]

df = pd.DataFrame(data=data, columns=columns)

#SCORE:  18.2
df.to_csv("resultadoPaso1.csv", index=False, sep=";")