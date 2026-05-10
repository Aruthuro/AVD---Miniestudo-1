# AVD---Miniestudo-1

Repositório do miniestudo, contendo informações diversas sobre o projeto.

O relatório desse trabalho esta armazenado no arquivo [Miniestudo_1_Baseline](Miniestudo_1_Baseline.pdf) e pode ser encontrado no [link do relatório](https://docs.google.com/document/d/14JUjP78j_OumdTUqtJR9KITf6nIWF5jE/edit?usp=sharing&ouid=100189718658241827513&rtpof=true&sd=true).

## Pasta ``consultas``

Essa pasta armazena as 80 consultas (40 para cada sistema) usadas no estudo, em dois arquivos JSON.

## Pastas ``resultados_sys_art`` e ``resultados_sys_gio``

Cada pasta armazena os dados coletados do sistema referenciado pelo seu nome (baseline_postgres.csv), além de informações do sistema no momento da coleta (``metadata_sistema_giovana.json`` ou ``metadata_sistema_arthur.json``) e métricas do SGBD para cada consulta (``planos_sistema_arthur.txt`` ou  ``planos_sistema_giovana.txt``).

## Arquivo ``coletor_benchmarking_BD.py``

Arquivo com a definição de uma classe usada para coletar e registrar as informações dos experimentos. Esse código é incluído no escopo do sistema a ser medido, possibilitando a criação de um objeto com métodos para carregar as consultas de um arquivo específico, realizar consultas, fazer medições e salvar essas informações em arquivos (como informações do sistema, planos e uso de disco e cache do SGBD e as amostras).

## Arquivo ``mini_estudo.ipynb``

Notebook jupyter usado para o calculo das estatísticas e plot dos gráficos usados no relatório.