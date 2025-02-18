"""Bot per il caricamento su Mastodon dell'immagine dell'ultimora del Televideo"""
#Questa versine del bot posta una nuova immagine solo se entrambi i feed sono stati aggiornati entro le rispettive finestre di tempo, per evitare di postare un'immagine vecchia con un titolo nuovo.

import requests
import feedparser
import time
import threading
from Credenziali import mastodon as credenziali_mastodon
from PIL import Image
from io import BytesIO
from hashlib import md5 as hasher
from mastodon import Mastodon
from Credenziali import mastodon as LOGIN

#Indirizzi
indirizzo_immagine = "https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/16_9_page-101.png"
indirizzo_feed = 'https://www.televideo.rai.it/televideo/pub/rss101.xml'

#Periodi Temporali
#Gli sleep sono il tempo che passa fra due dowload dal web
sleep_rss = 20
sleep_immagine = 20
sleep_post = 10
#Le finestre sono la finestra di tempo per la quale i due feed sono considerati "nuovi" dopo essere cambiati
finestra_rss = 600
finestra_immagine = 180
#Poiché alle volte l'immagine viene aggiornata nello stesso momento in cui il feed viene aggiornato, ma con ancora il precedente contenuto, si introduce un ritardo per l'apertura della finestra del feed RSS
ritardo_finestra_rss = 60

class RSS:
    def __init__(self, intervallo_controlli : int, finestra_novità : int, ritado_finestra: int, indirizzo : str) -> None:
        self.indirizzo = indirizzo
        self.sleep = intervallo_controlli
        self.finestra = finestra_novità
        self.ritardo_finestra = ritado_finestra
        self.ora_ultimo_cambio = time.gmtime()
        self._stop = threading.Event()
        self.thread = threading.Thread(target= self._ciclo)
        self.thread.start()
        self.lancio = None
        self.postato = True

    def _ciclo(self) -> None:
        while not self._stop.is_set():
            self.aggiorna()
            time.sleep(self.sleep)

    def aggiorna(self) -> None:
        try:
            self.lancio = feedparser.parse(self.indirizzo).entries[0]
            ora_corrente = self.lancio.published_parsed
            if ora_corrente > self.ora_ultimo_cambio:
                self.ora_ultimo_cambio = ora_corrente
                self.postato = False
        except:
            print("Errore RSS")

    def filtra_link(self, testo : str) -> str:
        #Rimuove i link dal testo, alle volte presenti nel sommario sotto la forma di <a href="...">...</a> e che di solito non portano da nessuna parte
        if "<a" in testo:
            inizio = testo.find("<a")
            fine = testo.find(">", inizio)
            testo = testo[:inizio] + testo[fine + 1:]
            inizio = testo.find("</a>")
            testo = testo[:inizio] + testo[inizio + 4:]
        return testo

    def titolo(self) -> str | None:
        #Restituisce il titolo dell'ultimo lancio RSS scaricato
        try:
            return self.lancio.title + "\n\n" + "#Televideo #Ultimora"
        except:
            return None 
        
    def descrizione(self) -> str | None:
        #Restituisce il sommario dell'ultimo lancio RSS scaricato
        try:
            testo = self.filtra_link(self.lancio.summary)
            return testo
        except:
            return None
        
    def se_nuovo(self) -> bool:
        #Restituisce True se il lancio RSS è stato aggiornato entro la finestra di tempo
        tempo = time.time() - 3_600 - time.mktime(self.ora_ultimo_cambio)
        controllo_tempo = tempo > self.ritardo_finestra and tempo < self.finestra + self.ritardo_finestra
        contenuto = self.lancio is not None
        return controllo_tempo and contenuto and not self.postato

class Immagine:
    def __init__(self, indirizzo : str, intervallo_controlli : int, finestra_novità : int) -> None:
        self.indirizzo = indirizzo
        self.ora_ultimo_cambio = time.time()
        self.intervallo = intervallo_controlli
        self.finestra = finestra_novità
        self._stop = threading.Event()
        self.thread = threading.Thread(target= self._ciclo)
        self.thread.start()
        self.immagine = None
        self.postato = True

    def _ciclo(self) -> None:
        while not self._stop.is_set():
            self.aggiorna()
            time.sleep(self.intervallo)

    def scarica_immagine(self) -> Image.Image | None:
        try:
            risposta = requests.get(self.indirizzo)
            risposta.raise_for_status()
            immagine = Image.open(BytesIO(risposta.content))
            return immagine
        except:
            print("Errore immagine")
            return None
    
    def aggiorna(self) -> None:
        nuova_immagine = self.scarica_immagine()
        if nuova_immagine is not None:
            if self.immagine is None:
                self.immagine = nuova_immagine
            if hasher(nuova_immagine.tobytes()).digest() != hasher(self.immagine.tobytes()).digest():
                self.ora_ultimo_cambio = time.time()
                self.immagine = nuova_immagine
                self.postato = False

    def se_nuovo(self) -> bool:
        tempo = time.time() - self.ora_ultimo_cambio < self.finestra
        contenuto = self.immagine is not None
        return tempo and contenuto and not self.postato


#Gestione Mastodon
mastodon = Mastodon(client_id = 'Telepython_client.secret')
mastodon.log_in(credenziali_mastodon.email, credenziali_mastodon.password, to_file= 'Telepython_utente.secret', scopes=['write'])

def posta_immagine(immagine, titolo, descrizione) -> None:
    bytes= BytesIO()
    immagine.save(bytes, format= 'PNG')
    media = mastodon.media_post(bytes.getvalue(), mime_type= 'image/png', description= descrizione)
    mastodon.status_post(titolo, media_ids= media, language= 'IT')

#Ciclo principale
rss = RSS(sleep_rss, finestra_rss, ritardo_finestra_rss, indirizzo_feed)
immagine = Immagine(indirizzo_immagine, sleep_immagine, finestra_immagine)

while True:
    if rss.se_nuovo() and immagine.se_nuovo():
        print("Posto")
        posta_immagine(immagine.immagine, rss.titolo(), rss.descrizione())
        rss.postato = True
        immagine.postato = True
    time.sleep(sleep_post)