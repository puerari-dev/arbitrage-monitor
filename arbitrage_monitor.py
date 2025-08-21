import ccxt
import concurrent.futures
import time
import os
import re
from datetime import datetime


# Configuração das exchanges de compra e venda
# 'binance', 'bybit', 'bitget', 'bitfinex', 'gateio', 'okx', 'huobi', 'mercado', 'coinbase', 'kraken', 'kucoin', 'mexc', 'p2b', 'whitebit', 'xt'
exchanges_compra_names = ['binance', 'huobi', 'bybit', 'mexc', 'mercado']
exchanges_venda_names = ['binance', 'bybit', 'bitget', 'okx', 'huobi', 'mercado', 'coinbase', 'kraken', 'kucoin', 'mexc']

# União das listas sem duplicatas
exchanges_compra_venda = list(set(exchanges_compra_names + exchanges_venda_names))
# Inicialização das exchanges
exchanges = [getattr(ccxt, name)() for name in exchanges_compra_venda]

percentual_arbitragem = 4  # Arbitragem deve ser superior a x%
percentual_max_arbitragem = 60  # Arbitragem deve ser inferior a x%
liquidez_minima = 1  # Liquidez total mínima para compra e venda em USDT
numero_ordens = 14  # Número de ordens a serem exibidas do livro de ordens
volume_arbitragem_usdt = 500 # Volume para cálculo de spread médio


# Função para carregar os pares de cada corretora
def carregar_pares_de_arquivo(corretora):
    # Define o caminho completo do arquivo na pasta 'pairs'
    arquivo = os.path.join('pairs', f'{corretora}.pairs')
    pares = []
    
    if os.path.exists(arquivo):
        try:
            with open(arquivo, 'r') as file:
                conteudo = file.read()
                # Remove espaços extras e quebra de linha
                conteudo = conteudo.strip()
                
                # Usa expressão regular para extrair os pares removendo aspas simples e separando por vírgula
                pares = re.findall(r"'([^']+)'", conteudo)
        except Exception as e:
            print(f"Erro ao ler o arquivo {arquivo}: {e}")
    else:
        print(f"Arquivo {arquivo} não encontrado.")
    
    return pares

# Função para carregar a blacklist de pares
def carregar_blacklist():
    # Define o caminho completo do arquivo de blacklist
    arquivo_blacklist = os.path.join('pairs', 'blacklist.pairs')
    blacklist = {}

    if os.path.exists(arquivo_blacklist):
        try:
            with open(arquivo_blacklist, 'r') as file:
                conteudo = file.read().strip()

                # Usa expressão regular para extrair pares e exchanges
                itens_blacklist = re.findall(r"'([^']+)'", conteudo)

                for item in itens_blacklist:
                    # Divide pelo ponto e vírgula para separar par e exchange
                    par, exchange = item.split(';')
                    par = par.strip()
                    exchange = exchange.strip()

                    # Adiciona ao dicionário: a chave é o par, o valor é uma lista de exchanges
                    if par not in blacklist:
                        blacklist[par] = []
                    blacklist[par].append(exchange)
        except Exception as e:
            print(f"Erro ao ler o arquivo de blacklist {arquivo_blacklist}: {e}")
    else:
        print(f"Arquivo de blacklist {arquivo_blacklist} não encontrado.")
    
    return blacklist

# Função para obter o preço de conversão de BRL para USDT
def obter_preco_brl_usdt(corretora):
    dollar_value = 5.49  # Definido localmente na função como valor padrão
    
    try:
        # Obtém o ticker para o par USDT/BRL
        ticker = corretora.fetch_ticker('USDT/BRL')
        if ticker and ticker.get('bid') is not None:
            # Converte o preço de venda (bid) para BRL/USDT
            preco_brl_usdt = ticker['bid']
        else:
            # Se o par não for encontrado, usa o valor local dollar_value
            preco_brl_usdt = dollar_value
            print("Par USDT/BRL não encontrado. Usando valor local dollar_value.")
    except Exception as e:
        # Em caso de erro, usa o valor local dollar_value
        preco_brl_usdt = dollar_value
        print(f"Erro ao obter preço USDT/BRL: {e}. Usando valor local dollar_value.")
    
    return preco_brl_usdt

        
# Função para obter o preço de conversão de USD para USDT
def obter_preco_usd_usdt(corretora):
    try:
        # Obtém o ticker para o par USDT/USD
        ticker = corretora.fetch_ticker('USDT/USD')
        if ticker and ticker.get('bid') is not None:
            # Converte o preço de venda (bid) para USD/USDT
            preco_usd_usdt = ticker['bid']
        else:
            # Se o par não for encontrado, define a conversão como 1:1
            preco_usd_usdt = 1
            print("Par USDT/USD não encontrado. Usando conversão 1:1.")
    except Exception as e:
        # Em caso de erro, define a conversão como 1:1
        preco_usd_usdt = 1
        print(f"Erro ao obter preço USDT/USD: {e}. Usando conversão 1:1.")
    
    return preco_usd_usdt
        

# Função para obter preços e liquidez de uma exchange, com paralelização por pares
def obter_precos_e_liquidez(corretora):
    precos = {}
    
    try:
        mercados = corretora.load_markets()

        # Carrega os pares da exchange a partir do arquivo correspondente
        pares = carregar_pares_de_arquivo(corretora.id)

        # Define o fator de conversão de moedas se necessário
        if corretora.id in ['mercado']:
            preco_conversion = obter_preco_brl_usdt(corretora)
        elif corretora.id in ['kraken', 'coinbase', 'bitfinex']:
            preco_conversion = obter_preco_usd_usdt(corretora)
        else:
            preco_conversion = None
            
        def processar_par(par):
            try:
                # Introduz um atraso específico para evitar rate limit
                if corretora.id == 'kucoin':
                    time.sleep(1.2)
                elif corretora.id in ['gateio', 'coinbase', 'bitget', 'bitfinex', 'okx', 'xt']:
                    time.sleep(0.7)

                moeda, base = par.split('/')
                #print(f"Processando par {par} na exchange {corretora.id}")

                # Obtém o ticker do par ou faz a conversão para USDT se necessário
                ticker = corretora.fetch_ticker(par) if par in mercados else None
                if ticker:
                    if base == 'BRL' and preco_conversion:
                        if ticker['ask'] is not None and ticker['bid'] is not None:
                            ticker['ask'] /= preco_conversion
                            ticker['bid'] /= preco_conversion
                            par = f'{moeda}/USDT'  # Atualiza o par para USDT
                        else:
                            print(f"Ticker inválido para {par} na corretora {corretora.id}: ask ou bid é None")
                            return None  # Ignora este par se ask ou bid for None
                    elif base == 'USD' and preco_conversion:
                        if ticker['ask'] is not None and ticker['bid'] is not None:
                            ticker['ask'] /= preco_conversion
                            ticker['bid'] /= preco_conversion
                            par = f'{moeda}/USDT'  # Atualiza o par para USDT
                        else:
                            print(f"Ticker inválido para {par} na corretora {corretora.id}: ask ou bid é None")
                            return None  # Ignora este par se ask ou bid for None

                if ticker:
                    fees = corretora.fees['trading']
                    ask_price = ticker.get('ask') or 0
                    bid_price = ticker.get('bid') or 0
                    base_volume = ticker.get('baseVolume') or 0
                    quote_volume = ticker.get('quoteVolume') or 0

                    ask_liquidez_usdt = base_volume * ask_price
                    bid_liquidez_usdt = quote_volume * bid_price

                    return par, {
                        'bid': bid_price,
                        'ask': ask_price,
                        'bid_liquidez_usdt': bid_liquidez_usdt,
                        'ask_liquidez_usdt': ask_liquidez_usdt,
                        'taxa_compra': fees.get('maker', None),
                        'taxa_venda': fees.get('taker', None),
                        'exchange': corretora.id
                    }
                else:
                    return None

            except Exception as e:
                print(f"Erro ao processar par {par} na exchange {corretora.id}: {e}")
                return None

        # Executa a obtenção de preços para cada par em paralelo com controle de threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            resultados = list(executor.map(processar_par, pares))

        # Filtra os resultados não nulos e atualiza o dicionário de preços
        for resultado in resultados:
            if resultado:
                par, dados_preco = resultado
                precos[par] = dados_preco

    except Exception as e:
        print(f"Erro ao obter preços e liquidez de {corretora.id}: {e}")
    
    return precos


# Função para processar preços de todas as exchanges em paralelo
def processar_precos():
    precos_por_exchange = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_exchange = {executor.submit(obter_precos_e_liquidez, exchange): exchange for exchange in exchanges}
        for future in concurrent.futures.as_completed(future_to_exchange):
            exchange = future_to_exchange[future]
            try:
                resultado = future.result()
                if resultado:  # Verifica se o resultado não está vazio
                    precos_por_exchange[exchange.id] = resultado
                else:
                    print(f"Nenhum preço obtido para {exchange.id}")
            except Exception as e:
                print(f"Erro durante o processamento de {exchange.id}: {e}")
    return precos_por_exchange


# Função para obter o livro de ordens de uma exchange para um par específico
def obter_livro_ordens(corretora, par, numero_ordens):
    try:
        # Obtém o livro de ordens na moeda original
        livro = corretora.fetch_order_book(par)
        if livro:
            # Verifica a estrutura dos dads
            if len(livro['bids'][0]) == 3:  # Corretoras com 3 parâmetros (OKX)
                ofertas = {
                    'bids': [(preco, volume) for preco, volume, _ in livro['bids'][:numero_ordens]],
                    'asks': [(preco, volume) for preco, volume, _ in livro['asks'][:numero_ordens]]
                }
            else:  # Corretoras com 2 parâmetros
                ofertas = {
                    'bids': [(preco, volume) for preco, volume in livro['bids'][:numero_ordens]],
                    'asks': [(preco, volume) for preco, volume in livro['asks'][:numero_ordens]]
                }
            
            # Verifica se o par é em BRL ou USD e precisa ser convertido para USDT
            if par.split("/")[1] == "BRL":
                preco_brl_usdt = obter_preco_brl_usdt(corretora)
                if preco_brl_usdt:
                    ofertas['bids'] = [(preco / preco_brl_usdt, volume) for preco, volume in ofertas['bids']]
                    ofertas['asks'] = [(preco / preco_brl_usdt, volume) for preco, volume in ofertas['asks']]
                else:
                    print(f"Não foi possível converter {par} para USDT. Usando valores originais.")

            elif par.split("/")[1] == "USD":
                preco_usd_usdt = obter_preco_usd_usdt(corretora)
                if preco_usd_usdt:
                    ofertas['bids'] = [(preco / preco_usd_usdt, volume) for preco, volume in ofertas['bids']]
                    ofertas['asks'] = [(preco / preco_usd_usdt, volume) for preco, volume in ofertas['asks']]
                else:
                    print(f"Não foi possível converter {par} para USDT. Usando valores originais.")
                    
            return ofertas
    except Exception as e:
        print(f"Erro ao obter livro de ordens de {par} na exchange {corretora.id}: {e}")
        return None


# Função para identificar oportunidades de arbitragem
def identificar_arbitragem(precos_por_exchange, percentual_arbitragem, liquidez_minima):
    oportunidades = []

    # Cria uma união de todos os pares presentes nas exchanges
    pares = set()  # Usar set para evitar duplicatas
    for exchange in precos_por_exchange:
        pares.update(precos_por_exchange[exchange].keys())

    for par in pares:
        for exchange_compra in exchanges_compra_names:
            for exchange_venda in exchanges_venda_names:
                # Evita a comparação de uma exchange consigo mesma
                if exchange_compra == exchange_venda:
                    continue
                
                preco_compra = precos_por_exchange.get(exchange_compra, {}).get(par, {})
                preco_venda = precos_por_exchange.get(exchange_venda, {}).get(par, {})

                if not preco_compra or not preco_venda:
                    continue

                bid_compra = preco_compra.get('bid')
                ask_compra = preco_compra.get('ask')
                bid_venda = preco_venda.get('bid')
                ask_venda = preco_venda.get('ask')

                if bid_compra is None or ask_compra is None or bid_venda is None or ask_venda is None:
                    continue

                spread_percentual = round((bid_venda - ask_compra) / ask_compra * 100, 4) if ask_compra else 0
                liquidez_compra = preco_compra.get('ask_liquidez_usdt', 0)
                liquidez_venda = preco_venda.get('bid_liquidez_usdt', 0)

                if spread_percentual >= percentual_arbitragem and liquidez_compra >= liquidez_minima and liquidez_venda >= liquidez_minima:
                    # Obtém o livro de ordens para a exchange de compra
                    corretora_compra = next((ex for ex in exchanges if ex.id == exchange_compra), None)
                    if corretora_compra:
                        if exchange_compra in ['mercado']:  # Exchange que opera com pares BRL
                            par_compra = f'{par.split("/")[0]}/BRL'
                        elif exchange_compra in ['kraken', 'coinbase', 'bitfinex']:  # Exchanges que operam com pares USD
                            par_compra = f'{par.split("/")[0]}/USD'
                        else:
                            par_compra = f'{par.split("/")[0]}/USDT'
                        livro_ordens_compra = obter_livro_ordens(corretora_compra, par_compra, numero_ordens)
                    else:
                        livro_ordens_compra = None
                    # Obtém o livro de ordens para a exchange de venda
                    corretora_venda = next((ex for ex in exchanges if ex.id == exchange_venda), None)
                    if corretora_venda:
                        if exchange_venda in ['mercado']:  # Exchange que opera com pares BRL
                            par_venda = f'{par.split("/")[0]}/BRL'
                        elif exchange_venda in ['kraken', 'coinbase', 'bitfinex']:  # Exchanges que operam com pares USD
                            par_venda = f'{par.split("/")[0]}/USD'
                        else:
                            par_venda = f'{par.split("/")[0]}/USDT'
                        livro_ordens_venda = obter_livro_ordens(corretora_venda, par_venda, numero_ordens)
                    else:
                        livro_ordens_venda = None

                    oportunidades.append({
                        'par': par,
                        'compra': exchange_compra,
                        'venda': exchange_venda,
                        'spread_percentual': spread_percentual,
                        'ask_compra': ask_compra,
                        'bid_venda': bid_venda,
                        'liquidez_compra': liquidez_compra,
                        'liquidez_venda': liquidez_venda,
                        'livro_ordens_compra': livro_ordens_compra,
                        'livro_ordens_venda': livro_ordens_venda
                    })

    return oportunidades


# Função para calcular spread médio de cada oportunidade
def calcular_spread_medio(oportunidade, volume_arbitragem_usdt):
    def calcular_preco_medio(ordens, volume_total_usdt):
        volume_acumulado_usdt = 0
        volume_acumulado_crypto = 0
        
        for preco, volume in ordens:
            if preco == 0:  # Evita divisão por zero no preço
                continue

            volume_restante_usdt = volume_total_usdt - volume_acumulado_usdt
            volume_usdt_a_usar = min(volume_restante_usdt, preco * volume)
            volume_crypto_a_usar = volume_usdt_a_usar / preco
            volume_acumulado_usdt += volume_usdt_a_usar
            volume_acumulado_crypto += volume_crypto_a_usar
            
            if volume_acumulado_usdt >= volume_total_usdt:
                break
        
        if volume_acumulado_crypto > 0:
            return volume_acumulado_usdt / volume_acumulado_crypto, volume_acumulado_usdt
        else:
            return None, 0 
    
    if oportunidade['livro_ordens_compra'] is not None and oportunidade['livro_ordens_venda'] is not None:
        # Extrai os livros de ordens de compra e venda da oportunidade
        livro_ordens_compra = oportunidade['livro_ordens_compra']
        livro_ordens_venda = oportunidade['livro_ordens_venda']

        # Calcula o preço médio para a compra e venda com base no volume_arbitragem_usdt
        preco_medio_compra, volume_acumulado_compra = calcular_preco_medio(livro_ordens_compra['asks'], volume_arbitragem_usdt)
        preco_medio_venda, volume_acumulado_venda = calcular_preco_medio(livro_ordens_venda['bids'], volume_arbitragem_usdt)

        # Calcula o spread percentual com base nos preços médios
        if preco_medio_compra is not None and preco_medio_venda is not None:
            spread_percentual_medio = ((preco_medio_venda - preco_medio_compra) / preco_medio_compra) * 100
            return spread_percentual_medio, volume_acumulado_compra
    else:
        return oportunidade['spread_percentual'], 0  # Retorna o spread padrão e 0 volume se não for possível calcular o spread médio
        

# Função principal para rodar o script de arbitragem
def main():
    while True:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Obtendo preços e liquidez das exchanges...")
            precos_por_exchange = processar_precos()

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Identificando oportunidades de arbitragem...")
            oportunidades = identificar_arbitragem(precos_por_exchange, percentual_arbitragem, liquidez_minima)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if oportunidades:
                print(f"[{timestamp}] Oportunidades de arbitragem encontradas:\n")

                # Carregar a blacklist para fazer a verificação de pares inválidos
                blacklist = carregar_blacklist()

                # Verificar as oportunidades e remover as inválidas
                for oportunidade in oportunidades[:]:  # Itera sobre uma cópia da lista
                    par = oportunidade['par']
                    exchange_compra = oportunidade['compra']
                    exchange_venda = oportunidade['venda']

                    # Verifica se o par está na blacklist para a exchange de compra ou venda
                    if par in blacklist:
                        if exchange_compra in blacklist[par] or exchange_venda in blacklist[par]:
                            oportunidades.remove(oportunidade)  # Remove da lista original

                if oportunidades:
                    for oportunidade in oportunidades:
                        spread_percentual_medio, volume_acumulado_usdt = calcular_spread_medio(oportunidade, volume_arbitragem_usdt)
                        if spread_percentual_medio >= percentual_arbitragem and spread_percentual_medio <= percentual_max_arbitragem:
                            print(f"{oportunidade['par']} | {oportunidade['compra']} --> {oportunidade['venda']}")
                            #print(f"       Comprar em {oportunidade['compra']}: Preço = {oportunidade['ask_compra']:.4f} USDT, Liquidez = {oportunidade['liquidez_compra']:.2f} USDT")
                            #print(f"       Vender em {oportunidade['venda']}: Preço = {oportunidade['bid_venda']:.4f} USDT, Liquidez = {oportunidade['liquidez_venda']:.2f} USDT")
                            print(f"        Spread: {oportunidade['spread_percentual']:.2f}%")
                            print(f"        Spread médio: {spread_percentual_medio:.2f}%")
                            print(f"        Volume acumulado: {volume_acumulado_usdt:.2f} USDT")
                            print("- " * 30)
                            # Exibe o livro de ordens apenas para a corretora de compra
                            if oportunidade['livro_ordens_compra']:
                                volume_compra_usdt_total = 0
                                print(f"    Livro de Ordens (Compra) na {oportunidade['compra']}:")
                                for ask in oportunidade['livro_ordens_compra']['asks']:
                                    preco, volume = ask
                                    volume_usdt = round(preco * volume, 1)  # Calcula o volume em USDT
                                    volume_compra_usdt_total += volume_usdt
                                    print(f"        Preço: {preco}, Volume: {volume}, Volume USDT: {volume_usdt}")
                                print(f"\n        Volume USDT total de compra: {volume_compra_usdt_total:.2f}")
                            print("- " * 30)
                            # Exibe o livro de ordens apenas para a corretora de venda
                            if oportunidade['livro_ordens_venda']:
                                volume_venda_usdt_total = 0
                                print(f"    Livro de Ordens (Venda) na {oportunidade['venda']}:")
                                for bid in oportunidade['livro_ordens_venda']['bids']:
                                    preco, volume = bid
                                    volume_usdt = round(preco * volume, 1)  # Calcula o volume em USDT
                                    volume_venda_usdt_total += volume_usdt
                                    print(f"        Preço: {preco}, Volume: {volume}, Volume USDT: {volume_usdt}")
                                print(f"\n        Volume USDT total de venda: {volume_venda_usdt_total:.2f}")
                            print("-" * 60)
                
            else:
                print(f"[{timestamp}] Nenhuma oportunidade de arbitragem encontrada.\n")

        except Exception as e:
            print(f"Erro durante a execução: {e}")

        # Aguarda um tempo antes de verificar novamente
        print("-" * 60)
        time.sleep(180)

if __name__ == "__main__":
    main()