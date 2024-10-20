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
from PIL import Image

# para codificar los archivos .txt -> buscar windows 1252

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

inicio = time.time()

imgs = [i for i in os.listdir(os.path.join(path,'data')) if i.endswith(".jpg")]
# leemos las imágenes las que estén giradas 180 grados y las rotamos
for image in imgs:
    img = Image.open(os.path.join('data', image))
    osd = pytesseract.image_to_osd(img)
    angle = re.search('(?<=Rotate: )\d+', osd).group(0)
    if angle == '180':
        print(image)
        img = img.rotate(int(angle))
        img.save(os.path.join(path, 'data', image))

fin = time.time()

#280.3 segundos  5 minutos
print("tiempo en girar las imágenes: ", fin - inicio, " segundos")

# paso nuevamente las imágenes por el OCR.
inicio = time.time()
for image in imgs:
    img = Image.open(os.path.join('data', image))
    custom_config = r'--oem 3 --psm 6'
    txt=pytesseract.image_to_string(img, lang='spa', config=custom_config)
    text_file_name = image.split(".")[0]+".txt"
    text_file=open(os.path.join("data",text_file_name), "a")
    text_file.write(txt)
    text_file.close()

fin = time.time()

#280.3 segundos  6 minutos  # con whitelist: 407.8  segundos - 7 minutos
print("tiempo en pasar nuevamente las imágenes por el OCR: ", round(fin - inicio, 2), " segundos")



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
        # en este caso [\s\S]* es similar a .* pero incluye el \n   y el (?:) significa que capturo el grupo pero no lo retorno.
        'nombre': r'Yo[,\.][\n\s]*([\s\S]*?)(?:[\n\s]*[TmM]ayo[rt])', #r'Yo,(.+)((?:\n.+)+)mayor',
        'ciudad': r'en[\W\s\n_]*(.*)[\s]*en virtud',
        'anio': r"([12]\d{3})[.\s_\d]+[4alt]+", #r'(\d{4}.*)a*\s*[ltf]+[aá]\s*orden', #r'de (.*)a la orden',
        'mes': r'mes\s+de[—\s_\.]*([a-z]{4,10})[_.\s]*de',
        'dia': r'd[ií]?a[\s_\.:]*([1-9][0-9]?).*', #r'día(.*)del mes',
        'valor': r'sum[a\.]+([\s\S]*?)M[O]?N', #r'suma de[\n\s]*(.*)\n*MONEDA LEGAL, .* he', #r'suma de(.+)((?:\n.+)+)MONEDA LEGAL, que he',
        'intereses': r's[.\s]+[lt]a ([\s\S]*?)M[O]?N',#r's la suma de[\n\s]*(.*) \){0,1} MONEDA',
        'tasa_intereses': r'asa del?([\s\S]+?)[aá]?[nñ]?ual' #r'del[\n\s]*\((.*)\) anual'
}

exp_patterns_p1 = {
        'id_cliente': r'(\d{4,})',#r'\n*(\d{4,})\n',
        'tipo_documento': r'(NIT|CC|CE)',#r'\n*\d{4,}\n*(.*)\n.*',
        'firmado': r'wisi.\n*(.*)\n*DEUD[O]?R',
        'nombre2': r'DEU.*([A-Z\s]+)Nom'#r'DEU[\s\S]*$([A-Z\s]+)Nom'

}

#SCORE: 25.2
pattern = re.compile(exp_patterns['nombre'])

df['nombre'] = df['0'].str.extract(pattern)
df['nombre'] = df['nombre'].apply(lambda x: limpiaString(str(x)))
df['nombre'] = df['nombre'].replace({'nan':''})
# elimino caracteres especiales: todo lo que no sean letras o espacios
df['nombre'] = df['nombre'].replace(regex={r'[^\w\s]+': ''}) # ^a-zA-Z ]
# si el nombre es muy largo (> 40 caracteres) deje sólo los 40 primeros
idx = df[df['nombre'].str.len()>40].index 
df.loc[idx,'nombre'] = df.loc[idx, 'nombre'].str[:40]
df['nombre'] = df['nombre'].str.strip()


#SCORE:  31.5, 33.1
df['ciudad'] = df['0'].str.extract(exp_patterns['ciudad'])
df['ciudad'] = df['ciudad'].apply(lambda x: limpiaString(str(x)))
df['ciudad'] = df['ciudad'].replace({'nan':''})
# eliminino caracteres especiales y números
df['ciudad'] = df['ciudad'].replace(regex={r'[^\w\s]|[0-9]+': ''})
df['ciudad'] = df['ciudad'].str.strip()


#SCORE:  33.7, 38.1
df['anio'] = df['0'].str.extract(exp_patterns['anio'])
df['anio'] = df['anio'].apply(lambda x: limpiaString(str(x)))
df['anio'] = df['anio'].replace({'nan':''})
df['anio'] = df['anio'].replace(regex={r'[^0-9]': ''})
df['anio'] = df['anio'].str.strip()

re.findall(r"\W+", "abc — ")
#SCORE:  29.2, 45.1
df['mes'] = df['0'].str.extract(exp_patterns['mes'])
df['mes'] = df['mes'].apply(lambda x: limpiaString(str(x)))
df['mes'] = df['mes'].replace({'nan':''})
df['mes'] = df['mes'].replace(regex={r'[^\w\s]|[0-9]+': ''})

#SCORE: 34.3, 53.3
df['dia'] = df['0'].str.extract(exp_patterns['dia'])
df['dia'] = df['dia'].apply(lambda x: limpiaString(str(x)))
df['dia'] = df['dia'].replace({'nan':''})

# SCORE:  34.7, 57.6
df['valor'] = df['0'].str.extract(exp_patterns['valor'])
df['valor'] = df['valor'].apply(lambda x: limpiaString(str(x)))
df['valor'] = df['valor'].replace({'nan':''})
df['valor'] = df['valor'].replace(regex={r'[^0-9,\.]': ''})
#limpio todo lo que esté a la izquierda y no sea un número:
df['valor'] = df['valor'].replace(regex={r'^[^0-9]+(?=\d)': ''})


#SCORE:  37.4, 61.9
df['intereses'] = df['0'].str.extract(exp_patterns['intereses'])
df['intereses'] = df['intereses'].apply(lambda x: limpiaString(str(x)))
df['intereses'] = df['intereses'].replace({'nan':''})
df['intereses'] = df['intereses'].replace(regex={r'^[^0-9]+(?=\d)': ''})
idx = df[df['intereses'].str.len()>15].index 
df.loc[idx,'intereses'] = df.loc[idx, 'intereses'].str[:15]


# SCORE:  38.8, 67.0
df['tasa_intereses'] = df['0'].str.extract(exp_patterns['tasa_intereses'])
df['tasa_intereses'] = df['tasa_intereses'].apply(lambda x: limpiaString(str(x)))
df['tasa_intereses'] = df['tasa_intereses'].replace({'nan':''})
df['tasa_intereses'] = df['tasa_intereses'].replace(regex={r'[^0-9\.,]': ''})
df['tasa_intereses'] = df['tasa_intereses'].replace(regex={r'^[^0-9]+(?=\d)': ''})
idx = df[df['tasa_intereses'].str.len()>7].index 
df.loc[idx,'tasa_intereses'] = df.loc[idx, 'tasa_intereses'].str[:7]
# Elimino caracteres finales después del número
df['tasa_intereses'] = df['tasa_intereses'].replace(regex={r'(?<=[0-9])[^0-9]+$': ''})

# SCORE: 39.5, 68.6
df['id_cliente'] = df['1'].str.extract(exp_patterns_p1['id_cliente'])
df['id_cliente'] = df['id_cliente'].apply(lambda x: limpiaString(str(x)))
df['id_cliente'] = df['id_cliente'].replace({'nan':''})

#SCORE:  46.8, 74.0
df['tipo_documento'] = df['1'].str.extract(exp_patterns_p1['tipo_documento'])
df['tipo_documento'] = df['tipo_documento'].apply(lambda x: limpiaString(str(x)))
df['tipo_documento'] = df['tipo_documento'].replace({'nan':''})

# SCORE: 76.7
df['firmado'] = df['1'].str.extract(exp_patterns_p1['firmado'])
df['firmado'] = df['firmado'].apply(lambda x: limpiaString(str(x)))
df['firmado'] = df['firmado'].replace({'nan':''})
#df['firmado'] != ""
df['firmado'] = df['firmado'].where(df['firmado'] != "", 0) # si diferente de vacio deja el valor de lo contrario pone 0
df['firmado'] = df['firmado'].mask(df['firmado'] != 0, 1) # si diferente de vacio pone 1

# 78.3
df['nombre2'] = df['1'].str.extract(exp_patterns_p1['nombre2'])
df['nombre2'] = df['nombre2'].apply(lambda x: limpiaString(str(x)))
df['nombre2'] = df['nombre2'].replace({'nan':''})

idx = df[df['nombre']==""].index 
df.loc[idx,'nombre'] = df.loc[idx, 'nombre2']


df2 = dar_formato_df(df)
df2.to_csv("resultadoPaso3.csv", index=False, sep=";")