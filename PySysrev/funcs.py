from __future__ import unicode_literals, print_function
import requests
import pandas
import json
import plac
import random
from pathlib import Path
import spacy
import io
import pprint

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

def processAnnotations(project_id, label, output_path):
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

    with open(output_path, 'w') as fout:
        json.dump(final_json, fout)

def trainAnnotations(input_path, output_dir):
    nlp = spacy.blank('en')  # create blank Language class

    model=None
    new_model_name='gene'
    #output_dir='sysrev_gene'
    n_iter=20
    training_data='training_data.json'
    label='GENE'
    max_steps_since_min=10

    with open(input_path) as f:
        TRAIN_DATA = json.load(f)

    if 'ner' not in nlp.pipe_names:
        ner = nlp.create_pipe('ner')
        nlp.add_pipe(ner)
    # otherwise, get it, so we can add labels to it
    else:
        ner = nlp.get_pipe('ner')

    ner.add_label(label)   # add new entity label to entity recognizer
    if model is None:
        optimizer = nlp.begin_training()
    else:
        # Note that 'begin_training' initializes the models, so it'll zero out
        # existing entity types.
        optimizer = nlp.entity.create_optimizer()

    # get names of other pipes to disable them during training
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != 'ner']
    min_loss = 5000.0
    steps_since_last_min = 0
    with nlp.disable_pipes(*other_pipes):  # only train NER
        for itn in range(n_iter):
            random.shuffle(TRAIN_DATA)
            losses = {}
            for text, annotations in TRAIN_DATA:
                nlp.update([text], [annotations], sgd=optimizer, drop=0.35,
                           losses=losses)
            steps_since_last_min += 1
            if losses["ner"] < min_loss:
                min_loss = losses["ner"]
                steps_since_last_min = 0
            print("current loss: {} | min_loss: {} | Steps since last min: {}".format(losses["ner"],min_loss,steps_since_last_min))    
            if steps_since_last_min > max_steps_since_min:
                print("Maximum steps since last min loss exceeded")
                break
    if output_dir is not None:
        output_dir = Path(output_dir)
        if not output_dir.exists():
            output_dir.mkdir()
        nlp.meta['name'] = new_model_name  # rename model
        nlp.to_disk(output_dir)