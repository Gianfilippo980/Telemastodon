"""Bot per il caricamento su Mastodon dell'immagine dell'ultimora del Televideo"""

import requests
import feedparser
import time
import threading
from Credenziali import mastodon as credenziali_mastodon
from PIL import Image
from io import BytesIO
from hashlib import md5 as hasher
from mastodon import Mastodon

#Indirizzi
indirizzo_immagine = "https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/16_9_page-101.png"
indirizzo_feed = 'https://www.televideo.rai.it/televideo/pub/rss101.xml'

#Periodi
#Gli sleep sono il tempo che passa fra due dowload dal web
sleep_rss = 20
sleep_immagine = 20
#Le finestre sono la finestra di tempo per la quale i due feed sono considerati "nuovi" dop essere cambiati
finestra_rss = 60
finestra_immagine = 60

class RSS:
    def __init__(self, intervallo_controlli : int, finestra_novità : int, indirizzo : str) -> None:
        self.indirizzo = indirizzo
        self.intervallo = intervallo_controlli
        self.finestra = finestra_novità
        self.ora_ultimo_cambio = time.gmtime()
        self._stop = threading.Event()
        self.thread = threading.Thread(target= self._ciclo)
        self.thread.start()

    def _ciclo(self) -> None:
        while not self._stop.is_set():
            self.aggiorna()
            time.sleep(self.intervallo)

    def aggiorna(self) -> None:
        try:
            self.lacnio = feedparser.parse(self.indirizzo).entries[0]
            ora_corrente = self.lancio.published_parsed
            if ora_corrente > self.ora_ultimo_cambio:
                self.ora_ultimo_cambio = ora_corrente
        except:
            print("Errore RSS")

    def titolo(self) -> str | None:
        #Restituisce il titolo dell'ultimo lancio RSS scaricato
        try:
            return self.lancio.title + "\n\n" + "#Ultimora"
        except:
            return None 
        
    def descrizione(self) -> str | None:
        #Restituisce il sommario dell'ultimo lancio RSS scaricato
        try:
            return self.lancio.summary
        except:
            return None
        
    def se_nuovo(self) -> bool:
        #Restituisce True se il lancio RSS è stato aggiornato entro la finestra di tempo
        return time.gmtime() - self.ora_ultimo_cambio < self.finestra

class Immagine:
    def __init__(self, indirizzo : str, intervallo_controlli : int, finestra_novità : int) -> None:
        self.indirizzo = indirizzo
        self.ora_ultimo_cambio = time.gmtime()
        self.intervallo = intervallo_controlli
        self.finestra = finestra_novità
        self._stop = threading.Event()
        self.thread = threading.Thread(target= self._ciclo)
        self.thread.start()
        self.immagine = None

    def _ciclo(self) -> None:
        while not self._stop.is_set():
            self.aggiorna()
            time.sleep(self.intervallo)

    def scarica_immagine(url) -> Image.Image | None:
        try:
            risposta = requests.get(url)
            risposta.raise_for_status()
            immagine = Image.open(BytesIO(risposta.content))
            return immagine
        except:
            print("Errore immagine")
            return None
    
    def aggiorna(self) -> None:
        nuova_immagine = self.scarica_immagine(self.indirizzo)
        if nuova_immagine is not None:
            self.ora_ultimo_cambio = time.gmtime()
            self.immagine = nuova_immagine

    def se_nuovo(self) -> bool:
        return time.gmtime() - self.ora_ultimo_cambio < self.finestra
    
    def immagine(self) -> Image.Image | None:
        try:
            return self.immagine
        except:
            return None

#Gestione Mastodon
mastodon = Mastodon(client_id = 'Telepython_client.secret')
mastodon.log_in([LOGIN], to_file= 'Telepython_utente.secret', scopes=['write'])

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
