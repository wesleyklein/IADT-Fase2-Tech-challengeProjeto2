# Exportação de resultados

O botão **Exportar resultado** fica disponível para resultados hospitalares finais, comparações e parciais após cancelamento. Uma execução simples gera um JSON detalhado e registra a execução no CSV. Uma comparação gera um JSON para o algoritmo genético, outro para a heurística e duas linhas no CSV.

O JSON inclui `schema_version`, cenário, configuração, resumo, rotas, paradas, não atendidas e `is_partial`. O CSV mantém cabeçalho único e recebe uma linha por execução. Falhas são apresentadas no painel sem fechar a aplicação.
