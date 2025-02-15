"""Bot per il caricamento su Mastodon dell'immagine dell'ultimora del Televideo"""

import requests
from PIL import Image
from io import BytesIO
import feedparser
import time
from mastodon import Mastodon
from Credenziali import mastodon as LOGIN

#Gestione immagine
indirizzo_immagine = "https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/16_9_page-101.png"
indirizzo_feed = 'https://www.televideo.rai.it/televideo/pub/rss101.xml'

def scarica_immagine(url):
    try:
        risposta = requests.get(url)
        risposta.raise_for_status()
        immagine = Image.open(BytesIO(risposta.content))
        return immagine
    except:
        print("Errore di rete")
        return None

def apri_rss(url_rss):
    try:
        feed = feedparser.parse(url_rss)
        return feed
    except:
        print("Errore RSS")
        return None

def ora_ultima(feed):
    try:
        return feed.entries[0].published_parsed
    except:
        return None

#Gestione Mastodon
mastodon = Mastodon(client_id = 'Telepython_client.secret')
mastodon.log_in(LOGIN.email, LOGIN.password, to_file= 'Telepython_utente.secret', scopes=['write'])

def posta_immagine(titolo, descrizione):
    media = mastodon.media_post('ultim_ora.png', description= descrizione)
    mastodon.status_post(titolo, media_ids= media, language= 'IT')

#Loop
ora_precedente = time.gmtime()
while True:
    feed_rss = apri_rss(indirizzo_feed)
    if feed_rss is None:
        time.sleep(10)
        continue
    time.sleep(20)
    #Ritardo qui per essere sicuro di prendere l'immagine dopo l'aggiornamento

    ora_corrente = ora_ultima(feed_rss)
    if ora_corrente is None:
        continue  
    if ora_corrente > ora_precedente:
        immagine_corrente = scarica_immagine(indirizzo_immagine)
        if immagine_corrente is None:
            #In caso di errore attende un altro ciclo
            continue
        try:
            titolo = feed_rss.entries[0].title + "\n\n" + "#Ultimora"
            descrizione = feed_rss.entries[0].summary
        except:
            continue
        ora_precedente = ora_corrente
        immagine_corrente.save("ultim_ora.png")
        posta_immagine(titolo, descrizione)
