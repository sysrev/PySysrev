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
    data['start'] = [x['context']['start-offset'] if 'start-offset' in list(x['context'].keys()) else None for x in result]
    data['end'] = [x['context']['end-offset'] if 'end-offset' in list(x['context'].keys()) else None for x in result]
    data['datasource'] = ['pubmed'] * len(result)

    df = pandas.DataFrame.from_dict(data)
    return df

def processAnnotations(project_id, label):

    def remove_overlapping_entities(df):
        idx_to_remove = []
        for text_id in df.text.unique():
            all_ranges = []
            sub_df = df[df['text'] == text_id][['sysrev_id', 'text', 'start', 'end']]
            for index, row in sub_df.iterrows():
                r_start = int(row['start'])
                r_end = int(row['end'])
                if all([True if x not in all_ranges else False for x in range(r_start, r_end)]):
                    all_ranges.extend(list(range(r_start, r_end)))
                else:
                    idx_to_remove.append(index)
        return idx_to_remove

    df = getAnnotations(project_id)
    df = df.drop_duplicates(subset=['text', 'start', 'end'])
    df = df[(df['start'].notnull()) & (df['end'].notnull())]
    df = df[df['end'] - df['start'] < 50]
    df = df.reset_index(drop=True)
    overlapping_idx = remove_overlapping_entities(df)
    df = df.drop(df.index[overlapping_idx])
    annotations = df.to_dict('records')

    def process_annotation(annotation):
        return [annotation["text"], {"entities": [(int(annotation["start"]), int(annotation["end"]),label)]}]

    processed_annotations = list(map(process_annotation, annotations))

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
