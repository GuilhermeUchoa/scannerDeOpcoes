from scanner import buscar_venda_put
import pandas as pd

def main():
    # --- CONFIGURAÇÃO DA BUSCA ---
    ativos = ['ABEV3', 'B3SA3', 'BBAS3', 'BBSE3', 'EGIE3', 'FLRY3', 'HYPE3', 'ITSA4', 'KLBN11', 'LEVE3', 'PETR4', 'TAEE11', 'UNIP6', 'VALE3',]

    resultados = []

    for i in ativos:
        
        res = buscar_venda_put(i, '2026-02-20', distancia_strike=0.88, valor_investido=10000)
        
        if res:
            resultados.append(res)
            print(f"{i}: Opção {res['Opção']} encontrada.")
        else:
            print(f"❌ {i}: Sem dados para esta data.")

    # DataFrame
    df = pd.DataFrame(resultados).sort_values(by='Total Prêmio',ascending=False)
    df = df.to_markdown(index=False)
    print("\n", df)

if __name__ == "__main__":
    main()
