

server = json.load(open('server-results.sarif'))
[v for v in server['runs'][0]['results'] if 'Fixed Version' in v['message']['text']]
