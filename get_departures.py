# -*- coding: utf-8 -*-
import requests
import pytz
from datetime import datetime
import string
import json
import time
import os

# Configurazione Supabase
SUPABASE_URL = 'https://znvoqrkcslicihrnjxym.supabase.co'  # Project URL
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpudm9xcmtjc2xpY2locm5qeHltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM0Njc1MTAsImV4cCI6MjA2OTA0MzUxMH0.C7BzqwA4aHolWVMk2uOTqPByryWTaDdjCIjnFPQhgj4'


url_viaggiatreno = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/"

def insert_to_supabase(departures_batch):
    """Inserisce batch di partenze in Supabase"""
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }

    # Prepara i dati per Supabase
    data_to_insert = []
    for departure in departures_batch:
        data_to_insert.append({
            'station_code': departure[0],
            'train_number': departure[1],
            'created_at': datetime.now().isoformat()
        })

    # Inserisce nel database
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/departures",
        headers=headers,
        json=data_to_insert
    )

    if response.status_code == 201:
        print(f"Inseriti {len(data_to_insert)} record in Supabase")
        return True
    else:
        print(f"Errore inserimento Supabase: {response.status_code} - {response.text}")
        return False

#### FUNZIONI ORIGINALI (con piccole ottimizzazioni)

def autocomplete_station(station_string_start):
    response = requests.get(url_viaggiatreno + 'autocompletaStazione/' + station_string_start).text.split('\n')
    return response

def elenca_stazioni():
    lista_stazioni = []
    for letter in string.ascii_lowercase:
        lista_stazioni.append(autocomplete_station(letter))
        time.sleep(0.1)  # Piccola pausa per non sovraccaricare l'API

    flattened_list = [item for sublist in lista_stazioni for item in sublist]
    return sorted(list(set(flattened_list)))

def formatted_string_datetime(out_form, data='', in_form=''):
    timezone = pytz.timezone("Europe/Rome")
    if data:
        data = datetime.strptime(data, in_form)
    else:
        data = datetime.now(timezone)
    formatted_string = data.strftime(out_form)
    return formatted_string

def get_routes_for_station(station_code, orario):
    formatted_date = formatted_string_datetime('%a %b %d %Y')
    date_time = (formatted_date + " " + datetime.strptime(orario, "%H:%M").strftime("%H:%M:%S") +
                 " GMT+0100%20(Ora%20standard%20dell%E2%80%99Europa%20centrale)").replace(" ", "%20")

    api_url = f"{url_viaggiatreno}partenze/{station_code}/{date_time}"

    try:
        response = requests.get(api_url, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error during API call: {e}")
        return []

#### SCRIPT PRINCIPALE

print("Avvio monitoraggio treni...")
start_time = datetime.now()

station_list = elenca_stazioni()
print(f"Trovate {len(station_list)} stazioni")

departures_list = []
error_list = []
batch_size = 100  # Inserisce ogni 100 record

for count, station_i in enumerate(station_list[1:], start=1):
    print(f'🚉 Stazione {station_i.split("|")[0]} - {count}/{len(station_list)-1}')

    current_time = datetime.now().strftime('%H:%M')

    try:
        station_i_num = station_i.split('|')[1]
        departures_station_i = get_routes_for_station(station_i_num, current_time)

        for route in departures_station_i:
            train_number = route['numeroTreno']
            if route['codOrigine'] == station_i_num:
                departures_list.append([station_i_num, train_number])
                print(f'Treno {train_number} dalla stazione {station_i.split("|")[0]}')

        # Inserisce batch ogni 100 record
        if len(departures_list) >= batch_size:
            if insert_to_supabase(departures_list):
                departures_list.clear()  # Svuota la lista dopo l'inserimento

        time.sleep(0.2)  # Pausa tra le richieste

    except Exception as e:
        print(f"Errore con {station_i}: {e}")
        error_list.append(station_i)

# Inserisce gli ultimi record rimasti
if departures_list:
    insert_to_supabase(departures_list)

end_time = datetime.now()
duration = end_time - start_time

print(f"🏁 Completato in {duration}")
print(f"📊 Errori: {len(error_list)} stazioni")

# Salva anche backup locale degli errori (opzionale)
if error_list:
    with open(f'errors_{start_time.strftime("%Y%m%d_%H%M")}.json', 'w') as f:
        json.dump(error_list, f, indent=2)
