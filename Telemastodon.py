"""Bot per il caricamento su Mastodon dell'immagine dell'ultimora del Televideo"""
# Questa versine del bot usa l'OCR per riconosce l'ora dell'immagine e la confronta con l'ora dell'ultima notizia RSS, se le due ore coincidono entro una finestra, il bot posta l'immagine e il sommario della notizia su Mastodon

import re
import requests
import feedparser
import time
from PIL import Image
import pytesseract
from io import BytesIO
from mastodon import Mastodon
from Credenziali import mastodon as credenziali_mastodon


#Indirizzi
indirizzo_immagine = "https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/16_9_page-101.png"
indirizzo_feed = 'https://www.televideo.rai.it/televideo/pub/rss101.xml'

#Periodi Temporali
sleep = 20
finestra = 120

class RSS:
    def __init__(self, indirizzo : str) -> None:
        self.indirizzo = indirizzo
        self.ora = time.localtime()
        self.lancio = None
        self.nuovo = False

    def aggiorna(self) -> time.struct_time:
        try:
            nuovo_lancio = feedparser.parse(self.indirizzo).entries[0]
            #Aggiunge un'ora per il fuso orario
            ora_lancio = time.localtime(time.mktime(nuovo_lancio.published_parsed) + 3_600)
            if ora_lancio > self.ora:
                self.ora = ora_lancio
                self.lancio = nuovo_lancio
                self.nuovo = True
                print("ora rss:     ", ora_lancio)
        except:
            print("Errore RSS")
        return self.ora

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

class Immagine:
    def __init__(self, indirizzo : str) -> None:
        self.indirizzo = indirizzo
        self.ora = time.localtime()
        self.immagine = None
        self.nuovo = False

    def scarica_immagine(self) -> Image.Image | None:
        try:
            risposta = requests.get(self.indirizzo)
            risposta.raise_for_status()
            immagine = Image.open(BytesIO(risposta.content))
            return immagine
        except:
            print("Errore immagine")
            return None
    
    def aggiorna(self) -> time.struct_time:
        nuova_immagine = self.scarica_immagine()
        if nuova_immagine is not None:
            nuova_ora = self.riconosci_orario(nuova_immagine)
            if nuova_ora is not None and nuova_ora > self.ora:
                self.immagine = nuova_immagine
                self.ora = nuova_ora
                self.nuovo = True
                print("ora immagine:", nuova_ora)
        return self.ora

    def riconosci_orario(self, immagine : Image) -> time.struct_time | None:
        if immagine is None:
            return None
        zona_orario = immagine.crop((22, 24, 121, 55))
        testo = pytesseract.image_to_string(zona_orario, config='--psm 7')
        # Validazione dei dati OCR
        testo = re.sub(r'[^0-9.]', '', testo)
        testo = testo.split('.')
        if len(testo) == 2:
            # Alle volte l'OCR confonde uno zero con un otto o con un 9 e restituisce un orario impossibile, questo succede soprattutto con le ore, che a volte hanno una sola cifra
            orario = [str(time.localtime().tm_hour), str(time.localtime().tm_min)]
            # Controlliamo le ore
            if int(testo[0]) - int(orario[0]) > 1:
                if len(testo[0]) < len(orario[0]):
                    testo[0] = '0'+ testo[0]                  
                for carattere_OCR, carattere_orario in zip(testo[0], orario[0]):
                    if carattere_OCR != carattere_orario:
                        if carattere_OCR == '8' or carattere_OCR == '9' and carattere_orario == '0':
                            testo[0] = orario[0]
                            break  
            # Per i minuti il problema pricipale è che, alle volte, appare un 77
            if int(testo[1]) > 59:
                testo[1] = time.localtime().tm_min
            
            orario_testo = [int(numero) for numero in testo]
            if orario_testo[0] >0 and orario_testo[0] < 24 and orario_testo[1] >= 0 and orario_testo[1] < 60:
                data = ''
                for t in time.localtime()[:3]:
                    data += str(t) + '.'
                return time.strptime(data + testo[0] + '.' + testo[1], "%Y.%m.%d.%H.%M")
        else:
            print("Errore orario")
            return None

#Gestione Mastodon
mastodon = Mastodon(client_id = 'Telepython_client.secret')
mastodon.log_in(credenziali_mastodon.email, credenziali_mastodon.password, to_file= 'Telepython_utente.secret', scopes=['write'])

def posta_immagine(immagine, titolo, descrizione) -> None:
    bytes= BytesIO()
    immagine.save(bytes, format= 'PNG')
    media = mastodon.media_post(bytes.getvalue(), mime_type= 'image/png', description= descrizione)
    mastodon.status_post(titolo, media_ids= media, language= 'IT')

#Ciclo principale
rss = RSS(indirizzo_feed)
immagine = Immagine(indirizzo_immagine)

while True:
    if rss.nuovo and immagine.nuovo and time.mktime(rss.ora) - time.mktime(immagine.ora) < finestra:
        print("Posto")
        posta_immagine(immagine.immagine, rss.titolo(), rss.descrizione())
        rss.nuovo = False
        immagine.nuovo = False
    time.sleep(sleep)