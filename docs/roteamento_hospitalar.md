# Roteamento hospitalar

Cada cenário possui um depósito, entregas e uma frota heterogênea. Toda rota parte do hospital e retorna a ele. O AG evolui uma permutação de entregas; o decoder percorre essa ordem e escolhe deterministicamente o veículo viável de menor custo incremental. Capacidade e autonomia incluem o retorno. Entregas impossíveis recebem um motivo explícito e nunca desaparecem.

A heurística é determinística e serve de referência de comparação. O runner executa de forma incremental para preservar a responsividade, aceita pausa, continuação e cancelamento e mantém a melhor solução parcial disponível.
