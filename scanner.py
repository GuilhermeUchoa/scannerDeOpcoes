import requests
import yfinance as yf
import pandas as pd
import datetime


def buscar_venda_put(ativo, data_vencimento, valor_investido=10000, distancia_strike=0.80):
    # Configuração de conexão (Lembre-se de atualizar os cookies se expirarem)
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

    params = {'idAcao': ativo,
              'dataReferencia': datetime.datetime.now().strftime('%Y-%m-%d')}

    try:
        # 0. Request dos dados
        url = 'https://opcoes.net.br/listaopcoes/todas'
        response = requests.get(
            url, params=params, cookies=cookies, headers=headers)
        dados_json = response.json()

        # 1. Preço atual do ativo (mais robusto)
        ticker = yf.Ticker(f"{ativo}.SA")
        hist = ticker.history(period="1d")
        if not hist.empty:
            preco_atual = hist['Close'].iloc[-1]
        else:
            preco_atual = ticker.info.get('bid') or ticker.info.get('currentPrice')

        if not preco_atual:
            return None

        # 2. Localizar a cadeia de PUTs
        cadeia_total = dados_json['optionsChain']['PUT'].get(data_vencimento)
        if not cadeia_total:
            return None

        strikes_dict = cadeia_total['strikes']
        alvo = preco_atual * distancia_strike

        # 3. Filtrar strikes que POSSUEM prêmio e encontrar o mais próximo
        # O prêmio está no índice [3] do array de valores de cada strike
        opcoes_validas = []
        for chave, valores in strikes_dict.items():
            premio_str = valores[3]
            if premio_str is not None:
                strike_f = float(chave.replace(',', '.'))
                opcoes_validas.append((strike_f, chave, valores))

        if not opcoes_validas:
            return None

        # Encontra o strike cuja diferença para o alvo seja a menor possível
        strike_escolhido_f, chave_original, dados_op = min(opcoes_validas, key=lambda x: abs(x[0] - alvo))

        # 4. Cálculos finais
        premio = float(dados_op[3].replace(',', '.'))
        qnt_lote = int((valor_investido / strike_escolhido_f) // 100) * 100
        if qnt_lote == 0:
            qnt_lote = 100  # Garante lote mínimo

        return {
            "Ativo": ativo,
            "Opcao": dados_op[0],
            "Strike": f"R$ {strike_escolhido_f:.2f}",
            "Preco Atual": f"R$ {preco_atual:.2f}",
            "Distancia": f"{round(strike_escolhido_f/preco_atual, 2)}",
            "Premio Unit.": f"R$ {premio:.2f}",
            "Strike - Premio Unit.": f"R$ {round(strike_escolhido_f - premio, 2)}",
            "Qtd": qnt_lote,
            "Rentabilidade": round((premio / strike_escolhido_f) * 100, 2),
            "Total Premio": round(qnt_lote * premio, 2)
        }

    except Exception as e:
        print(f"Erro em {ativo}: {e}")
        return None


def execVendaDePutOpcoes(distancia_strike):
    ativos = ['ABEV3', 'B3SA3', 'BBAS3', 'BBSE3', 'EGIE3', 'FLRY3', 'HYPE3', 'ITSA4', 'KLBN11',
              'LEVE3', 'PETR4', 'TAEE11', 'UNIP6', 'VALE3', 'WEGE3', 'AGRO3', 'TUPY3', 'WIZC3']
    resultados = []

    if distancia_strike > 1:
        texto = "ITM"
    elif distancia_strike < 1:
        texto = "OTM"
    else:
        texto = "ATM"

    data_vencimento = '2026-02-20'
    valor_investido = 10000

    print(
        f"--- Buscando: {distancia_strike} ({texto}) | Vencimento: {data_vencimento} ---")

    for i in ativos:
        res = buscar_venda_put(i, data_vencimento=data_vencimento,
                               distancia_strike=distancia_strike, valor_investido=valor_investido)
        if res:
            resultados.append(res)
        else:
            print(f"{i}: Sem opções com prêmio nesta data.")

    if resultados:
        df = pd.DataFrame(resultados).sort_values(
            by='Rentabilidade', ascending=False)
        print(df.to_markdown(index=False))
        print("\n")
    else:
        print("Nenhum dado encontrado para os parâmetros selecionados.\n")


if __name__ == "__main__":
    # Execução das faixas desejadas
    for d in [0.8, 0.85, 0.9, 0.95, 1, 1.1, 1.15, 1.2, 1.15]:
        execVendaDePutOpcoes(distancia_strike=d)
