# RipeRadar - README Resumido

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

Fonte github Datasets: https://github.com/Horea94/Fruit-Images-Dataset/tree/master/Test/  
Fonte kaggle Datasets: https://www.kaggle.com/datasets/moltean/fruits/code  
