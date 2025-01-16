from mastodon import Mastodon

mastodon= Mastodon(client_id = 'Telepython_client.secret')
url= mastodon.auth_request_url(scopes= ['write'])
print(url)
codice = input("Codice:")
mastodon.log_in(to_file= 'Telepython_utente.secret', code= codice, scopes= ['write'])