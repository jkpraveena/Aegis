def test_health(client):assert client.get('/health').json()['status']=='ok'
def test_analysis_without_seeded_facts(client):
    r=client.post('/api/v1/analyze',json={'query':'Summarise the current business situation.','include_retrieval':True,'include_analysis':True})
    assert r.status_code==200,r.text
    data=r.json();assert data['status']=='completed';assert data['findings']==[]
    assert 'No dataset uploaded' in ' '.join(data['warnings'])
    assert client.get('/api/v1/runs/'+data['run_id']).status_code==200
def test_query_validation(client):assert client.post('/api/v1/analyze',json={'query':'bad'}).status_code==422
def test_run_history(client):
    client.post('/api/v1/analyze',json={'query':'Show the current uploaded data summary.','include_retrieval':False})
    r=client.get('/api/v1/runs');assert r.status_code==200 and len(r.json())==1
def test_document_upload_and_retrieval(client):
    r=client.post('/api/v1/documents',files={'file':('policy.txt',b'Employees must encrypt confidential customer records before external transfer.','text/plain')})
    assert r.status_code==200,r.text
    a=client.post('/api/v1/analyze',json={'query':'What must employees do before external transfer of customer records?','include_retrieval':True,'include_analysis':False})
    assert a.status_code==200,a.text
    assert len(a.json()['evidence'])==1
    assert a.json()['evidence'][0]['source']=='policy.txt'
def test_csv_upload_and_analysis(client):
    csv=b'quarter,revenue,cost\nQ1,100,70\nQ2,150,90\n'
    r=client.post('/api/v1/datasets',files={'file':('sales.csv',csv,'text/csv')})
    assert r.status_code==200,r.text;dataset_id=r.json()['id']
    a=client.post('/api/v1/analyze',json={'query':'Analyse revenue and cost trends.','dataset_id':dataset_id,'include_retrieval':False,'include_analysis':True})
    assert a.status_code==200,a.text
    assert any('Analysed 2 rows' in x for x in a.json()['findings'])
