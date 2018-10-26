from __future__ import unicode_literals, print_function
import pandas
import requests
from pathlib import Path

def getAnnotations(project_id):
    url = 'https://sysrev.com/web-api/project-annotations?project-id=' + str(project_id)
    response = requests.get(url)
    result = response.json()["result"]
    
    data = {}
    data['selection'] = [x['selection'] for x in result]
    data['annotation'] = [x['annotation'] for x in result]
    data['semantic_class'] = [x['semantic-class'] for x in result]
    data['external_id'] = [x['pmid'] for x in result]
    data['sysrev_id'] = [x['article-id'] for x in result]
    data['text'] = [x['context']['text-context'] for x in result]
    data['start'] = [x['context']['start-offset'] if 'start-offset' in x['context'].keys() else None for x in result]
    data['end'] = [x['context']['end-offset'] if 'end-offset' in x['context'].keys() else None for x in result]
    data['datasource'] = ['pubmed'] * len(result)

    df = pandas.DataFrame.from_dict(data)
    return df

def processAnnotations(project_id, label):
    response = requests.get('https://sysrev.com/web-api/project-annotations?project-id=' + str(project_id))
    SYSREV_DATA = response.json()
    annotations = [x for x in SYSREV_DATA['result'] if 'start-offset' in x['context'].keys()]

    def process_annotation(annotation):
        return [annotation["context"]["text-context"], {"entities": [(annotation["context"]["start-offset"],annotation["context"]["end-offset"],label)]}]

    processed_annotations = map(process_annotation, annotations)

    def combine_annotations(processed_annotations):
        combined_annotations = {}
        for text,entities in processed_annotations:
            if combined_annotations.get(text) is None:
                combined_annotations[text] = []
            combined_annotations[text].append(entities["entities"][0])
        for key in combined_annotations:
            combined_annotations[key] = list(set(combined_annotations[key]))            
        return combined_annotations

    combined_processed_annotations = combine_annotations(processed_annotations)
    final_json = []
    for k in combined_processed_annotations:
        final_json.append([k,{"entities":combined_processed_annotations[k]}])

    return final_json

def getModel(model_name):
    return pickle.loads(urllib.urlopen("https://s3.amazonaws.com/sysrev-model/".format(model_name)).read())