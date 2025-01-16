from mastodon import Mastodon
Mastodon.create_app('Telepython', scopes= ['write'],
                    api_base_url= 'https://mstdn.social',
                    to_file= 'Telepython_client.secret')