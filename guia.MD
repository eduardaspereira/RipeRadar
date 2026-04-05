# Guião de Apresentação e Defesa: RipeRadar (Smart Shelf)
Este plano está dividido em 6 fases estratégicas. 

# Fase 1: O "Hook" (O Problema e a Visão)
- A Nossa Visão (RipeRadar):  RipeRadar como um sistema proativo. Não é um robô que separa fruta; é uma Prateleira Inteligente (Smart Shelf) que sente a fruta a amadurecer, prevê a deterioração e atua para salvar o lote.  

# Fase 2: A Evolução do Design 
- A Armadilha do Protótipo Básico: Explica que a ideia inicial era uma caixa fechada, mas que isso falha no mundo real porque a logística não permite analisar caixa a caixa.
- A Inovação Física: Mostra o design da prateleira (podes usar as imagens/diagramas da arquitetura). Destaca:A grelha de proteção embutida.A eliminação de cablagem complexa usando a ligação USB-C direta entre o Arduino Portenta C33 e o Raspberry Pi 5.

# Fase 3: A Tríade Tecnológica (Fusão de Sensores)
A genialidade está no cruzamento de dados de 3 sensores distintos.  
- O Olhar (TCS34725 - Cor): Deteta o fim do ciclo (manchas, oxidação).
- O Olfato (Nicla Sense ME / BME688 - Químico): O grande trunfo. Mede VOCs e o pico de Etileno antes de a fruta mostrar sinais de podridão visual.
- O Toque (Nicla Voice - Acústica): Analisa a frequência de resposta a um impacto mecânico leve para detetar a densidade interna (se a fruta está firme ou "farinhenta").

# Fase 4: O "Secret Sauce" (O que torna o projeto surpreendente)
1. Amostragem Ativa de Ar (Termodinâmica Aplicada)
- O Conceito: Num supermercado aberto, os gases dissipam-se.

- A Solução: Ventoinha no teto da prateleira. Ela atua como um sistema de sucção (vácuo), puxando o ar do fundo da caixa de fruta de forma constante em direção ao sensor Nicla Sense ME, garantindo uma leitura 100% precisa e eliminando pontos cegos.

2. Preservação Ativa (Controlo Ambiental)
- O Conceito: Quando a fruta madura liberta etileno, contamina as restantes.

- A Solução: Se o Raspberry Pi deteta um pico de etileno através da IA, ativa a ventoinha na velocidade máxima não para medir, mas para expulsar o gás contaminado da prateleira, prolongando a vida das outras maçãs/bananas. O detetor transforma-se num conservador.

3. Edge AI e Otimização Económica
- O Conceito: Machine Learning local.

- A Solução: O Raspberry Pi 5 cruza os dados dos 3 sensores para emitir um alerta preditivo. Este alerta pode comunicar com as etiquetas eletrónicas do supermercado para baixar o preço da fruta antes que esta se estrague (Dynamic Pricing).

# Fase 5: Metodologia de Recolha de Dados (A Prova Científica)
| Cenário de Teste | Objetivo | Método de Recolha de Dados | Dados a Extrair |
| :--- | :--- | :--- | :--- |
| Acelerador Químico | Calibrar a sensibilidade ao gás. | Colocar o Nicla Sense num recipiente com panos embebidos em Etanol e Ácido Acético. | Valores nominais de resistência dos gases; Curvas de saturação e recuperação temporal. |
| Evolução Natural | Criar o dataset de base para ML. | Gravar o ciclo de vida (7 a 14 dias) de 3 maçãs isoladas na "Smart Shelf". | Registo de métricas a cada 5 segundos: RGB Ratio, Concentração de VOCs (Index), Temperatura e Humidade. |
| Teste de Resposta Acústica | Treinar a deteção de textura. | Bater suavemente com uma ponta de borracha numa maçã verde (dura) e numa maçã passada (mole) sob o Nicla Voice. | Frequência de pico (Hz) e tempo de amortecimento do som da ressonância da fruta. |
| Teste de Obstrução | Provar a eficácia da ventoinha. | Tapar parcialmente a grelha do sensor com caixas e ligar a ventoinha de sucção. | Medir o diferencial de tempo de deteção de gases com e sem fluxo de ar forçado. |


# Fase 6: Conclusões e Entregáveis
- O que pretendemos entregar: Um sistema físico funcional (Portenta C33 + RPi 5), um modelo de Machine Learning treinado (Random Forest) e um dashboard ao vivo.

- O Impacto Real: "Provámos que é possível monitorizar um lote de fruta em ambiente aberto cruzando visão, química e som, e agir mecanicamente para atrasar a deterioração."
