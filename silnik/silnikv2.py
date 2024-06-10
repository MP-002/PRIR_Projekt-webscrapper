import asyncio
from concurrent.futures import ProcessPoolExecutor
from bs4 import BeautifulSoup
from redis import Redis
import requests
import time
from urllib.parse import urljoin
import json

def sync_getUrls(): #funkcja pobiera adresy stron do przeszukania z bazy danych
    r = Redis(host='172.17.0.2', port=6379, db=0) # połączenie z bazą redis
    urls = r.lrange('urls', 0, -1) # pobranie listy 'urls'
    return [element.decode('utf-8') for element in urls] # f zwraca zdekodowaną listę adresów url

def sync_getTargets(): #funkcja pobiera elementy stron do znalezienia z bazy danych
    r = Redis(host='172.17.0.2', port=6379, db=0) # połączenie z bazą redis
    targets = r.lrange('targets',0,-1) # pobranie listy 'targets'
    return [element.decode('utf-8') for element in targets] # f zwraca zdekodowaną listę celów poszukiwań

def sync_pushData(results, urls, targets): # funkcja wysyła pozyskane dane do bazy 
    r = Redis(host='172.17.0.2', port=6379, db=0) # połączenie z bazą redis
    r.set('results', json.dumps(results)) # wysłanie wyników do bazy, zapis w liście 'results'
    r.lpush('urlsH', json.dumps(urls)) # wysłanie adresów url do bazy, zapis w liście 'urlsH'
    r.lpush('targetsH', json.dumps(targets))# wysłanie celów poszukiwań do bazy, zapis w liście 'targetsH'
    r.lpush('resultsH', json.dumps(results))# wysłanie wyników do bazy, zapis w liście 'resultsH'
#listy urlsH,targetsH,resultsH wykorzystywane są do przechowywania historii poszukiwań

async def async_fetch_content(url):#asynchroniczna funkcja pobiera zawartość strony z podanego url
    loop = asyncio.get_event_loop()#stworzenie pętli zdarzeń
    response = await loop.run_in_executor(None, requests.get, url)#czekanie na pobranie strony
    if response.status_code == 200:#jeśli poprawnie pobrano stronę
        return response.text#zwraca zawartość strony jako tekst
    else:
        return None # w przeciwnym wypadku nie zwraca nic

async def async_parse_content(url, targets):#funkcja parsuje pobraną stronę
    content = await async_fetch_content(url)#oczekiwanie na pobranie strony
    if not content:
        print('Nie udało się pobrać strony')#komunikat w razie niepowodzenia
        return []

    results = []#lista na wyniki
    soup = BeautifulSoup(content, 'html.parser')#parsowanie strony
    for target in targets:#dla każdego elementu na liście
        links = soup.find_all(target)#znajdź elementy
        target_results = []#podlista na znalezione elementy
        for link in links:#dla znalezionych elementow na liście
            if target == 'a' and link.get('href'):#jeśli cel to hiperłącze,znaleziony znacznik to href
                href = link.get('href')#zapis do zmiennej
                if href.startswith(('http://', 'https://')):#jeśli link jest absolutny
                    if href not in target_results:#i nie został jeszcze zapisany
                        target_results.append(href)#zapisz na liście
                else:#jeśli nie
                    target_results.append(urljoin(url, href))#stwórz adres za pomocą url i zapisz go
            elif(target=='img'):#jeśli cel to obraz
                        if link.get('src'):#jeśli znaleziono źródło
                            if link.get('src').startswith(('http://', 'https://')):#gdy link jest pełny
                                if link.get('src').find('.png'):#gdy obraz zapisano jako png
                                    index = link.get('src').find('.png')#zapisanie pozycji
                                    if index != -1:#jeśli za pozycją znajdują się dane
                                        target_results.append(link.get('src')[:index + 4])#skróć adres obrazu
                                if link.get('src').find('.jpg'):#gdy obraz zapisano jako jpg
                                    index = link.get('src').find('.jpg')#zapisanie pozycji
                                    if index != -1:#jeśli za pozycją znajdują się dane
                                        target_results.append(link.get('src')[:index + 4])#skróć adres obrazu
                                if link.get('src').find('image'):#gdy obraz zapisano jako image
                                    index = link.get('src').find('image')#zapisanie pozycji
                                    if index != -1:#jeśli za pozycją znajdują się dane
                                        target_results.append(link.get('src')[:index + 5])#skróć adres obrazu
                                elif link.get('src') not in results:#jeśli adresu obrazu jeszcze nie zapisano
                                    target_results.append(link.get('src'))# zapisz adres na liście
                                    #powyższe instrukcje wycinają niepotrzebne modyfikatory, np blur
                            else:#jeśli adres nie jest pełny
                                if link.get('src') not in results:#jeśli adresu obrazu jeszcze nie zapisano
                                    if link.get('src').find('no_thumbnail')==-1:#pomija puste obrazy, np na stronie olx
                                        target_results.append(urljoin(url,link.get('src')))#stwórz adres za pomocą url
            elif target == 'video':#jeśli szukane są znaczniki wideo
                for src_tag in link.find_all(['source', 'iframe', 'embed']):#jeśli znaleziono podane tagi
                    if src_tag.get('src') and src_tag['src'] not in target_results:#jeśli adres istnieje i jeszcze go nie zapisano
                        target_results.append(src_tag['src'])#zapisz adres na liście
            else:#dla pozostałych szukanych elementów
                if link.text not in target_results:#jeśli jeszcze ich nie zapisano
                    target_results.append(link.text)#dołącz dane do listy
        results.append(target_results)#dołącz znalezione elementy do wyników
    return results#zwróc listę z wynikami dla danej strony url

async def main():# funkcja główna
    time_start = time.time()

    with ProcessPoolExecutor() as pool:#przy użyciu wieloprocesowości
        loop = asyncio.get_running_loop()
        urls = await loop.run_in_executor(pool, sync_getUrls)#pobierz z bazy adresy url do przeszukania
        targets = await loop.run_in_executor(pool, sync_getTargets)#pobierz z bazy cele do znalezienia

    # równoległe pobieranie i parsowanie zawartości dla każdego url
    fetch_tasks = [async_parse_content(url, targets) for url in urls]
    results = await asyncio.gather(*fetch_tasks)#czekaj na wyniki

    # wypłaszczanie listy wyników, usunięcie niepotrzebnych zagnieżdżeń
    flat_results = [item for sublist in results for item in sublist]

    with ProcessPoolExecutor() as pool:#przy użyciu wieloprocesowości
        loop = asyncio.get_running_loop()#wyślij pozyskane dane do bazy
        await loop.run_in_executor(pool, sync_pushData, flat_results, urls, targets)

    print(f'\nCzas wykonania: {time.time() - time_start}')

if __name__ == '__main__':
    asyncio.run(main())
