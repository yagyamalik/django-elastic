from django.shortcuts import render
from elasticsearch import Elasticsearch, helpers
import configparser
import io
import os
import requests
from django.conf import settings
from docx import Document
from polls.forms import UploadDocumentForm
from django.http import HttpResponse
import datetime

config = configparser.ConfigParser()
config.read('/Users/yagyamalik/Documents/Avasant/django-elastic/mysite/polls/example.ini')
##Create an instance of the elasticsearch client
es = Elasticsearch(
    cloud_id=config['ELASTIC']['cloud_id'],
    http_auth=(config['ELASTIC']['user'], config['ELASTIC']['password'])
)
#define index name
index_name = 'project1'
# Create your views here.
def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")

#this function creates an index in elasticsearch
def initiate_index(request):
    #this is how we define schema in elsaticsearch
    es.indices.create(index=index_name, body={
    'mappings': {
        'properties': {
            'title': {'type': 'text'},
            'content': {'type': 'text'},
            'date':{'type': 'date'},
                }
            }
        }
    )
    return HttpResponse("Index created")

#This function sends PDFs to OCR endpoint to get text. If the file provifeid is a docx file, it extracts text from the file.
def extract_text(file_path):
    if file_path.endswith('.docx'):
        doc = Document(file_path)
        text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    elif file_path.endswith('.pdf'):
        response = requests.post('https://compute-service-dev-bkj4clsvbq-em.a.run.app/ocr/extract_text', files={'document': open(file_path, 'rb')}).json()
        text = response['extracted_text']
    return text

#This function uploads a document to the elasticsearch index
def upload_document(request):
    if request.method == 'POST':
        form = UploadDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.cleaned_data['document']
            file_path = os.path.join(settings.MEDIA_ROOT, document.name)
            with io.open(file_path, 'wb') as f:
                for chunk in document.chunks():
                    f.write(chunk)
            text = str(extract_text(file_path))
            upload_date = datetime.datetime.now().strftime("%Y-%m-%d")
            print(text)
            #This is how we add a document to the index
            es.index(index=index_name, document={'title': str(document.name), 'content': text, 'date': upload_date})
            es.indices.refresh(index=index_name)
            os.remove(file_path)
    else:
        form = UploadDocumentForm()
    return render(request, 'polls/upload_document.html', {'form': form})

#This function searches the elasticsearch index for a query and returns the results
def search(request):
    query = request.GET.get('query', '')
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)
    body = {
        'query': {
            'bool': {
                'must': {
                    'match': {
                        'content': query
                    }
                }
            }
        },
        'highlight': {
            'fields': {
                'content': {}
            }
        }
    }
    if start_date and end_date:
        body['query']['bool']['filter'] = {
            'range': {
                'date': {
                    'gte': start_date,
                    'lte': end_date
                }
            }
        }
    results = es.search(index=index_name, body=body)
    hits = results['hits']['hits']
    for hit in hits:
        #We are explicitly adding these fields to the hits because we want to display them in the template
        hit['name'] = hit['_source']['title']
        hit['upload_date'] = hit['_source']['date']
        hit_highlight = hit['highlight']['content'][0]
        hit['highlight'] = hit_highlight

    context = {
        'hits': hits
    }
    print(hits)
    return render(request, 'polls/search.html', context)