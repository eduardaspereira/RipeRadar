# RipeRadar - README
## Sumário
[1. Notas](#1-notas)  
[2. Resumo de cada ficheiro](#2-files)  
[3. Fontes](#3-fontes)  
[4. Casos de uso](#4-casos-de-uso)  

-------------------
# [1. Notas](#1-notas)
- pedir cabo eslov(TCS34725)-eslov(Nicla Sense ME) para simular industria com menos cablagem
- camera module (OV7675) -> a forma/textura da fruta ou a presença de bolor (fungos)
- TCS34725 -> precisão cromática
- treinar Nicla Sense ME no BME AI Studio


# [2. Resumo de cada ficheiro](#2-files)
## scripts/calibracao.py
Le dados brutos do sensor de cor TCS34725 em tempo real.
Normaliza R, G e B pelo canal clear (C) e calcula a razao R/G.
Serve para calibrar perfis de fruta antes de treinar ou testar modelos.

## scripts/detetor_CORfrutas.py
Identifica fruta por distancia euclidiana entre cor atual e perfis predefinidos.
Integra leitura opcional de gas via serial (Nicla Sense ME).
Mostra predicao e confianca continuamente no terminal.

## scripts/detetor_GASESfrutas.py
Combina pistas de cor e gas com sistema de votos por fruta.
Estimativa de estado de maturacao (verde, madura, podre) por regras.
E um prototipo de logica de fusao de sensores para edge AI.

## scripts/feature_extractor.py
Percorre imagens do dataset e extrai media de R, G, B por imagem.
Calcula a feature adicional R/G ratio para reforcar separacao de classes.
Gera o ficheiro CSV sintetico usado no treino do modelo.

## scripts/train.py
Carrega o CSV de features e separa dados em treino/teste.
Treina um RandomForestClassifier para classificar tipo de fruta.
Avalia desempenho, imprime metricas e guarda o modelo em .pkl.

## scripts/live_preditor.py
Carrega o modelo treinado e recebe leituras do sensor em tempo real.
Monta as features no formato esperado e faz predicao com probabilidade.
Mostra fruta prevista e nivel de confianca no terminal.

## scripts/riperadar_synthetic_dataset.csv
Dataset tabular gerado a partir de imagens processadas.
Contem label, subtipo e features numericas (r, g, b, rg_ratio).
E a base de entrada para o treino supervisionado em train.py.

## scripts/riperadar_model.pkl
Modelo de machine learning treinado e serializado com joblib.
Usado em inferencia online no live_preditor.py.
Evita novo treino sempre que o sistema e iniciado.

[3. Fontes](#3-fontes)
Fonte github Datasets: https://github.com/Horea94/Fruit-Images-Dataset/tree/master/Test/  
Fonte kaggle Datasets: https://www.kaggle.com/datasets/moltean/fruits/code  

# [4. Casos de uso](#4-casos-de-uso)  
#### A. O Modelo "Smart Crate" (Caixa Inteligente)
Em vez de analisar fruta a fruta, o sistema é instalado na própria caixa de transporte ou na prateleira do supermercado.  
- Como funciona: Os sensores (Nicla Sense ME para gases e temperatura) monitorizam o ambiente da caixa inteira.  
- Vantagem: Se uma única fruta começa a apodrecer, ela liberta gases que o sistema deteta precocemente. O sistema avisa o funcionário: "A Caixa 42 tem uma fruta a começar a estragar-se, verifique agora". Isto evita que a podridão se espalhe ("uma maçã podre estraga o cesto").

#### B. Triagem em Tapete Rolante (Centro de Distribuição)
Isto aplica-se antes da fruta chegar ao supermercado, nos centros logísticos.  
- Como funciona: As frutas passam por um tapete de alta velocidade. O Raspberry Pi 5 processa as imagens (cor) e dados em milissegundos.  
- Vantagem: Aqui, o braço empurra a fruta detetada como "Spoiling" ou "Rotten" para fora da linha de produção automaticamente, sem intervenção humana.  

# [5. Extras](#5-extras)  
#### O "Price-Optimizer" Dinâmico (Varejo Inteligente)
Em vez de usares o atuador para separar a fruta, ligas o sistema ao inventário do supermercado.  
- O Conceito: À medida que o Raspberry Pi 5 detecta que um lote de fruta está a passar de "Ripe" (Maduro) para "Spoiling" (A iniciar deterioração), o sistema comunica com etiquetas de preço eletrónicas.  
- Utilidade Real: O preço da fruta desce automaticamente 20% ou 30% em tempo real para incentivar a venda imediata.  
- Por que é "Premium": Ataca diretamente o prejuízo financeiro das superfícies comerciais e promove o desperdício zero. Estás a usar a Edge AI do Pi 5  para tomar decisões económicas.  


#### O "Acoustic Health" Scanner (Invisível ao Olho)
Muitas vezes a fruta parece boa por fora, mas está "farinhenta" ou a fermentar por dentro.  
- O Conceito: Maximizar o uso do Nicla Voice. Criar um sistema de percussão leve (um pequeno "toque" mecânico) e usar o sensor acústico para captar a ressonância do fruto.
- Utilidade Real: Frutas como a melancia ou a maçã mudam a sua assinatura sonora conforme a densidade interna e o nível de sumo.
- Por que é "Premium": A detecção visual (cor) é comum. A detecção acústica para prever a textura interna usando Machine Learning no Raspberry Pi é algo que raramente se vê em protótipos.


#### Contentor de Atmosfera Ativa (Logística de Exportação)
Transformar o projeto num sistema de preservação ativa, não apenas detecção.
- O Conceito: Usar a Nicla Sense ME para monitorizar níveis de gás etileno e humidade dentro de um contentor.
- Ação Inteligente: Se o sensor detectar um pico de gás etileno (sinal de que uma fruta está a amadurecer e a "contagiar" as outras) , a Portenta C33 ativa a ventoinha  para purificar o ar ou injetar CO2 para travar o amadurecimento.
- Por que é "Premium": Deixa de ser um sensor passivo para ser um sistema de controlo ambiental autónomo que salva toneladas de carga em navios cargueiros.

#### Algoritmo de "Time-to-Waste" (TTW)
Em vez de dizer apenas "a fruta está podre", criar um modelo preditivo que diga: "Esta prateleira tem 48 horas de vida útil restante antes de se tornar invendável". Isto permite ao gestor do supermercado planear promoções com antecedência, e não apenas quando a fruta já está má.

#### Dashboard de Saúde do Lote (Edge Interface)
Ao usar Raspberry Pi 5, podemos criar um pequeno servidor local (Flask/FastAPI) que mostre um mapa de calor das prateleiras. Os funcionários poderiam ver num tablet quais as zonas que precisam de rotação de stock prioritária

#### Integração com Humidade e Temperatura
Fruta que amadurece depressa aumenta a temperatura local (respiração celular). Cruzar os dados de gás do Nicla Sense ME com o gradiente de temperatura. Se o etileno sobe e a temperatura também, temos uma confirmação dupla de que o lote está a "aquecer" (deteriorar-se)


# Como simular Gás
- Simular Fermentação: Usar um pano embebido em vinagre (ácido acético) ou álcool (etanol) perto do sensor. Estes gases são subprodutos comuns da fruta a passar do ponto.
- Concentração Rápida: Colocar uma única maçã num frasco fechado com o sensor durante 1 hora. A concentração de gases subirá rapidamente, permitindo-te ver se o sensor reage.
- Acende um fósforo e apaga-o rapidamente perto da caixa de fruta para criar fumo. Mostra como a ventoinha embutida "suga" o fumo exatamente para onde está o sensor Nicla Sense ME.

# Como simular Som
- Usar objetos de densidades diferentes para calibrar o Nicla Voice antes de passares para a fruta: uma bola de golfe (muito firme), uma bola de ténis (firme/ripe) e uma esponja húmida (podre).

# Como simular Cor
Em vez de esperar dias, usar cartões de cor impressos com os tons exatos de castanho e amarelo das frutas para testar o sensor TCS34725.
- Correlação real entre a oxidação química e a mudança cromática captada pelo TCS34725


# ideias pro codigo
1. Spoilage Score
```python  
Spoilage Score =
 0.4 * VOC index
+0.3 * vision spoilage
+0.2 * temp deviation
+0.1 * humidity
```

2. dashboard 
```
Shelf 3 — Apples
Freshness score: 82%

Predicted spoilage:
18 hours

Recommendation:
discount 20%
```
- mapa da loja
- alertas push
- previsão de desperdício
- Retail ROI analysis : Food waste ↓ 20-30%


3. Sistema aprende baseline da loja.
4. Active sampling fan control para evitar saturação de sensor, ruído ambiental
