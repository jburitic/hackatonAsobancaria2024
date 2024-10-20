# -*- coding: utf-8 -*-
"""
@author: juburiti

"""

import pytesseract
import os
from pdf2image import convert_from_path
import pandas as pd
import re
import time

pd.set_option('display.max_columns', None)

path = os.getcwd()
poppler_path = r'C:\installed\poppler-24.02.0\Library\bin'
pytesseract.pytesseract.tesseract_cmd = r'C:\installed\Tesseract-OCR\tesseract.exe'



def dar_formato_df(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    columns = ["ID","nombre","ciudad","anio","mes","dia","valor","intereses","tasa_intereses","id_cliente","tipo_documento","firmado"]

    # intersección entre las columnas esperadas y las columnas ya existentes en el dataframe
    cols = list(set(columns) & set(df2.columns))

    # adiciono las columnas que hacen falta en blanco
    for c in columns:
        if c not in cols:
            df2[c] = ""
    
    return df2[columns]

def limpiaString(texto):
    chars_to_remove  = ['\n','_+','\s+','\)', '\(', '\$', '\%']

    texto = re.sub("|".join(chars_to_remove), " ", texto)
    #texto = ''.join([c for c in texto if c not in chars_to_remove])
    texto = texto.strip()
    return texto

pdfs = [i for i in os.listdir(os.path.join(path,'data')) if i.endswith(".pdf")]

ids=[]
for pdf in pdfs:
    id_pagare = int(pdf.split(".")[0])
    ids.append(id_pagare)

columns = ["ID","nombre","ciudad","anio","mes","dia","valor","intereses","tasa_intereses","id_cliente","tipo_documento","firmado"]

inicio = time.time()

for pdf in pdfs:
    pdf_file = os.path.join(path, 'data', pdf)
    pages = convert_from_path(pdf_file, 350, poppler_path=poppler_path)
    #pages = convert_from_path(path+pdf_file, 500)
    nombre_pdf=pdf_file.split(".")[0]

    for i, page in enumerate(pages):
        image_name = "_P_" + str(i) + ".jpg"
        #print(image_name)
        page.save(os.path.join(path, 'data', nombre_pdf+image_name), "JPEG")    
        txt=pytesseract.image_to_string(page, lang="spa")
        text_file_name = nombre_pdf+"_"+str(i)+".txt"
        text_file=open(text_file_name, "a")
        #print(txt)
        text_file.write(txt)
        text_file.close()

fin = time.time()
# 667.21  segundos aprox 11 minutos
print("terminó de guardar imágenes y pasar las imágenes a texto", round(time.time()-inicio, 2), " segundos")

pathTxt = os.path.join(path, "data")
txts = [i for i in os.listdir(pathTxt) if i.endswith(".txt")]

data = []

for txt in txts:
    tmp = []
    file = open(os.path.join(pathTxt,txt), "r")
    content = file.read()
    #campos = extraerCampos(content)
    tmp.extend([txt, content])
    #tmp.extend(campos)
    data.append(tmp)
    #print(content)
    file.close()


# paso toda la información a un df de pandas:
df = pd.DataFrame(data, columns=['fileName', 'content'])

df['ID'] = df['fileName'].str.split('_').str[0].astype(int)
df['page'] = df['fileName'].str.split('_').str[2].str.split(".").str[0]

# separamos cada página en una columna
df = df.pivot(values='content', index='ID', columns='page')
df = df.reset_index().rename_axis(None, axis=1)

exp_patterns = {
        #'ID': r'No\.(.*) Yo,',
        'nombre': r'Yo,(.*)mayor', #r'Yo,(.+)((?:\n.+)+)mayor',
        'ciudad': r'en _(.*)en virtud',
        'anio': r'(\d{4}.*)a la orden', #r'de (.*)a la orden',
        'mes': r'mes de(.*) de \d{4}',
        'dia': r'día(.*)del mes',
        'valor': r'suma de[\n\s]*(.*)\n*MONEDA LEGAL, .* he', #r'suma de(.+)((?:\n.+)+)MONEDA LEGAL, que he',
        'intereses': r's la suma de[\n\s]*(.*) \){0,1} MONEDA',
        'tasa_intereses': r'del[\n\s]*\((.*)\) anual'
}

exp_patterns_p1 = {
        'id_cliente': r'\n*(\d{4,})\n',
        'tipo_documento': r'\n*\d{4,}\n*(.*)\n.*',
        'firmado': r'wisi.\n*(.*)\n*DEUDOR'

}

#SCORE:  20.9
df['nombre'] = df['0'].str.extract(r'Yo,(.*)mayor')
df['nombre'] = df['nombre'].apply(lambda x: limpiaString(str(x)))
df['nombre'] = df['nombre'].replace({'nan':''})

#SCORE:  26
df['ciudad'] = df['0'].str.extract(r'en _(.*)en virtud')
df['ciudad'] = df['ciudad'].apply(lambda x: limpiaString(str(x)))
df['ciudad'] = df['ciudad'].replace({'nan':''})

#SCORE:  28
df['anio'] = df['0'].str.extract(r'(\d{4}.*)a la orden')
df['anio'] = df['anio'].apply(lambda x: limpiaString(str(x)))
df['anio'] = df['anio'].replace({'nan':''})
#df['anio'].fillna(value="")

#SCORE:  29.2
df['mes'] = df['0'].str.extract(exp_patterns['mes'])
df['mes'] = df['mes'].apply(lambda x: limpiaString(str(x)))
df['mes'] = df['mes'].replace({'nan':''})

#SCORE: 34.3
df['dia'] = df['0'].str.extract(exp_patterns['dia'])
df['dia'] = df['dia'].apply(lambda x: limpiaString(str(x)))
df['dia'] = df['dia'].replace({'nan':''})

# SCORE:  34.7
df['valor'] = df['0'].str.extract(exp_patterns['valor'])
df['valor'] = df['valor'].apply(lambda x: limpiaString(str(x)))
df['valor'] = df['valor'].replace({'nan':''})

#SCORE:  37.4
df['intereses'] = df['0'].str.extract(exp_patterns['intereses'])
df['intereses'] = df['intereses'].apply(lambda x: limpiaString(str(x)))
df['intereses'] = df['intereses'].replace({'nan':''})

# SCORE:  38.8
df['tasa_intereses'] = df['0'].str.extract(exp_patterns['tasa_intereses'])
df['tasa_intereses'] = df['tasa_intereses'].apply(lambda x: limpiaString(str(x)))
df['tasa_intereses'] = df['tasa_intereses'].replace({'nan':''})

# SCORE: 39.5
df['id_cliente'] = df['1'].str.extract(exp_patterns_p1['id_cliente'])
df['id_cliente'] = df['id_cliente'].apply(lambda x: limpiaString(str(x)))
df['id_cliente'] = df['id_cliente'].replace({'nan':''})

#SCORE:  42.4
df['tipo_documento'] = df['1'].str.extract(exp_patterns_p1['tipo_documento'])
df['tipo_documento'] = df['tipo_documento'].apply(lambda x: limpiaString(str(x)))
df['tipo_documento'] = df['tipo_documento'].replace({'nan':''})


#SCORE:  49.1
df['firmado'] = df['1'].str.extract(exp_patterns_p1['firmado'])
df['firmado'] = df['firmado'].apply(lambda x: limpiaString(str(x)))
df['firmado'] = df['firmado'].replace({'nan':''})
df['firmado'] != ""
df['firmado'] = df['firmado'].where(df['firmado'] != "", 0) # si diferente de vacio deja el valor de lo contrario pone 0
df['firmado'] = df['firmado'].mask(df['firmado'] != 0, 1) # si diferente de vacio pone 1


df2 = dar_formato_df(df)
df2.to_csv("resultadoPaso2.csv", index=False, sep=";")