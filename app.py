import os
from dotenv import load_dotenv
import requests

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Obtiene los valores de las variables de entorno
access_token = os.getenv('ACCESS_TOKEN')
account_id = os.getenv('ACCOUNT_ID')

# Verifica que el token de acceso exista
if not access_token:
    raise ValueError('Debes configurar tu ACCESS_TOKEN en un archivo .env')

# URLs de la API para obtener los datos de las acciones en contado inmediato y a 48 hs
api_urls = {
    'general_ci': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=ACCIONES&instrument_subtype=GENERAL&settlement_days=CI&currency=ARS&segment=C&size=50&page=1',
    'general_48': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=ACCIONES&instrument_subtype=GENERAL&settlement_days=48hs&currency=ARS&segment=C&size=50&page=1',
    'lideres_ci': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=ACCIONES&instrument_subtype=LIDERES&settlement_days=CI&currency=ARS&segment=C&size=50&page=1',
    'lideres_48': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=ACCIONES&instrument_subtype=LIDERES&settlement_days=48hs&currency=ARS&segment=C&size=50&page=1',
    'bonos_ci': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=BONOS_PUBLICOS&instrument_subtype=NACIONALES_USD&settlement_days=CI&currency=ARS&segment=C&size=50&page=1',
    'bonos_48': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=BONOS_PUBLICOS&instrument_subtype=NACIONALES_USD&settlement_days=48hs&currency=ARS&segment=C&size=50&page=1',
    'bonos_corp_ci': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=BONOS_CORP&instrument_subtype=TOP&settlement_days=CI&currency=ARS&segment=C&size=50&page=1',
    'bonos_corp_48': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=BONOS_CORP&instrument_subtype=TOP&settlement_days=48hs&currency=ARS&segment=C&size=50&page=1',
    'bonos_usd_ci': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=BONOS_PUBLICOS&instrument_subtype=NACIONALES_USD&settlement_days=CI&currency=USD&segment=C&size=50&page=1',
    'bonos_usd_48': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=BONOS_PUBLICOS&instrument_subtype=NACIONALES_USD&settlement_days=48hs&currency=USD&segment=C&size=50&page=1',
    'bonos_corp_usd_ci': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=BONOS_CORP&instrument_subtype=TOP&settlement_days=CI&currency=USD&segment=C&size=50&page=1',
    'bonos_corp_usd_48': 'https://api.cocos.capital/api/v1/markets/tickers?instrument_type=BONOS_CORP&instrument_subtype=TOP&settlement_days=48hs&currency=USD&segment=C&size=50&page=1'
}

# Prepara los encabezados para la autenticación Bearer y el ID de cuenta
headers = {
    'Authorization': f'Bearer {access_token}',
    'x-account-id': account_id
}

# Inicializa variables
data = {}
umbral_ganancia = 100
saldo_disponible = 1475000
oportunidades_arbitraje = []
oportunidades_probabilisticas = []
oportunidades_mep = []

# Realiza solicitudes GET a todas las URLs configuradas y almacena las respuestas
for key, url in api_urls.items():
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data[key] = response.json()
    else:
        print(f'Error al obtener datos de {key}: status code {response.status_code}')
        data[key] = {'items': []}  # Asegura que siempre hay una lista de items, incluso en error

# Función para procesar los datos y encontrar oportunidades de arbitraje
def procesar_datos(data_ci, data_48, tipo):
    for item_ci in data_ci['items']:
        matching_item = next((item_48 for item_48 in data_48['items'] if item_48['instrument_code'] == item_ci['instrument_code']), None)
        
        if not matching_item or not item_ci.get('asks') or not matching_item.get('bids'):
            continue

        ask_ci = item_ci['asks'][0]  # Tomamos la primera oferta de venta en CI
        bid_48 = matching_item['bids'][0]  # Tomamos la primera oferta de compra en 48 hs

        if ask_ci['price'] <= 0 or bid_48['price'] <= 0:
            # Ignora esta iteración si el precio de compra o venta es menor o igual a cero
            continue

        diferencia_precios = bid_48['price'] - ask_ci['price']
        if diferencia_precios > umbral_ganancia:
            precio_compra = ask_ci['price']
            if precio_compra > 0:
                cantidad_maxima_comprable = min(saldo_disponible // precio_compra, ask_ci['size'], bid_48['size'])
                if cantidad_maxima_comprable > 0:  # Asegúrate de que la cantidad máxima comprable sea mayor que cero
                    ganancia_esperada = cantidad_maxima_comprable * diferencia_precios
                    oportunidades_arbitraje.append({
                        'tipo': tipo,
                        'short_ticker': item_ci['short_ticker'],
                        'instrument_name': item_ci['instrument_name'],
                        'compra_ci_price': precio_compra,
                        'venta_48_price': bid_48['price'],
                        'cantidad': cantidad_maxima_comprable,
                        'diferencia_precios': diferencia_precios,
                        'ganancia_esperada': f"ARS {ganancia_esperada:.2f}"
                    })

# procesar_datos(data['general_ci'], data['general_48'], 'General')
# procesar_datos(data['lideres_ci'], data['lideres_48'], 'Líderes')
# procesar_datos(data['bonos_ci'], data['bonos_48'], 'Bonos')
# procesar_datos(data['bonos_corp_ci'], data['bonos_corp_48'], 'Bonos Corporativos')

# Imprime las oportunidades de arbitraje encontradas
for oportunidad in oportunidades_arbitraje:
    print(f"Oportunidad de arbitraje para {oportunidad['instrument_name']} (Ticker: {oportunidad['short_ticker']}, Tipo: {oportunidad['tipo']})")
    print(f"\tCompra en CI a: {oportunidad['compra_ci_price']}")
    print(f"\tVenta en 48hs a: {oportunidad['venta_48_price']}")
    print(f"\tCantidad: {oportunidad['cantidad']}")
    print(f"\tDiferencia de precios: {oportunidad['diferencia_precios']}")
    print(f"\tGanancia esperada: {oportunidad['ganancia_esperada']}\n")

oportunidades_probabilisticas = []

def procesar_datos_probabilisticos(data_ci, data_48, tipo):
    oportunidades_probabilisticas = []
    for item_ci in data_ci['items']:
        matching_item = next((item_48 for item_48 in data_48['items'] if item_48['instrument_code'] == item_ci['instrument_code']), None)
        
        if not matching_item or not matching_item.get('bids'):
            continue

        precio_compra_probabilistico = item_ci['last']
        if precio_compra_probabilistico is None:  # Comprueba si precio_compra_probabilistico es None
            continue  # Si es None, salta a la siguiente iteración del bucle
        
        mejor_precio_compra_48 = matching_item['bids'][0]['price']
        
        spread = mejor_precio_compra_48 - precio_compra_probabilistico
        if spread > umbral_ganancia:
            cantidad_maxima_comprable = min(saldo_disponible // precio_compra_probabilistico, matching_item['bids'][0]['size'])
            ganancia_esperada = cantidad_maxima_comprable * spread
            oportunidades_probabilisticas.append({
                'tipo': tipo,
                'short_ticker': item_ci['short_ticker'],
                'instrument_name': item_ci['instrument_name'],
                'compra_last_price': precio_compra_probabilistico,
                'venta_bid_price_48': mejor_precio_compra_48,
                'cantidad_comprable': cantidad_maxima_comprable,
                'diferencia_precios': spread,
                'ganancia_esperada': f"ARS {ganancia_esperada:.2f}"
            })


# Procesa los datos para general, líderes y bonos tanto para oportunidades certeras como probabilísticas
for tipo in ['general', 'lideres', 'bonos', 'bonos_corp']:
    procesar_datos(data[f'{tipo}_ci'], data[f'{tipo}_48'], tipo.capitalize())
    procesar_datos_probabilisticos(data[f'{tipo}_ci'], data[f'{tipo}_48'], tipo.capitalize())

# Imprime las oportunidades certeras de arbitraje encontradas
print("Oportunidades Certeras de Arbitraje:")
for oportunidad in oportunidades_arbitraje:
    print(f"Oportunidad de arbitraje para {oportunidad['instrument_name']} (Ticker: {oportunidad['short_ticker']}, Tipo: {oportunidad['tipo']})")
    print(f"\tCompra en CI a: {oportunidad['compra_ci_price']}")
    print(f"\tVenta en 48hs a: {oportunidad['venta_48_price']}")
    print(f"\tCantidad: {oportunidad['cantidad']}")
    print(f"\tDiferencia de precios: {oportunidad['diferencia_precios']}")
    # print(f"\tGanancia esperada: {oportunidad['ganancia_esperada']}\n")

# Imprime las oportunidades probabilísticas de arbitraje encontradas
print("Oportunidades Probabilísticas de Arbitraje:")
for oportunidad in oportunidades_probabilisticas:
    print(f"Oportunidad probabilística de arbitraje para {oportunidad['instrument_name']} (Ticker: {oportunidad['short_ticker']}, Tipo: {oportunidad['tipo']})")
    print(f"\tÚltimo precio vendido en CI: {oportunidad['compra_last_price']}")
    print(f"\tÚltimo precio ofrecido en 48hs: {oportunidad['venta_ask_price']}")
    print(f"\tDiferencia de precios: {oportunidad['diferencia_precios']}\n")
    # print(f"\tGanancia esperada: {oportunidad['ganancia_esperada']}\n")
    


def buscar_oportunidades_dolar_mep(data_ars, data_usd, tipo):
    for item_ars in data_ars['items']:
        item_usd = next((item for item in data_usd['items'] if item['instrument_code'] == item_ars['instrument_code']), None)
        if not item_usd:
            continue
        
        if item_ars['ask'] and item_usd['bid']:
            tipo_cambio_mep = item_ars['ask'] / item_usd['bid']
            ganancia_usd = saldo_disponible / tipo_cambio_mep
            oportunidades_mep.append({
                'tipo': tipo,
                'instrument_code': item_ars['instrument_code'],
                'compra_ars': item_ars['ask'],
                'venta_usd': item_usd['bid'],
                'tipo_cambio_mep': tipo_cambio_mep,
                'ganancia_usd': ganancia_usd                                                    
            })

# Ejecutar la búsqueda de oportunidades para cada par de bonos/ON en ARS y USD
buscar_oportunidades_dolar_mep(data['bonos_ci'], data['bonos_usd_48'], 'Bonos Públicos MEP')
buscar_oportunidades_dolar_mep(data['bonos_corp_ci'], data['bonos_corp_usd_48'], 'Bonos Corporativos MEP')

# Imprimir las oportunidades encontradas
print("Oportunidades Dólar MEP:")
for oportunidad in oportunidades_mep:
    print(f"Oportunidad de Dólar MEP en {oportunidad['tipo']} ({oportunidad['instrument_code']})")
    print(f"\tCompra en ARS: {oportunidad['compra_ars']}")
    print(f"\tVenta en USD: {oportunidad['venta_usd']}")
    print(f"\tTipo de cambio MEP: {oportunidad['tipo_cambio_mep']:.2f}\n")
    # print(f"\tGanancia USD: {oportunidad['ganancia_usd']}")
