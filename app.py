import os
from dotenv import load_dotenv
import requests

#importar y cargar schudele luego lo separaremos en otro modulo
import schedule
import time

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
            # if cantidad_maxima_comprable > 0:  # Asegúrate de que la cantidad máxima comprable sea mayor que cero
                ganancia_esperada = 1000 * diferencia_precios
                oportunidades_arbitraje.append({
                    'tipo': tipo,
                    'short_ticker': item_ci['short_ticker'],
                    'instrument_name': item_ci['instrument_name'],
                    'compra_ci_price': precio_compra,
                    'venta_48_price': bid_48['price'],
                    'cantidad': 1000,
                    'diferencia_precios': diferencia_precios,
                    'ganancia_esperada': f"ARS {ganancia_esperada:.2f}"
                })

# Función para procesar los datos y encontrar oportunidades de arbitraje probabilístico
def procesar_datos_probabilisticos(data_ci, data_48, tipo):
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
            # cantidad_maxima_comprable = min(saldo_disponible // precio_compra_probabilistico, matching_item['bids'][0]['size'])
            ganancia_esperada = 1000 * spread
            oportunidades_probabilisticas.append({
                'tipo': tipo,
                'short_ticker': item_ci['short_ticker'],
                'instrument_name': item_ci['instrument_name'],
                'compra_last_price': precio_compra_probabilistico,
                'venta_bid_price_48': mejor_precio_compra_48,
                'cantidad_comprable': 1000,
                'diferencia_precios': spread,
                'ganancia_esperada': f"ARS {ganancia_esperada:.2f}"
            })

def buscar_oportunidades_dolar_mep(data_ars, data_usd, tipo):
    for item_ars in data_ars['items']:
        item_usd = next((item for item in data_usd['items'] if item['instrument_code'] == item_ars['instrument_code']), None)
        if not item_usd:
            continue
        
        if item_ars['ask'] and item_usd['bid']:
            tipo_cambio_mep = item_ars['ask'] / item_usd['bid']
            ganancia_usd = saldo_disponible / tipo_cambio_mep
            if tipo_cambio_mep < 1000:
                oportunidades_mep.append({
                    'tipo': tipo,
                    'instrument_code': item_ars['instrument_code'],
                    'compra_ars': item_ars['ask'],
                    'venta_usd': item_usd['bid'],
                    'tipo_cambio_mep': tipo_cambio_mep,
                    'ganancia_usd': ganancia_usd                                                    
                })

def imprimir_oportunidades():
    for oportunidad in oportunidades_arbitraje:
        print(f"Oportunidad de arbitraje para {oportunidad['instrument_name']} (Ticker: {oportunidad['short_ticker']}, Tipo: {oportunidad['tipo']})")
        print(f"\tCompra en CI a: {oportunidad['compra_ci_price']}")
        print(f"\tVenta en 48hs a: {oportunidad['venta_48_price']}")
        print(f"\tCantidad: {oportunidad['cantidad']}")
        print(f"\tDiferencia de precios: {oportunidad['diferencia_precios']}")
        print(f"\tGanancia esperada: {oportunidad['ganancia_esperada']}\n")
        
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
        print(f"\tÚltimo precio ofrecido en 48hs: {oportunidad['venta_bid_price_48']}")
        print(f"\tDiferencia de precios: {oportunidad['diferencia_precios']}\n")
        # print(f"\tGanancia esperada: {oportunidad['ganancia_esperada']}\n")

    # Imprimir las oportunidades encontradas
    print("Oportunidades Dólar MEP:")
    for oportunidad in oportunidades_mep:
        print(f"Oportunidad de Dólar MEP en {oportunidad['tipo']} ({oportunidad['instrument_code']})")
        print(f"\tCompra en ARS: {oportunidad['compra_ars']}")
        print(f"\tVenta en USD: {oportunidad['venta_usd']}")
        print(f"\tTipo de cambio MEP: {oportunidad['tipo_cambio_mep']:.2f}\n")
        # print(f"\tGanancia USD: {oportunidad['ganancia_usd']}")
        
def procesar_scalping(data_ci):
    oportunidades_scalping = []
    for item in data_ci['items']:
        if not item.get('asks') or not item.get('bids'):
            continue

        # Consideramos el mejor precio de venta (ask) y el mejor precio de compra (bid)
        mejor_ask = item['asks'][0]
        mejor_bid = item['bids'][0]

        # Verificamos que exista una diferencia de precio que justifique el scalping
        diferencia_precios = mejor_ask['price'] - mejor_bid['price']
        if diferencia_precios <= 0 or (mejor_ask['size'] < 1 or mejor_bid['size'] < 1):
            continue

        # Comprobamos la tendencia del mercado para ese instrumento
        tendencia = (item['last'] - item['prev_close']) / item['prev_close'] if item['prev_close'] else 0

        # Consideramos solo oportunidades con tendencia positiva y con volumen significativo
        if tendencia > 0 and item['volume'] > 1000:  # El umbral de volumen puede ajustarse según el análisis
            oportunidades_scalping.append({
                'ticker': item['short_ticker'],
                'nombre': item['instrument_name'],
                'precio_compra': mejor_bid['price'],
                'precio_venta': mejor_ask['price'],
                'volumen': item['volume'],
                'diferencia_precios': diferencia_precios,
                'tendencia': tendencia
            })

    return oportunidades_scalping

def imprimir_oportunidades_scalping(oportunidades_scalping):
    for oportunidad in oportunidades_scalping:
        print(f"Oportunidad de Scalping para {oportunidad['nombre']} (Ticker: {oportunidad['ticker']})")
        print(f"\tCompra a: {oportunidad['precio_compra']}")
        print(f"\tVenta a: {oportunidad['precio_venta']}")
        print(f"\tVolumen: {oportunidad['volumen']}")
        print(f"\tDiferencia de precios: {oportunidad['diferencia_precios']}")
        print(f"\tTendencia: {'Positiva' if oportunidad['tendencia'] > 0 else 'Negativa'}\n")

def main():
    print("Inicializando la aplicación...")
    
    # Procesa los datos para general, líderes y bonos tanto para oportunidades certeras como probabilísticas
    for tipo in ['general', 'lideres', 'bonos', 'bonos_corp']:
        procesar_datos(data[f'{tipo}_ci'], data[f'{tipo}_48'], tipo.capitalize())
        procesar_datos_probabilisticos(data[f'{tipo}_ci'], data[f'{tipo}_48'], tipo.capitalize())

    # Ejecutar la búsqueda de oportunidades para cada par de bonos/ON en ARS y USD
    buscar_oportunidades_dolar_mep(data['bonos_ci'], data['bonos_usd_48'], 'Bonos Públicos MEP')
    buscar_oportunidades_dolar_mep(data['bonos_corp_ci'], data['bonos_corp_usd_48'], 'Bonos Corporativos MEP')

    # Imprime las oportunidades encontradas
    imprimir_oportunidades()
    
    print("Esperando 5 minutos para la próxima ejecución...")
    # imprimir hora de ejecución
    print(time.strftime("%H:%M:%S"))

def scalping():
    print("Inicializando la búsqueda de oportunidades de scalping...")
    oportunidades_scalping_total = []  # Lista para guardar todas las oportunidades de scalping
    for tipo in ['general', 'lideres', 'bonos', 'bonos_corp']:
        oportunidades_scalping = procesar_scalping(data[f'{tipo}_ci'])  # Obtiene las oportunidades de scalping
        oportunidades_scalping_total.extend(oportunidades_scalping)  # Agrega las oportunidades encontradas a la lista total

    imprimir_oportunidades_scalping(oportunidades_scalping_total)  # Ahora pasamos la lista correcta como argumento
    print("Esperando 60 segundos para la próxima ejecución...")
    # imprimir hora de ejecución
    print(time.strftime("%H:%M:%S"))

main()
scalping()


# Ejecutar la función main cada 5 minutos
schedule.every(5).minutes.do(main)
schedule.every(60).seconds.do(scalping)

while True:
    schedule.run_pending()
    time.sleep(1)