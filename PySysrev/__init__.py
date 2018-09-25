import requests
import pandas

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
