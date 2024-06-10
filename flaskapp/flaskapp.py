from redis import Redis
from flask import Flask, render_template, request,redirect, url_for
from urllib.parse import urljoin
import subprocess
import json

def uploadData(urls,targets,con):#funkcja przesyła do bazy adresy url i cele podane przez użytkownika
    con.delete('urls')#wyczyść stare adresy
    con.delete('targets')#wyczyść stare cele
    for url in urls:#każdy adres url z listy
        con.rpush('urls',url)#dołącz do bazy
    for target in targets:#każdy element z listy
        con.rpush('targets',target)#dołącz do bazy

def getResults(urls,targets):#funkcja pobiera wyniki
    r = Redis(host='172.17.0.2', port=6379, db=0) # połączenie z bazą Redis
    uploadData(urls,targets,r)#wyślij dane użytkownika do bazy 
    subprocess.run("docker start silnik", shell=True)#w oddzielnym procesie uruchom silnik aplikacji
    subprocess.run("docker wait silnik", shell=True)#poczekaj na koniec pracy kontenera
    return json.loads(r.get('results'))#zwraca zdeserializowaną listę z wynikami z bazy danych redis

def getUrlsH():#f pobiera wcześniej parsowane adresy stron 
    r = Redis(host='172.17.0.2', port=6379, db=0) # połączenie z bazą Redis
    urlsH = [json.loads(item) for item in r.lrange('urlsH', 0, -1)]#pobiera zdeserializowaną listę url z bazy danych redis
    return urlsH#zwraca listę url

def getTargetsH():#f pobiera wcześniej szukane znaczniki stron
    r = Redis(host='172.17.0.2', port=6379, db=0) # połączenie z bazą Redis
    targetsH = [json.loads(item) for item in r.lrange('targetsH', 0, -1)]#pobiera zdeserializowaną listę celów z bazy danych redis
    return targetsH#zwraca listę znaczników

def getResultsH():#f pobiera wcześniej pozyskane wyniki
    r = Redis(host='172.17.0.2', port=6379, db=0)# połączenie z bazą Redis
    resultsH = [json.loads(item) for item in r.lrange('resultsH', 0, -1)]#pobiera zdeserializowaną listę wyników z bazy danych redis
    return resultsH#zwraca listę wyników

def deleteH():#f usuwa historię wyników
    r = Redis(host='172.17.0.2', port=6379, db=0) # połączenie z bazą Redis
    r.delete('resultsH')#usuń dawne wyniki
    r.delete('urlsH')#usuń dawne adresy url
    r.delete('targetsH')#usuń dawne znaczniki

def translate(targets):#f zamienia znaczniki na nazwy
    Targets = []#nowa lista znaczników
    for target in targets:#dla każdego znacznika
        if target=='h1':
            Targets.append('nagłówki 1')#
        if target=='h2':                #
            Targets.append('nagłówki 2')#
        if target=='h3':                #
            Targets.append('nagłówki 3')#
        if target=='h4':                #
            Targets.append('nagłówki 4')#
        if target=='h5':                #            
            Targets.append('nagłówki 5')# nadaj odpowiednią nazwę
        if target=='h6':                #
            Targets.append('nagłówki 6')#
        if target=='a':                 #
            Targets.append('hiperłącza')#
        if target=='img':               #
            Targets.append('obrazy')    #
        if target=='p':                 #
            Targets.append('paragrafy') #
        if target=='span':              #
            Targets.append('linie tekstu')
        if target=='video':
            Targets.append('wideo')
    return Targets#zwraca nową listę z nazwami
        
def binary(url_index, target_index, num_targets):#f tworzy kombinację indeksów url i target aby dobrać 
    combined_index = (url_index * num_targets) + target_index#odpowiednią pozycję results
    return combined_index#zwraca indeks results na potrzeby skryptu w pliku results.html

urls = [] # lista adresów url
targets = [] # lista szukanych znaczników
results = [] # lista wyników

resultsH = [] # lista wcześniej pozyskanych wyników
urlsH = [] # lista wcześniej użytych adresów
targetsH = [] # lista wcześniej szukanych znaczników

app = Flask(__name__)# aplikacja Flask

app.jinja_env.globals['binary'] = binary# przekazanie funkcji binary

@app.route('/')#domyślna ścieżka
def index():# zwraca stronę index.html
    return render_template('index.html',urls=urls,targets=targets)# przekazuje listy adresów i znaczników

@app.route('/results')#ścieżka wyników 'results'
def results():
    results = getResults(urls,targets)#pobiera wyniki z bazy uzyskane przez silnik
    Targets = translate(targets)# zamienia znaczniki na nazwy
    return render_template('results.html',results=results,targets=Targets,urls=urls)#zwraca stronę 'results' wraz z listami wyników,znaczników i stron url

@app.route('/history')#ścieżka z historią wyszukiwań 'history'
def history():
    urlsH = getUrlsH()#pobiera historię adresów url
    targetsH = getTargetsH()# pobiera historię znaczników
    resultsH = getResultsH()# pobiera historię wyników
    return render_template('history.html',urls=urlsH,targets=targetsH,results=resultsH)#zwraca 'history'

@app.route('/',methods=['POST','GET'])#ścieżka przekierowuje dane z formularza
def submit():
    form_data = request.form.to_dict()#pobranie danych z formularza
    for key, value in form_data.items():#sprawdzanie klucza i wartości danych z formularza
        if(key =='url'):#jeśli dane oznaczone są jako adres url
            if(value!=''):#jeśli wartość nie jest pusta
                urls.append(value)#dołącz adres do listy urls
        else:# w innym wypadku
            if(value=='on'):# jeśli pozycja jest zaznaczona - checked
                targets.append(key)# dodaj wartość do listy szukanych znaczników
    return redirect(url_for('index'))# przekieruj do strony index.html

@app.route('/clearurl')#ścieżka clearurl - resetuje adresy stron url wybrane przez użytkownika
def clearurl():
    global urls
    urls = []# czyści listę adresów url
    return redirect(url_for('index'))# przekierowuje do strony index.html

@app.route('/cleartarget')#ścieżka cleartarget - resetuje znaczniki wybrane przez użytkownika
def cleartarget():
    global targets
    targets = []# czyści listę znaczników
    return redirect(url_for('index'))# przekierowuje do strony index.html


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)# uruchomienie aplikacji na localhost
    

