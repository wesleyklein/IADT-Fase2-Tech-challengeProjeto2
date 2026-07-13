# Análise 

Os quatro novos JSONs adicionam a configuração genética com probabilidade de mutação de 0,15 no cenário de alta demanda.

Porém, novamente existem apenas duas soluções únicas:

- um resultado do algoritmo genético;
- um resultado da heurística;
- cada resultado foi exportado duas vezes.

Os arquivos genéticos possuem a mesma semente `2993089580`, mesmo custo, mesmas rotas e mesmo tempo. O mesmo acontece com os dois arquivos heurísticos.

## 1. Comparação das três taxas de mutação

| Métrica | Mutação 0,10 | Mutação 0,15 | Mutação 0,20 |
|---|---:|---:|---:|
| Custo objetivo | 1.085,80 | 1.113,46 | 1.086,76 |
| Distância total | 479,42 km | 476,98 km | 482,90 km |
| Duração agregada | 812,56 min | 807,73 min | 816,70 min |
| Atraso | 0 min | 0 min | 0 min |
| Entregas | 30 | 30 | 30 |
| Não atribuídas | 0 | 0 | 0 |
| Tempo de execução | 57,92 s | 46,53 s | 40,21 s |
| Maior rota | 179,02 min | 196,12 min | 178,48 min |
| Desvio entre rotas | 12,27 min | 21,90 min | 10,56 min |

Os dados anteriores de mutação 0,10 e 0,20 estão nos resultados já analisados.

### Classificação por custo objetivo

1. Mutação 0,10: 1.085,80
2. Mutação 0,20: 1.086,76
3. Mutação 0,15: 1.113,46

A diferença entre 0,10 e 0,20 é mínima: somente 0,09%.

Já a mutação 0,15 ficou aproximadamente 2,55% acima do melhor resultado.

## 2. A mutação 0,15 percorreu a menor distância

Um ponto interessante é que a mutação 0,15 encontrou:

- a menor distância;
- a menor duração agregada;
- nenhuma entrega atrasada;
- nenhuma violação de capacidade;
- nenhuma violação de autonomia.

Mesmo assim, teve o pior custo entre as três soluções genéticas.

Isso acontece porque a função objetivo não considera somente distância.

### Decomposição do custo

| Componente | Mutação 0,10 | Mutação 0,15 | Mutação 0,20 |
|---|---:|---:|---:|
| Distância | 479,42 | 476,98 | 482,90 |
| Chegada ponderada por prioridade | 581,82 | 592,68 | 582,74 |
| Penalidade de atraso | 0,00 | 0,00 | 0,00 |
| Penalidade de balanceamento | 24,55 | 43,79 | 21,12 |
| Custo total | 1.085,80 | 1.113,46 | 1.086,76 |

A mutação 0,15 economizou:

- 2,44 km em relação à mutação 0,10;
- 5,91 km em relação à mutação 0,20.

Mas perdeu mais pontos em outros critérios:

- entregas prioritárias chegaram, em média ponderada, um pouco mais tarde;
- houve maior desbalanceamento entre os veículos.

Portanto, o ganho de distância não compensou a pior distribuição temporal das rotas.

## 3. Problema de balanceamento da mutação 0,15

As durações de suas rotas foram:

| Veículo | Duração |
|---|---:|
| Moto 1 | 148,29 min |
| Moto 2 | 131,13 min |
| Van 1 | 171,58 min |
| Van 2 | 196,12 min |
| Van 3 | 160,61 min |

A diferença entre a rota mais curta e a mais longa foi de aproximadamente:

`196,12 − 131,13 = 64,99` minutos

Nas outras configurações:

| Mutação | Menor rota | Maior rota | Diferença |
|---|---:|---:|---:|
| 0,10 | 141,51 min | 179,02 min | 37,51 min |
| 0,15 | 131,13 min | 196,12 min | 64,99 min |
| 0,20 | 146,18 min | 178,48 min | 32,30 min |

A mutação 0,20 apresentou o melhor balanceamento.

## 4. Duração agregada não é o tempo real da operação

A mutação 0,15 possui a menor duração agregada, com 807,73 minutos. Porém, como os cinco veículos trabalham simultaneamente, o tempo necessário para concluir toda a operação é determinado pela rota mais longa.

Assim, o tempo operacional aproximado seria:

| Configuração | Término da última rota |
|---|---:|
| Mutação 0,10 | 179,02 min |
| Mutação 0,15 | 196,12 min |
| Mutação 0,20 | 178,48 min |
| Heurística | 238,58 min |

Portanto, mesmo tendo a menor soma das durações, a mutação 0,15 terminaria a operação aproximadamente:

- 17,10 minutos depois da mutação 0,10;
- 17,63 minutos depois da mutação 0,20.

Isso reforça que, para esse problema, vale acompanhar também o *makespan*, isto é, o tempo da maior rota.

## 5. Mutação 0,15 contra heurística

| Métrica | Genético 0,15 | Heurística |
|---|---:|---:|
| Custo objetivo | 1.113,46 | 3.713,70 |
| Distância | 476,98 km | 573,83 km |
| Duração agregada | 807,73 min | 933,31 min |
| Maior rota | 196,12 min | 238,58 min |
| Atraso | 0 min | 47,15 min |
| Entregas | 30 | 30 |
| Tempo de processamento | 46,53 s | 0,0080 s |

Mesmo sendo o pior dos três resultados genéticos, a mutação 0,15 ainda foi muito superior à heurística:

- custo 70,02% menor;
- distância 16,88% menor;
- duração agregada 13,46% menor;
- maior rota 17,80% menor;
- nenhum atraso.

A heurística continua produzindo exatamente a mesma solução, independentemente de a configuração exibir mutação 0,10, 0,15 ou 0,20, porque esse parâmetro não é utilizado por ela.

## Conclusão atualizada

Entre as execuções disponíveis:

- melhor custo: mutação 0,10;
- menor distância: mutação 0,15;
- menor duração agregada: mutação 0,15;
- melhor balanceamento: mutação 0,20;
- menor tempo de execução genética: mutação 0,20;
- melhor tempo para concluir toda a operação: mutação 0,20;
- todas as configurações genéticas: zero atraso e todas as entregas realizadas.

Para apresentação do trabalho, a mutação 0,20 pode ser considerada o melhor compromisso geral, porque seu custo ficou somente 0,09% acima do melhor, executou mais rápido e apresentou o melhor equilíbrio entre as rotas. A mutação 0,10 continua sendo a vencedora estritamente pela função objetivo, mas a diferença entre ambas é praticamente irrelevante diante de apenas uma semente por configuração.