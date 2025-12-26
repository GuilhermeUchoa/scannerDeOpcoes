import requests
import yfinance as yf
import pandas as pd # Opcional: para visualizar melhor no final
import datetime

def buscar_venda_put(ativo, data_vencimento, valor_investido=12000, distancia_strike=0.80):
    # Configuração de conexão (Headers e Cookies do seu navegador)
    cookies = {
        '_gid': 'GA1.3.721123878.1766674907',
        '.AspNetCore.Antiforgery.g1ir8UL7PVw': 'CfDJ8PB93EeIUJdKtD-b-s3_nBbWvt39IFdasNe93aOAl6wmMHrxy3_zxDF0MB_PemjuSvMAQwGQddnfzQkAHjYNEixzpVZqgKT7d_LEuF57IqBQO6OWxG1bigOJk_elz5D-qawLrIPBuB8WUEPgyXdzmyo',
        '_ga': 'GA1.3.916223412.1764780575',
        '_ga_YH2ELJFQPC': 'GS2.3.s1766763605$o10$g0$t1766763605$j60$l0$h0',
        '.AspNetCore.Identity.Application': 'CfDJ8PB93EeIUJdKtD-b-s3_nBYa2c8jYKnRrJpllz852UEmP8_sEXjoynHU7c4dE8J9eDQVNLKSgya8AhvAMsnqkTua9FyJd4-2UeWXnKnd6AjQzmUQmEMQgnZBylzG2R0NMho3VPDvGzCZdCrXRhm-0XYNLs9eJlTqPrkKBFKWMRlHgavXCFcEbJ7pUfo4P963iCBvTtEVzaJkg5JlAJWXnRmAYSxIjjZzvfvMOs8xgFHEPzEvtBRlccp9bVYlDaN2eJ63M-sTkEPPubK6oBD7X8NuTXLpJxVfXnw15JOdYqNF-1RCqo1NoM9T4PCgCEBzwHI_EaNd3UlZ-YW02LOb0wfl8XFha9F8fS02VW8YEa5mQuCs-kFDSQp7jQLb07ZnbMGyuviI4CdEJXRqywyeb-JLHX-QjfZjAKcEjCkWX_P7lN8hI8mTiMsHC-Cir6KXdV3wCngyfysxmALeHLp2DruX8Jru23uLtFClOJG6M9yhlc9O6E-eiaM06Ar4Npt7L0TGSt47MUf36_7T9WVIIjl77CHGSvIQzEI_sge1JmkWTa4caNUkvITTTGa7zwrrzMS84fw_8aYaRxJeYoMKrxAX0bA0Evkjz7HztaUw-6Q3GRsSq9CkiJZvw_earfaCbE2bCHC6RPk7-L24Y3_lRAuW812Bd09nQrmJtJSqJydI3nzCJsCOhbeuSkXNwalPUw',
    }
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }
    
    # A dataReferencia no site costuma ser o dia atual ou último fechamento
    # Se der erro de "success: false", tente fixar uma data de pregão recente aqui
    params = {'idAcao': ativo, 'dataReferencia': datetime.datetime.now().strftime('%Y-%m-%d')} 

    try:
        url = 'https://opcoes.net.br/listaopcoes/todas'
        response = requests.get(url, params=params, cookies=cookies, headers=headers)
        dados_json = response.json()
        
        if not dados_json.get('success'):
            return None

        # 1. Preço atual do ativo
        ticker = yf.Ticker(f"{ativo}.SA")
        preco_atual = ticker.info.get('bid') or ticker.info.get('currentPrice')
        if not preco_atual: return None

        # 2. Localizar a data de vencimento no JSON
        cadeia_puts = dados_json['optionsChain']['PUT'].get(data_vencimento)
        if not cadeia_puts:
            return None # Data não disponível para este ativo específico

        # 3. Lógica do Strike mais próximo
        strikes_dict = cadeia_puts['strikes']
        alvo = preco_atual * distancia_strike
 
        # Converte strikes para float e acha o mais próximo do alvo
        strikes_float = [float(s.replace(',', '.')) for s in strikes_dict.keys()]
        strike_escolhido = min(strikes_float, key=lambda x: abs(x - alvo))
        
        # Recupera os dados usando a chave original (string com vírgula)
        chave_original = str(strike_escolhido).replace('.', ',')
        # Pequeno ajuste caso o replace simples falhe em números redondos (ex: 30.0 -> 30)
        if chave_original not in strikes_dict:
             chave_original = f"{strike_escolhido:.2f}".replace('.', ',').replace(',00', '')

        dados_op = strikes_dict.get(chave_original)
        if not dados_op: return None

        premio = float(dados_op[3].replace(',', '.')) if dados_op[3] else 0.0
        qnt_lote = int((valor_investido / preco_atual) // 100) * 100

        return {
            "Ativo": ativo,
            "Opção": dados_op[0],
            "Strike": strike_escolhido,
            "Preço Atual": preco_atual,
            "Prêmio Unit.": premio,
            "Qtd": qnt_lote,
            "Total Prêmio": round(qnt_lote * premio, 2)
        }

    except Exception as e:
        print(f"Erro em {ativo}: {e}")
        return None

