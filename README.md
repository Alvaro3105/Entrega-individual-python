# Alvaro — Tempo de deslocamento

**Projeto:** Números que Falam — Descobrindo o Brasil · Persona 5 (Transporte e Mobilidade Urbana)
**Pergunta da persona que esta parte responde:** P1 — mediana do tempo de deslocamento por meio de transporte × raça
**Fonte:** IBGE, Censo Demográfico 2022 — SIDRA 10330

## Arquivos
| Arquivo | O que é |
|---|---|
| `etl.py` | Coleta (API do SIDRA/IBGE) + tratamento + gravação da base tratada |
| `estatisticas.py` | Cálculos estatísticos (média, mediana, moda, quartis, IQR, amplitude, variância, desvio padrão, outliers) |
| `painel.py` | Tela no Streamlit (KPIs, gráficos, estatística, interpretação, metodologia) |
| `dados/` | Base IBGE tratada: `tempo_meio_raca_uf.csv`, `tempo_raca_municipio.csv.gz` |
| `analise.md` | Análise descritiva com os resultados e as respostas às perguntas |

## Como rodar (a partir da pasta do projeto, com o ambiente virtual ativo)
1. Baixar e tratar os dados (só precisa uma vez; os dados já estão em `dados/`):
   ```
   python -m integrante_2_alvaro.etl
   ```
2. Abrir o painel:
   ```
   streamlit run integrante_2_alvaro/painel.py
   ```

## Integração com o dashboard do grupo
O `painel.py` segue o padrão do grupo (`docs/padrao_integracao.md`): o `app.py` final chama
`carregar_dados()` e `render(dados, filtros)`.
