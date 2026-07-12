# Fitness hospitalar

O custo minimizado é a soma de distância, chegada ponderada pela prioridade, atraso ponderado, excesso de capacidade, excesso de autonomia, não atendimento e desequilíbrio das durações. Os pesos ficam em `HospitalFitnessWeights` e pertencem ao cenário; JSONs antigos recebem os defaults.

Entregas críticas têm peso 5, altas 3 e regulares 1. Atrasos usam multiplicadores próprios. Soluções só são viáveis quando não há entregas pendentes nem excessos além da tolerância numérica de `1e-9`.
