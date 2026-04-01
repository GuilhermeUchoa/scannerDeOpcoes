import pandas as pd
import warnings
import seaborn as sns
import matplotlib.pyplot as plt
import base64
import json
from io import BytesIO
import os

warnings.filterwarnings('ignore')
sns.set_theme(style="white")

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
            df_temp['Produto'] = df_temp['Produto'].astype(
                str).map(lambda x: x.split(' -')[0].strip())
            df_temp['Tipo'] = aba.strip()
            tabelas.append(df_temp)

    df_total = pd.concat(tabelas, ignore_index=True)
    tipos_validos = ['Fundo de Investimento', 'Tesouro Direto']
    df_total.loc[~df_total['Tipo'].isin(tipos_validos), 'Tipo'] = 'Ações'

    df_total = df_total.groupby(['Tipo', 'Produto'], as_index=False).agg({
        'Valor Atualizado': 'sum'})
    total_geral = df_total['Valor Atualizado'].sum()
    df_total['(%) Atual'] = (df_total['Valor Atualizado'] / total_geral)

    metas_dic = carregar_metas(df_total['Produto'].unique())
    metas_upper = {k.upper(): v for k, v in metas_dic.items()}
    df_total['(%) Meta'] = df_total['Produto'].str.upper().map(
        metas_upper).fillna(0)

    return df_total.sort_values(by=['Tipo', '(%) Atual'], ascending=[True, False])


def gerar_grafico_comparativo(df):
    df_plot = df.melt(id_vars='Produto', value_vars=['(%) Atual', '(%) Meta'],
                      var_name='Tipo_Perc', value_name='Valor')
    df_plot['Valor'] = df_plot['Valor'] * 100

    plt.figure(figsize=(12, 6))
    ax = sns.barplot(data=df_plot, x='Produto', y='Valor',
                     hue='Tipo_Perc', palette=['#34495e', '#3498db'])

    plt.title("Comparativo: Atual vs Meta (%)",
              fontsize=14, fontweight='bold', pad=20)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.ylabel("Percentual (%)")
    plt.xlabel("")
    plt.legend(title="")
    sns.despine()
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=100)
    plt.close()
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def gerar_relatorio_html(df, arquivo_saida="dashboard_investimentos.html"):
    if df.empty:
        return

    grafico_comp = gerar_grafico_comparativo(df)
    total_valor = df['Valor Atualizado'].sum()
    total_ativos = len(df)

    linhas_html = ""
    for _, row in df.iterrows():
        p_atual = row['(%) Atual'] * 100
        p_meta = row['(%) Meta'] * 100
        aporte = ((p_meta / 100) * total_valor) - row['Valor Atualizado']

        margem = p_meta * 0.1
        if p_atual < (p_meta - margem):
            status, color = "COMPRAR", "#27ae60"
        elif p_atual > (p_meta + margem):
            status, color = "REDUZIR", "#e67e22"
        else:
            status, color = "AGUARDAR", "#7f8c8d"

        linhas_html += f"""
        <tr class="asset-row" data-tipo="{row['Tipo']}" data-valor-atual="{row['Valor Atualizado']:.2f}">
            <td><a href="javascript:void(0)" onclick="abrirGraficoSuspenso(event, '{row['Produto']}')" style="color:#3498db; font-weight:bold; cursor:pointer; text-decoration:none;">{row['Produto']}</a></td>
            <td><span class="type-badge">{row['Tipo']}</span></td>
            <td data-order="{row['Valor Atualizado']}">R$ {row['Valor Atualizado']:,.2f}</td>
            <td data-order="{p_atual}">{p_atual:.2f}%</td>
            <td><input type="number" step="0.01" class="meta-input" data-ativo="{row['Produto']}" value="{p_meta:.2f}">%</td>
            <td class="col-aporte" data-order="{aporte}" style="font-weight: bold;">R$ {aporte:,.2f}</td>
            <td><span class="status-badge" style="background: {color}">{status}</span></td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="utf-8">
        <title>Dashboard de Rebalanceamento</title>
        <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        
        <style>
            :root {{ --primary: #2c3e50; --secondary: #3498db; --bg: #f8f9fa; --text-muted: #718096; }}
            body {{ font-family: 'Inter', sans-serif; background-color: var(--bg); margin: 0; padding: 20px; color: #2d3436; }}
            .container {{ max-width: 1300px; margin: auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
            .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }}
            .card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); border: 1px solid #edf2f7; }}
            .card h3 {{ margin: 0; font-size: 14px; color: var(--text-muted); text-transform: uppercase; }}
            .card p {{ margin: 10px 0 0; font-size: 24px; font-weight: 700; color: var(--primary); }}
            
            /* TABELA E CONTEÚDO PRINCIPAL */
            .main-content {{ background: white; padding: 25px; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
            table.dataTable {{ border: none !important; margin-top: 20px !important; }}
            .meta-input {{ width: 60px; padding: 5px; border: 1px solid #e2e8f0; border-radius: 6px; text-align: center; font-weight: 600; }}
            .type-badge {{ background: #edf2f7; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; color: #4a5568; }}
            .status-badge {{ color: white; padding: 5px 10px; border-radius: 20px; font-size: 10px; font-weight: 800; }}
            
            /* BOTÕES DE FILTRO BONITOS */
            .filter-group {{ margin-bottom: 25px; display: flex; gap: 10px; border-bottom: 1px solid #edf2f7; padding-bottom: 15px; }}
            .btn-filter {{ 
                background: #fff; 
                border: 1px solid #e2e8f0; 
                padding: 8px 18px; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 14px; 
                font-weight: 500;
                color: var(--text-muted);
                transition: all 0.2s ease;
            }}
            .btn-filter:hover {{ background: #f7fafc; border-color: #cbd5e0; }}
            .btn-filter.active {{ 
                background: var(--secondary); 
                color: white; 
                border-color: var(--secondary);
                box-shadow: 0 4px 12px rgba(52, 152, 219, 0.2);
            }}

            /* BOTÕES DE AÇÃO */
            .btn {{ background: var(--primary); color: white; border: none; padding: 10px 18px; cursor: pointer; border-radius: 8px; font-weight: 600; font-size: 14px; transition: 0.2s; }}
            .btn-save {{ background: var(--secondary); }}
            
            /* GRÁFICO SUSPENSO */
            #floating-chart-container {{
                display: none;
                position: absolute;
                z-index: 9999;
                width: 700px;
                height: 450px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.25);
                border: 1px solid #edf2f7;
                padding: 12px;
            }}
            .close-chart {{
                position: absolute;
                top: -12px;
                right: -12px;
                width: 30px;
                height: 30px;
                background: #e74c3c;
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-weight: bold;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Dashboard de Carteira</h1>
                <div class="no-print">
                    <button class="btn btn-save" onclick="salvarMetas()">💾 Salvar Metas</button>
                    <button class="btn" onclick="window.print()">🖨️ Exportar PDF</button>
                </div>
            </div>

            <div class="summary-grid">
                <div class="card"><h3>Patrimônio Total</h3><p>R$ {total_valor:,.2f}</p></div>
                <div class="card"><h3>Ativos Monitorados</h3><p>{total_ativos}</p></div>
                <div class="card"><h3>Status Geral</h3><p id="total-meta-info">Carregando...</p></div>
            </div>

            <div class="main-content">
                <div class="filter-group">
                    <button class="btn-filter active" onclick="filtrar('Tudo', this)">Todos ativos</button>
                    <button class="btn-filter" onclick="filtrar('Ações', this)">Ações</button>
                    <button class="btn-filter" onclick="filtrar('Fundo de Investimento', this)">Fundos</button>
                    <button class="btn-filter" onclick="filtrar('Tesouro Direto', this)">Renda Fixa</button>
                </div>
                
                <table id="portfolioTable" class="display compact borderless">
                    <thead>
                        <tr>
                            <th>Produto</th>
                            <th>Classe</th>
                            <th>Valor Atual</th>
                            <th>% Atual</th>
                            <th>% Meta</th>
                            <th>Aporte Necessário</th>
                            <th>Sugestão</th>
                        </tr>
                    </thead>
                    <tbody>{linhas_html}</tbody>
                </table>
            </div>

            <div class="chart-section" style="margin-top: 30px; display: flex; justify-content: center;">
                <div class="card" style="width: 100%; text-align: center;">
                    <h3>Distribuição Atual vs Meta</h3>
                    <img src="data:image/png;base64,{grafico_comp}" style="max-width: 100%;">
                </div>
            </div>
        </div>

        <div id="floating-chart-container">
            <div class="close-chart" onclick="fecharGrafico()">&times;</div>
            <div id="tv-chart-inner" style="height: 100%; width: 100%;"></div>
        </div>

        <script>
            let table;
            
            function abrirGraficoSuspenso(event, ticker) {{
                const container = document.getElementById('floating-chart-container');
                const inner = document.getElementById('tv-chart-inner');
                
                let posX = event.pageX + 15;
                let posY = event.pageY + 15;

                // Evitar que o gráfico saia da tela à direita
                if (posX + 720 > window.innerWidth) posX = window.innerWidth - 750;
                
                container.style.display = 'block';
                container.style.left = posX + 'px';
                container.style.top = posY + 'px';
                
                inner.innerHTML = "";

                let symbol = ticker.includes(":") ? ticker : "BMFBOVESPA:" + ticker;

                new TradingView.widget({{
                    "autosize": true,
                    "symbol": symbol,
                    "interval": "D",
                    "timezone": "Etc/UTC",
                    "theme": "light",
                    "style": "3", // Estilo Área
                    "locale": "br",
                    "container_id": "tv-chart-inner",
                    "enable_publishing": false,
                    "hide_top_toolbar": false,
                    "hide_legend": false,
                    "save_image": false,
                    "range": "60M",
                    "studies": [
                        "STD;Stochastic"
                    ],
                    

                }});
                
                event.stopPropagation();
            }}

            function fecharGrafico() {{
                document.getElementById('floating-chart-container').style.display = 'none';
            }}

            document.addEventListener('click', function(e) {{
                const container = document.getElementById('floating-chart-container');
                if (!container.contains(e.target) && container.style.display === 'block') {{
                    fecharGrafico();
                }}
            }});

            $(document).ready(function() {{
                table = $('#portfolioTable').DataTable({{
                    paging: false,
                    info: false,
                    language: {{ search: "" , searchPlaceholder: "Buscar ativo..." }},
                    columnDefs: [{{ targets: [2, 3, 5], className: 'dt-right' }}]
                }});
                recalcular();
            }});

            function filtrar(tipo, btn) {{
                $('.btn-filter').removeClass('active');
                $(btn).addClass('active');
                if(tipo === 'Tudo') table.column(1).search('').draw();
                else table.column(1).search(tipo).draw();
            }}

            function recalcular() {{
                let totalGeral = 0;
                $('.asset-row').each(function() {{ 
                    totalGeral += parseFloat($(this).attr('data-valor-atual')) || 0; 
                }});
                
                let somaMeta = 0;
                $('.asset-row').each(function() {{
                    const row = $(this);
                    const metaPerc = parseFloat(row.find('.meta-input').val()) || 0;
                    const valorAtual = parseFloat(row.attr('data-valor-atual'));
                    const percAtual = (valorAtual / totalGeral) * 100;
                    
                    somaMeta += metaPerc;
                    const aporte = ((metaPerc / 100) * totalGeral) - valorAtual;
                    
                    const colAporte = row.find('.col-aporte');
                    colAporte.text('R$ ' + aporte.toLocaleString('pt-BR', {{minimumFractionDigits: 2}}));
                    colAporte.css('color', aporte >= 0 ? '#27ae60' : '#e74c3c');

                    const badge = row.find('.status-badge');
                    const margem = metaPerc * 0.1;
                    if (percAtual < (metaPerc - margem)) {{ badge.text('COMPRAR').css('background', '#27ae60'); }}
                    else if (percAtual > (metaPerc + margem)) {{ badge.text('REDUZIR').css('background', '#e67e22'); }}
                    else {{ badge.text('AGUARDAR').css('background', '#7f8c8d'); }}
                }});
                
                $('#total-meta-info').text(somaMeta.toFixed(1) + '% Alocado');
                $('#total-meta-info').css('color', Math.abs(somaMeta-100) > 0.1 ? '#e67e22' : '#27ae60');
            }}

            $('.meta-input').on('input', recalcular);

            function salvarMetas() {{
                const metas = {{}};
                $('.meta-input').each(function() {{ metas[$(this).data('ativo')] = parseFloat($(this).val()) / 100; }});
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
    print(f"Sucesso! Dashboard gerado em: {{os.path.abspath(arquivo_saida)}}")


if __name__ == "__main__":
    df_final = agrupandoCarteira("posicao.xlsx")
    if not df_final.empty:
        gerar_relatorio_html(df_final)
