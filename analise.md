# Análise 02 — Tempo de deslocamento até o trabalho
**Responsável:** Alvaro · **Código:** pasta `integrante_2_alvaro/` (`etl.py`, `estatisticas.py`, `painel.py`)
**Fonte:** IBGE, Censo 2022, SIDRA 10330 · **Universo:** o mesmo da análise da Ana Karolina (66,1 milhões de trabalhadores)

> Números do **Brasil**, sem filtros.

## 1. Atenção metodológica: o tempo vem em faixas
O IBGE não informa o tempo exato de cada pessoa, só a **faixa**: até 5 min, 6 a 15, 15 a 30, 30 min a 1 h, 1 a 2 h, 2 a 4 h e mais de 4 h. Por isso usamos a **estatística para dados agrupados**:

```
Mediana ≈ Li + ((n/2 − Fant) / fi) × h
```
- **Li**: limite inferior da classe mediana.
- **Fant**: pessoas acumuladas antes dela.
- **fi**: pessoas na classe.
- **h**: largura da classe.

A fórmula supõe que, dentro da classe, as pessoas se espalham por igual. O resultado é uma **estimativa**.
**Não fazemos boxplot de pessoas**, porque não existem tempos individuais. O boxplot usa a **mediana estimada de cada município**.

## 2. KPIs
| Indicador | Valor |
|---|---|
| Mediana estimada | **21,2 min** (classe mediana: 15 a 30 min) |
| Q1 / Q3 estimados | 10,5 min / 39,5 min (IQR ≈ 29 min) |
| Média estimada* | 30,0 min |
| Mais de 1 hora | **11,0%** |
| Mais de 2 horas | **1,0%** |
| Faixa predominante (classe modal) | 15 a 30 min |
| Diferença no % acima de 1 h entre raças | **5,9 p.p.** (preta 15,1% × branca 9,2%) |

*A média usa 270 min para a classe aberta "mais de 4 h". Por isso é uma aproximação, e a **mediana é a medida principal**. A média estimada (30,0) é maior que a mediana (21,2) porque as viagens longas puxam a média para cima.

## 3. Pergunta 1 da persona: mediana (min) por meio de transporte × raça
| Meio | Branca | Preta | Parda | Amarela | Indígena |
|---|---|---|---|---|---|
| A pé | 10,6 | 14,0 | 12,5 | 9,6 | 12,9 |
| Bicicleta | 16,5 | 20,0 | 18,5 | 16,2 | 20,2 |
| Motocicleta | 14,7 | 17,5 | 15,8 | 14,6 | 16,2 |
| Automóvel | 17,8 | 22,2 | 20,2 | 20,5 | 20,9 |
| Ônibus | 43,3 | **48,1** | 46,1 | 44,3 | 46,2 |
| BRT | 59,9 | **68,5** | 64,9 | — | — |
| Trem ou metrô | 57,5 | **71,7** | 70,1 | 46,5 | 62,5 |

"—": menos de 1.000 pessoas na combinação, então a estimativa é instável e não é mostrada.
**Leitura:** em **todos** os meios principais, pessoas pretas levam mais tempo que brancas. No trem/metrô, a diferença passa de 14 minutos (71,7 × 57,5). A desigualdade não vem só da escolha do meio: ela continua dentro do mesmo meio, provavelmente porque as pessoas moram mais longe dos empregos.

## 4. Respostas às perguntas
1. **Maior tempo:** pessoas pretas (mediana de 25,0 min; 15,1% acima de 1 h). Brancas: 19,6 min e 9,2%.
2. **Meios com as faixas mais longas:** BRT (mediana de 63,9 min; 52,8% acima de 1 h), trem/metrô (63,5 min; 52,6%) e ônibus (45,4 min; 30,6%). Transporte coletivo = viagens longas.
3. **Mais deslocamentos demorados:** os grupos preto (15,1%) e pardo (11,6%).
4. **Gargalos:** periferias de regiões metropolitanas. Os municípios com maior % acima de 1 h (com pelo menos 5 mil trabalhadores) são:
   - Francisco Morato (SP), 48,0%;
   - Japeri (RJ), 45,0%;
   - Belford Roxo (RJ), 42,4%;
   - Ferraz de Vasconcelos (SP), 41,9%;
   - Santo Antônio do Descoberto (GO), 41,0%;
   - Águas Lindas de Goiás (GO), 40,8%, já no entorno de Brasília.
5. **Diferenças relevantes?** Sim. São 5,9 p.p. a mais de pessoas pretas acima de 1 h, e a diferença aparece em todos os meios.

## 5. Estatística entre municípios (1.804 municípios com pelo menos 5 mil trabalhadores)
| Medida | Mediana estimada (min) | % acima de 1 h |
|---|---|---|
| Média | 17,0 | 5,8 |
| Mediana | 15,1 | 3,7 |
| Q1 / Q3 | 13,1 / 19,1 | 2,3 / 6,4 |
| IQR | 6,0 | 4,1 |
| Amplitude | 49,0 (8,9 a 57,9) | 47,8 |
| Desvio padrão | 6,1 | 6,2 |
| Limite superior de outlier | 28,1 | 12,5 |
| Outliers | 92 municípios | 166 municípios |

Nos dois casos, a média é maior que a mediana. Os municípios-dormitório das metrópoles são os outliers e puxam a média para cima. A mediana mostra o município típico: cerca de 15 minutos.

## 6. Limitações
- As medianas são **estimativas** por classe, e a classe "mais de 4 h" é aberta.
- No nível de município, o recorte baixado não cruza tempo × meio × raça juntos.
- Cerca de 0,8% dos trabalhadores não declarou o tempo. Os percentuais são calculados entre quem declarou.

## 7. Recomendações
- Priorizar **faixas exclusivas e BRT/metrô mais rápidos** nas ligações entre periferias e centros.
- Para Ana (Goiânia) e Lucas (Brasília): o **entorno do DF em Goiás** (Águas Lindas, Santo Antônio do Descoberto, Planaltina) está entre os piores tempos do país.

## 8. Como explicar em 30 segundos
"Metade dos brasileiros leva até uns 21 minutos para chegar ao trabalho. Mas quem depende de ônibus, trem ou metrô leva de 45 a 64 minutos, e pessoas pretas levam mais tempo em todos os meios. Os piores gargalos estão nas cidades-dormitório: em Francisco Morato, quase metade dos trabalhadores leva mais de uma hora."
