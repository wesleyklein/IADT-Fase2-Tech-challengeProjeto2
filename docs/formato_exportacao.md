# Formato de exportação

O JSON usa `schema_version: 1.0`, data ISO-8601, cenário, algoritmo, configuração, indicador parcial, resumo, rotas, paradas e entregas não atendidas. Enums são serializados como texto. Cada exportação recebe nome único.

O CSV `results/experiments.csv` recebe uma linha por execução, em UTF-8, e escreve o cabeçalho somente na criação. Arquivos em `results/` e cenários pessoais são ignorados pelo Git.
