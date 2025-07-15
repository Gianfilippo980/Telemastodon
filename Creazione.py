from mastodon import Mastodon
Mastodon.create_app(client_name=    'Telepython', 
                    scopes=         ['write:statuses', 'write:media'],
                    api_base_url=   'https://mstdn.social',
                    to_file=       'Telepython_client.secret')