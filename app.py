from flask import Flask, redirect, url_for, render_template, request
import PyPDF2 
import fitz
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar,LTLine,LAParams
import pdfminer
from math import ceil
from pikepdf import Pdf
import numpy as np
import pandas as pd
import re



# WSGI Application
app = Flask(__name__)

file = ''

# Decorator
@app.route('/')
def welcome():
    return render_template('index_main.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/file_view', methods=['POST'])
def file_view():
    global file
    file = str(request.form['filename'])
    return render_template('filepage.html', file_name = file)

@app.route('/check')
def check():
    return render_template('checks.html')

@app.route('/result1')
def result():
    try:
        PyPDF2.PdfFileReader(open(file, "rb"))
    except PyPDF2.errors.PdfReadError:
        return render_template('result.html', result1 = "invalid PDF file")
    else:
        return  render_template('result.html', result1 = "valid PDF file")
      
@app.route('/result2')
def pdf_pass():
    doc = PyPDF2.PdfFileReader(file)
    if doc.isEncrypted == 'True':
        return render_template('result.html', result2 = 'File is password protected')
    else:
        return render_template('result.html', result2 = 'File is not password protected')

@app.route('/result3')
def pdf_version():
    doc = PyPDF2.PdfFileReader(file)
    doc.stream.seek(0)
    return render_template('result.html', result3 = 'PDF Version : {}, PDF No. of Pages : {}'.format(doc.stream.readline()[1:8], doc.getNumPages()))

@app.route('/result4')
def pdf_dimension():
    pdf = PyPDF2.PdfFileReader(file,"rb")
    p = pdf.getPage(1)

    w_in_user_space_units = p.mediaBox.getWidth()
    h_in_user_space_units = p.mediaBox.getHeight()
    
    w = float(p.mediaBox.getWidth()) * 0.352
    h = float(p.mediaBox.getHeight()) * 0.352

    p.mediaBox.setUpperRight((596.59, 843.75))
    
    new_w = float(p.mediaBox.getWidth()) * 0.352
    new_h = float(p.mediaBox.getHeight()) * 0.352
    
    if w!=210 and h!=297:
        return render_template('result.html', result4 = 'pdf dimension is not valid: {}, {}'.format(ceil(w), ceil(h)))
    else :
        return render_template('result.html', result4 = 'Valid PDF Dimension : {}, {}'.format(ceil(new_w), ceil(new_h)))

@app.route('/result5')
def pdf_fs_fn():
    
    Extract_Data=[]

    for page_layout in extract_pages(file):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    for character in text_line:
                        if isinstance(character, LTChar):
                            Font_size=character.size
                            Font_name=character.fontname
                Extract_Data.append([(element.get_text()), Font_size, Font_name,])
    df = pd.DataFrame(Extract_Data, columns=['Page_no', 'Fontsize', 'Fontname', ])
    df = df[df['Page_no'].map(lambda x: x.startswith('Page'))]
    df['Page_no']=df['Page_no'].str[0:-1]
    # df.set_index('Page_no', inplace=True)
    return render_template('result.html', column_names=df.columns.values, row_data=list(df.values.tolist()),
                           link_column="Page_no", zip=zip)
    

@app.route('/result6')
def fetching_bookmark():
    reader = PyPDF2.PdfFileReader(file)
    
    def bookmark_list(bookmark_dict):
        result = {}
        for item in bookmark_dict:
            if isinstance(item, list):
                # recursive call
                result.update(bookmark_list(item))
            else:
                try:
                    result[reader.getDestinationPageNumber(item)+1] = item.title
                except:
                    pass
        return result
    
    def bookmark_destination(bookmark_dest):
        dct = {}
        for i in range(1, reader.getNumPages()+1):
            page_no = reader.pages[i-1]
            page_text = page_no.extract_text()
            results = re.findall(r'Form:([A-Za-z\t .]+)', page_text)
            dct[i] = results
        return dct
    
    bookmarks = bookmark_list(reader.getOutlines())
    bookmark_data = pd.DataFrame(bookmarks.values(), index=bookmarks.keys(), columns=['Bookmarks'])
    bookmark_data = bookmark_data.drop(index=0)
    lst_index = bookmark_data.index.to_list()

    
    bookmark_d = bookmark_destination(reader)
    bookmark_d = pd.DataFrame(bookmark_d.values(), index=bookmark_d.keys(), columns=['Destination'])
    bookmark_d = bookmark_d.fillna(' none')
    
    df = bookmark_data.join(bookmark_d, how='right')
    
    bk_marks=[]
    dst=[]
    correct_path=[]

    for i in range(len(lst_index)):
        
        if i==(len(lst_index)-1):
            for k in range(lst_index[i],lst_index[i]+1):
   
                if re.match(df['Destination'][k][1:], df['Bookmarks'][lst_index[i]]):
                    bk_marks.append(df['Bookmarks'][lst_index[i]])
                    dst.append(df['Destination'][k][1:])
                    correct_path.append('True')
                else:
                    bk_marks.append(df['Bookmarks'][lst_index[i]])
                    dst.append(df['Destination'][k][1:])
                    correct_path.append('False')
        else:
            for k in range(lst_index[i],lst_index[i+1]):
    
                if re.match(df['Destination'][k][1:], df['Bookmarks'][lst_index[i]]):
                    bk_marks.append(df['Bookmarks'][lst_index[i]])
                    dst.append(df['Destination'][k][1:])
                    correct_path.append('True')
                else:
                    bk_marks.append(df['Bookmarks'][lst_index[i]])
                    dst.append(df['Destination'][k][1:])
                    correct_path.append('False')
                    
    df_main = pd.DataFrame(
    {'Bookmarks': bk_marks,
     'Destination': dst,
     'correct_path': correct_path
    })
    
    # df_main.set_index('Bookmarks', inplace=True)
    
    return render_template('result.html', column_names=df_main.columns.values, row_data=list(df_main.values.tolist()),
                           link_column="Bookmarks", zip=zip)

@app.route('/result7')
def pdf_links():
    
    result = []

    with fitz.open(file) as my_pdf_file:
        for page_number in range(1, len(my_pdf_file)+1):
            page = my_pdf_file[page_number-1]
            for link in page.links():
                if "uri" in link and 'from' in link:
                    url = link["uri"]
                    form = link['from']
                    a = form.x0, form.y0, form.x1, round(form.y1)+1
                    a = page.get_textbox(a)
                    result.append([page_number, a, url])
    df = pd.DataFrame(result, columns=['Page_no', 'Name', 'Links'])
    # df.set_index('Page_no', inplace=True)
    
    return render_template('result.html', column_names=df.columns.values, row_data=list(df.values.tolist()),
                           link_column="Page_no", zip=zip)




if __name__=='__main__':
    app.run(debug=True)
    