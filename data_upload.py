
import os
import validators
import ibm_db
import ibm_db_dbi
import re
from selenium import webdriver
from bs4 import BeautifulSoup
import pdfplumber
from pdf2image import convert_from_path
from pytesseract import image_to_string
import pandas as pd
import difflib
from math import isnan
import sys


QUESTION_WORDS = ["What","Who","Where","How","Why","When","Is","Are","Should","Shall","Will","Can","do","Does"]

#Common functions
def isQues(text):
    first_word = text.split()[0].lower()
    words = text.split()
    ques_word = ""
    for wd in words:
        all_alpha = True
        for ch in wd:
            if not(64<=ord(ch)<=90 or 97<=ord(ch)<=122):
                all_alpha = False
                break
        if all_alpha:
            if wd.lower() in ['question','ques','que','q']:
                continue
            else:
                ques_word = wd
                break
        
    if first_word.endswith('.') and first_word[:-1].isdigit():
        return True
    elif first_word.startswith('q') and (first_word.endswith('.') or first_word.endswith(':')):
        return True
    elif text.endswith('?'):
        return True
    if ques_word in QUESTION_WORDS:
        return True
    else:
        return False

# URL Handler Code
def Scrape_html(url):
    
    opts = webdriver.FirefoxOptions()
    opts.headless = True
    browser = webdriver.Firefox(options=opts)
    
    browser.get(url)
    html_content = browser.page_source
    browser.quit()
    
    contents = html_content
    soup = BeautifulSoup(contents,'html.parser')
    text = soup.find_all(text=True)
    blacklist = ['[document]','noscript','header','html','meta','head', 'input','script','div']
    text = [str(t).strip() for t in text if t.parent.name not in blacklist]
    text = [t for t in text if t!='' and t[0].isalnum() and '="' not in t]
    text = [re.sub(r'\n','',t) for t in text]
    text = [re.sub(r'  +',' ',t) for t in text]
    ques = []
    ans = []
    ques_start= False
    ans_text = ''
    for ti,t in enumerate(text):
        if ques_start:
            ans_text += str(t) + '\n'
            if ti<len(text)-1 and isQues(text[ti+1]):
                ans.append(ans_text)
                ques_start = False
            
        else:
            if isQues(t):
                if str(t).split()[0].endswith('.') and str(t).split()[0][:-1].isdigit():
                    t = ' '.join(str(t).split()[1:])
                else:
                    t = str(t)
                ques_start = True
                ques.append(t)
                ans_text = ''
            else:
                continue
    ans.append(ans_text.split('\n')[0]) 
    faqs = []
    if len(ques) == len(ans):
        for ri in range(len(ques)):
            faqs.append(['',ques[ri],None,None,ans[ri]])
            
    return faqs

#Searchable PDF Handler Code
def Scrape_pdf(pdf_file):
    pdf = pdfplumber.open(pdf_file)
    text = ''
    
    for i in range(len(pdf.pages)):
        page = pdf.pages[i] # because the lib captures data page wise
        text_page = page.extract_text()
        lines_page = text_page.split('\n')
        for line in lines_page:
            line = line.strip()
            line = re.sub(r'  +',' ',line)
            if line == '':
                continue
            elif line.endswith('.') or line.endswith('?'):
                text += line+'\n'
            else:
                text += line+' '
    
    text = [t for t in text.split('\n') if t.strip()!='']
    if len(text)<10:
        text = ''
        pages = convert_from_path(pdf_file)
        for i in range(len(pages)):
            text_page = image_to_string(pages[i],config='--psm 6 --oem 2')
            lines_page = text_page.split('\n')
            for line in lines_page:
                line = line.strip()
                line = re.sub(r'  +',' ',line)
                if line == '':
                    continue
                elif line.endswith('.') or line.endswith('?'):
                    text += line+'\n'
                else:
                    text += line+' '
        
        text = [t for t in text.split('\n') if t.strip()!='']
    
    ques = []
    ans = []
    ques_start= False
    ans_text = ''
    
    for ti,t in enumerate(text):
        if ques_start:
            ans_text += str(t) + '\n'
            if ti<len(text)-1 and isQues(text[ti+1]):
                ans.append(ans_text)
                ques_start = False
    
        else:
            if isQues(t):
                ques_start = True
                ques.append(str(t))
                ans_text = ''
            else:
                continue
    ans.append(ans_text.split('\n')[0])
    
    pdf.close()
    faqs = []
    if len(ques) == len(ans):
        for ri in range(len(ques)):
            faqs.append(['',ques[ri],None,None,ans[ri]])
            
    return faqs

#CSV/Excel Handler Code
def Scrape_sheet(input_file):
    df = None
    faqs = []
    try:
        url_file = input_file
        file_name = './' + url_file
        df = pd.read_excel(file_name)
        print("\n  file_name \n")
        print(type(file_name))
        print(file_name)
        data_src = "Excel"
    except:
        try:
            df = pd.read_csv(input_file)
            data_src = "CSV"
        except:
            print("Invalid Input File")
            data_src = "Invalid"
    
    intents = []
    intent_examples = []
    entities = []
    entity_values = []
    responses = []
    columns = ["Intent","IntentExamples","Entities","EntityValues","Responses","Questions","Answers","Utterances"]
    
    if df is not None:
        for ci,col in enumerate(df.columns):
            col_mapped = difflib.get_close_matches(col,columns,n=1,cutoff=0.8)
            print(col,col_mapped)
            if col_mapped == []:
                continue
            else:
                col_mapped = col_mapped[0]
                if col_mapped == 'Intent':
                    intents = list(df[col])
                elif col_mapped in ["IntentExamples","Questions","Utterances"]:
                    intent_examples = list(df[col])
                elif col_mapped == "Entities":
                    entities = list(df[col])
                elif col_mapped == "EntityValues":
                    entity_values = list(df[col])
                elif col_mapped in ["Responses","Answers"]:
                    responses = list(df[col])
                else:
                    continue

        if len(intent_examples)!=0 and len(responses)!=0:
            len_faqs = len(intent_examples)
            for li in range(len_faqs):
                try:
                    intent = intents[li]
                    if type(intent)!=str and isnan(intent):
                        print("11")
                        intent = ''
                except:
                    intent = ''
                que = intent_examples[li]
                try:
                    entity = entities[li]
                    if type(entity)!=str and isnan(entity):
                        entity = None
                except:
                    entity = None
                try:
                    entity_value = entity_values[li]
                    if type(entity_value)!=str and isnan(entity_value):
                        entity_value = None
                except:
                    entity_value = None
                res = responses[li]
#                print([li,intent,que,entity,entity_value,res])
                faqs.append([intent,que,entity,entity_value,res])
            
    return faqs, data_src

#data prep
def dataPrep(input_arg):
    print("\nI am in dataPrep function...\n") 
    if validators.url(input_arg):
        faqs = Scrape_html(input_arg)
        data_src = "URL"
    else:
        ext = os.path.splitext(input_arg)[-1].lower()
        if ext in ['.pdf']:
            faqs = Scrape_pdf(input_arg)
            data_src = "PDF"
        else:
            faqs, data_src = Scrape_sheet(input_arg)
    
    print("Extracted",len(faqs),"Q/A from",data_src,"source")
    
    print("Connecting to Database...") 
    ibm_db_conn = ibm_db.connect("DATABASE="+"BLUDB"+";HOSTNAME="+"dashdb-txn-sbox-yp-dal09-11.services.dal.bluemix.net"+";PORT="+"50000"+";PROTOCOL=TCPIP;UID="+"dnr61151"+";PWD="+"1l2mz7b+hclkfnj0"+";", "","")
    conn = ibm_db_dbi.Connection(ibm_db_conn)
    
    
    print("\nPushing to Database...\n")  
    table_name = "FAQ_DATAPREP" 
    
    print("\nDeleting existing data from",table_name)
    query = "DELETE FROM " + table_name
    stmt = ibm_db.exec_immediate(ibm_db_conn, query)
    
    print("\nPushing the new data\n")
     
    for faq in faqs:
        query = "INSERT INTO " + table_name + " VALUES('"+faq[0]+"','"+faq[1]+"',"
        if faq[2] is None:
            query += "NULL,"
        else:
            query += "'"+faq[2]+"',"
        if faq[3] is None:
            query += "NULL,"
        else:
            query += "'"+faq[3]+"',"
        query += "'"+faq[4]+"')"
        stmt = ibm_db.exec_immediate(ibm_db_conn, query)
    print("Data Ingested to", table_name)
    conn.close()
    return "Success"
    

from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
import pandas as pd

app=Flask(__name__)

@app.route('/upload')
def upload_file():
   return render_template('upload.html')

@app.route('/uploader', methods = ['GET', 'POST'])
def uploader():
   if request.method == 'POST':
      f = request.files['file']
      f.save(secure_filename(f.filename))
      f_name = f.filename
      a = dataPrep(f_name)
      return 'file uploaded successfully and loaded into databases'
  
@app.route("/export", methods=['GET'])
def export_records():
    return 

if __name__ == "__main__":
    app.run()
    