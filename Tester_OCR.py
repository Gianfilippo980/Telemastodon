"""Programma per verificare il funzionamento dell'OCR sul televideo"""

import time
from io import BytesIO
import re

import pytesseract
from PIL import Image
import requests

indirizzo_immagine: str = ("https://www.televideo.rai.it/televideo/pub/tt4web/"
                           "Nazionale/16_9_page-101.png")


def scarica_immagine(
    indirizzo: str = indirizzo_immagine
) -> Image.Image | None:
    """Restituisce l'immagine se riesce a scaricarla, o None se fallisce."""
    try:
        risposta = requests.get(indirizzo, timeout= 60)
        risposta.raise_for_status()
        immagine = Image.open(BytesIO(risposta.content))
        return immagine
    except requests.exceptions.RequestException as eccezione:
        print("Errore connessione", eccezione)
        return None


def riconosci_testo(zona_orario: Image.Image) -> str:
    """Esegue l'OCR e restituisce il testo, mi aspetto che l'immagine contenga
    una sola riga di testo in italiano."""
    # Converto in Grigio
    zona_orario = zona_orario.convert("L")
    # Converto in Binario
    zona_orario = zona_orario.point(lambda p: 255 if p > 127 else 0)
    testo = pytesseract.image_to_string(zona_orario, lang='ita',
                                        config='--psm 7')
    testo = re.sub(r'[^0-9.]', '', testo)
    return testo


def orario(testo: str) -> time.struct_time | None:
    """Restituisce l'orario ricavato dalla stringa in ingresso, assume il
    formato %H.%M, se il riconoscimento fallisce, restituisce None."""
    try:
        ora = time.strptime(testo, "%H.%M")
        return ora
    except ValueError:
        print("Errore formato orario")
        return None

def salva(testo: str) -> None:
	"""Apre un file per con nome AAAA-MM-GG.out, in base alla data, se non
	esiste lo crea, e salva la stringa inviata."""
	orario = time.localtime()
	nome_file = (str(orario.tm_year) + "-" + str(orario.tm_month) +
					"-" + str(orario.tm_mday) + ".out")
	with open(nome_file, a) as file:
		file.write((testo + "\lf"))


def main() -> None:
    """Periodicamente scarica l'ultimora del televideo, riconosce l'orario
    dall'immagine e lo stampa insieme a quello del computer, se i due valori
    hanno ore diverse, salva il ritaglio di immagine usato per l'OCR per
    successivi esami."""
    testo = ''
    while True:
        immagine = scarica_immagine(indirizzo_immagine)
        if immagine is not None:
            # Ritaglio
            zona_orario = immagine.crop((24, 28, 119, 53))
            nuovo_testo = riconosci_testo(zona_orario)
            orario_ricezione = time.localtime()
            ora_vera = (str(orario_ricezione.tm_hour) + ':'
                        + str(orario_ricezione.tm_min))
            if nuovo_testo != testo:
				log = ora_vera + "->" + nuovo_testo
                print(log)
				salva (log)
                testo = nuovo_testo
                ora_testo = orario(testo)
                if ora_testo is not None:
                    if ora_testo.tm_hour != orario_ricezione.tm_hour:
						# Se l'orario ricostruito è diverso da quello di
						# ricezione, si salva l'immaigne che potrebbe essere
						# stata ricostruita male.
                        zona_orario.save((ora_vera + '.png'))
				else:
					# Se l'orario non è stato riconosciuto dall'immagine,
					# salvo l'immagine che potrebbe essere stata ricostruita
					# male.
					zona_orario.save((ora_vera + '.png'))
        time.sleep(60)


if __name__ == '__main__':
    main()
