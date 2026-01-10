import pandas as pd
import warnings
import seaborn as sns
import matplotlib.pyplot as plt
import base64
import json
from io import BytesIO
import os

warnings.filterwarnings('ignore')
sns.set_theme(style="whitegrid")

ARQUIVO_METAS = "metas.json"

def carregar_metas(ativos_da_carteira):
    if os.path.exists(ARQUIVO_METAS):
        with open(ARQUIVO_METAS, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        metas_padrao = {ativo: 0.037 for ativo in ativos_da_carteira}
        with open(ARQUIVO_METAS, 'w', encoding='utf-8') as f:
            json.dump(metas_padrao, f, indent=4)
        return metas_padrao

def agrupandoCarteira(arquivo):
    if not os.path.exists(arquivo):
        print(f"Erro: Arquivo '{arquivo}' não encontrado.")
        return pd.DataFrame()

    df_excel = pd.ExcelFile(arquivo)
    tabelas = []
    for aba in df_excel.sheet_names:
        df_temp = pd.read_excel(arquivo, sheet_name=aba).dropna()
        if not df_temp.empty:
            df_temp['Produto'] = df_temp['Produto'].astype(str).map(lambda x: x.split(' -')[0].strip())
            df_temp['Tipo'] = aba.strip()
            tabelas.append(df_temp)

    df_total = pd.concat(tabelas, ignore_index=True)
    tipos_validos = ['Fundo de Investimento', 'Tesouro Direto']
    df_total.loc[~df_total['Tipo'].isin(tipos_validos), 'Tipo'] = 'Acoes'
    df_total = df_total[df_total['Produto'] != 'Opção de Venda']

    df_total = df_total.groupby(['Tipo', 'Produto'], as_index=False).agg({'Valor Atualizado': 'sum'})

    total_geral = df_total['Valor Atualizado'].sum()
    df_total['(%) Atual'] = (df_total['Valor Atualizado'] / total_geral)
    
    metas_dic = carregar_metas(df_total['Produto'].unique())
    metas_upper = {k.upper(): v for k, v in metas_dic.items()}
    df_total['(%) Meta'] = df_total['Produto'].str.upper().map(metas_upper).fillna(0)
    
    df_total = df_total.sort_values(by=['Tipo', '(%) Atual'], ascending=[True, False])
    return df_total.set_index('Produto')

def gerar_grafico_com_labels(df, coluna_x, titulo):
    # Cálculo do percentual para os labels
    total = df["Valor Atualizado"].sum()
    df_plot = df.reset_index().copy().sort_values("Valor Atualizado", ascending=False)
    df_plot["Percentual"] = (df_plot["Valor Atualizado"] / total) * 100

    plt.figure(figsize=(8, 4.5))
    ax = sns.barplot(data=df_plot, x=coluna_x, y="Valor Atualizado", color="#2c3e50")
    
    # Adicionando os rótulos de porcentagem no topo de cada barra
    for i, p in enumerate(ax.patches):
        percentage = df_plot["Percentual"].iloc[i]
        ax.annotate(f"{percentage:.1f}%", 
                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                    ha='center', va='bottom', 
                    fontsize=10, fontweight='bold', color='black', xytext=(0, 5),
                    textcoords='offset points')

    plt.title(titulo, fontsize=13, fontweight='bold', pad=20)
    plt.xticks(rotation=30, ha="right", fontsize=9)
    plt.yticks(fontsize=9)
    plt.xlabel(""); plt.ylabel("Valor Atualizado (R$)")
    
    # Aumentar o limite superior do eixo Y para o label não cortar
    ax.set_ylim(0, ax.get_ylim()[1] * 1.15)
    
    sns.despine()
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=120)
    plt.close()
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def gerar_relatorio_html(df, arquivo_saida="relatorio_carteira.html"):
    if df.empty: return

    imagens = []
    # Gráfico Geral (Classes)
    df_tipo = df.groupby("Tipo", as_index=False)["Valor Atualizado"].sum()
    imagens.append(gerar_grafico_com_labels(df_tipo, "Tipo", "Distribuição por Classe (%)"))
    
    # Gráficos por Tipo
    for tipo in df['Tipo'].unique():
        df_sub = df[df["Tipo"] == tipo]
        imagens.append(gerar_grafico_com_labels(df_sub, "Produto", f"Composição: {tipo} (%)"))

    linhas_html = ""
    for idx, row in df.iterrows():
        p_atual = row['(%) Atual'] * 100
        p_meta = row['(%) Meta'] * 100
        falta = p_meta - p_atual
        linhas_html += f"""
        <tr class="asset-row" data-atual="{p_atual:.4f}">
            <td style="text-align: left;">{idx}</td>
            <td>R$ {row['Valor Atualizado']:,.2f}</td>
            <td>{p_atual:.2f}%</td>
            <td><input type="number" step="0.01" class="meta-input" data-ativo="{idx}" value="{p_meta:.2f}">%</td>
            <td class="col-falta" style="color: {'green' if falta > 0 else 'red'}">{falta:+.2f}%</td>
        </tr>
        """

    total_valor = df['Valor Atualizado'].sum()
    total_meta = df['(%) Meta'].sum() * 100

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; font-size: 12px; color: #333; }}
            .container {{ width: 90%; margin: auto; }}
            h2 {{ text-align: center; color: #2c3e50; margin-bottom: 20px; }}
            
            table {{ width: 80%; margin: 0 auto 30px auto; border-collapse: collapse; background: #fff; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background: #2c3e50; color: white; }}
            
            .footer-total {{ font-weight: bold; background: #f2f2f2; }}
            .meta-input {{ width: 60px; padding: 3px; border: 1px solid #ccc; text-align: center; border-radius: 3px; }}
            
            .charts-grid {{ 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 25px; 
            }}
            .chart-card {{ border: 1px solid #eee; padding: 10px; border-radius: 5px; background: #fff; }}
            .chart-card img {{ width: 100%; height: auto; }}
            
            .no-print {{ text-align: center; margin-bottom: 30px; }}
            .btn {{ background: #2c3e50; color: white; border: none; padding: 10px 25px; cursor: pointer; border-radius: 5px; font-weight: bold; font-size: 13px; }}
            .btn:hover {{ background: #34495e; }}

            @media print {{
                .no-print {{ display: none; }}
                .container, table {{ width: 100%; }}
                .charts-grid {{ gap: 10px; }}
                body {{ margin: 0; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Relatório de Rebalanceamento de Carteira</h2>
            
            <div class="no-print">
                <button class="btn" onclick="salvarMetas()">💾 Salvar metas.json</button>
                <button class="btn" onclick="window.print()">🖨️ Imprimir / PDF</button>
            </div>

            <table>
                <thead>
                    <tr><th style="text-align: left;">Ativo</th><th>Valor Atual</th><th>% Atual</th><th>% Meta</th><th>Falta</th></tr>
                </thead>
                <tbody>{linhas_html}</tbody>
                <tfoot>
                    <tr class="footer-total">
                        <td style="text-align: left;">TOTAL GERAL</td>
                        <td>R$ {total_valor:,.2f}</td>
                        <td>100.00%</td>
                        <td id="total-meta">{total_meta:.2f}%</td>
                        <td id="total-falta">{(total_meta - 100):+.2f}%</td>
                    </tr>
                </tfoot>
            </table>

            <div class="charts-grid">
                {"".join([f'<div class="chart-card"><img src="data:image/png;base64,{img}"></div>' for img in imagens])}
            </div>
        </div>

        <script>
            function recalcular() {{
                let somaMeta = 0;
                document.querySelectorAll('.asset-row').forEach(row => {{
                    const input = row.querySelector('.meta-input');
                    const colFalta = row.querySelector('.col-falta');
                    const meta = parseFloat(input.value) || 0;
                    const atual = parseFloat(row.dataset.atual);
                    const falta = meta - atual;
                    somaMeta += meta;
                    colFalta.innerText = (falta >= 0 ? '+' : '') + falta.toFixed(2) + '%';
                    colFalta.style.color = falta >= 0 ? 'green' : 'red';
                }});
                const totalFalta = somaMeta - 100;
                document.getElementById('total-meta').innerText = somaMeta.toFixed(2) + '%';
                document.getElementById('total-falta').innerText = (totalFalta >= 0 ? '+' : '') + totalFalta.toFixed(2) + '%';
                document.getElementById('total-falta').style.color = Math.abs(totalFalta) < 0.01 ? 'black' : (totalFalta > 0 ? 'green' : 'red');
            }}

            document.querySelectorAll('.meta-input').forEach(i => i.addEventListener('input', recalcular));

            function salvarMetas() {{
                const metas = {{}};
                document.querySelectorAll('.meta-input').forEach(i => metas[i.dataset.ativo] = parseFloat(i.value) / 100);
                const blob = new Blob([JSON.stringify(metas, null, 4)], {{ type: 'application/json' }});
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'metas.json';
                a.click();
            }}
        </script>
    </body>
    </html>
    """
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Relatório gerado com sucesso!")

if __name__ == "__main__":
    df_final = agrupandoCarteira("posicao.xlsx")
    if not df_final.empty:
        gerar_relatorio_html(df_final)