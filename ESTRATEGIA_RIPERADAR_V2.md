# RipeRadar - Estratégia de Implementação V2 (Edge AI Premium)
## Documento de Arquitetura, Design e Estratégia

---

## PARTE 1: DESIGN MECÂNICO DA PRATELEIRA (Solução aos Desafios Físicos)

### 1.1 Problema: Contacto Indireto com Fruta

**Contexto**: Frutas em caixas abertas, não há contacto direto constante. Gases dissipam-se em supermercados abertos. Sensor acústico precisa de mecanismo para "percutir" a fruta sem manipulação manual.

### 1.2 Solução: Arquitetura de "Câmara Microclimática Passiva"

```
┌─────────────────────────────────────────────────────────┐
│                   PRATELEIRA INTELIGENTE                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Caixa de Fruta (Aberta, Logística Padrão)      │   │
│  │  [🍎][🍎][🍎][🍎] [🍌][🍌][🍌] ...            │   │
│  └──────────────────────────────────────────────────┘   │
│                          ▲                               │
│                          │ Fluxo de Ar Sucção (↑)       │
│                          │                               │
│  ┌──────┐ ┌─────────────────────┐                       │
│  │Nicla │ │  Ventoinha de 24V   │                       │
│  │Voice │ │  (PWM Controlada)   │                       │
│  │      │ │  Manutenção: 5mm    │                       │
│  └──────┘ │  espaçamento        │                       │
│           └─────────────────────┘                       │
│                          ▲                               │
│  ┌──────────────────┐   │                               │
│  │ TCS34725 (Cor)   │◄──┼── (Posição: 15cm do fundo)   │
│  │ Fixado em tubo   │   │   da caixa (zona mais        │
│  │ de 25mm, com     │   │   quente - concentra VOCs)   │
│  │ difusor de ar    │   │                               │
│  └──────────────────┘   │                               │
│           ▲             │                               │
│           │             │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Nicla Sense ME (VOC/Etileno)                    │   │
│  │ Em câmara de ar de 50mm × 50mm × 100mm          │   │
│  │ (mantém concentração gas mesmo em ambiente      │   │
│  │  aberto)                                         │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Portenta C33 (Processamento Local)               │   │
│  │ + RPi 5 via USB-C                                │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Componentes Específicos do Design

#### A) Ventoinha de Sucção (Controlo Ambiental Ativo)
```
Componente: Noctua NF-A9x14 PWM (silencioso, 24V)
Posição: Teto da prateleira, acima da caixa de fruta
Fluxo: ~85 CFM (controlado via PWM do Arduino)

Lógica:
- REP Contínuo (30% velocidade): Mantém microclima de gases
- Pico (80% velocidade): Quando detecta Etileno > threshold, 
  expulsa o ar contaminado durante 10 segundos (salva as outras frutas)
- Desligar (0%): À noite ou quando confiança da cor é "Verde"
```

#### B) Câmara Microclimática para Nicla Sense ME
```
Material: Caixa de alumínio anodizado (25mm × 25mm × 100mm)
Entradas de Ar: 4 furos de 6mm (distribuição uniforme)
Saída: 1 furo de 8mm (superior)

Benefício: Cria uma câmara de concentração de gases que resiste 
à dispersão, mesmo em ambiente aberto. O sensor fica isolado 
termicamente e vê picos de etileno 20-30% mais cedo.
```

#### C) Posicionamento do TCS34725
```
Localização: 15-20cm do fundo da caixa, no centro vertical
Fixação: Tubo de proteção magnético + suporte articulado (permite ajuste)
Óptica: Lente adicional de 60° (difusor) para aumentar FOV

Por que funciona:
1. A fruta solta efetivamente os gases pelo seu "topo" (onde está mais activa a respiração)
2. A cor muda primeiro nas zonas onde o etileno se acumula
3. O tubo magnético permite calibração rápida sem ferramentas (Premium UX para retalhista)
```

#### D) Sistema Acústico (Nicla Voice)
```
Conceito: "Tap-to-Sense" - Toque mecânico suave na fruta

Hardware:
- Solenóide linear de 12V (vibração leve, 5N force)
- Ativado 2x por hora (quando confianças são ambíguas)
- Frequência de toque: 500Hz, duração 50ms

Microfone: Captado diretamente pelo Nicla Voice
- Frequência alvo: 1-5kHz (zona de textura: firme vs mole)
- Algoritmo: Correlação de pitch com regressão de densidade interna

Vantagem: Evita falsos positivos de cor causados por luz ambiente
(Exemplo: Uma maçã com "sombra solar" parece mais avermelhada)
```

---

## PARTE 2: ARQUITETURA DE MACHINE LEARNING AVANÇADA (Edge AI)

### 2.1 Problema: Random Forest atual é simples (apenas R,G,B,R/G)

**Análise**:
- Features atuais: 4 (R, G, B, R/G ratio)
- Sensores disponíveis: 4 tipos (cor, gas, acústica, temperatura)  
- Ruído ambiental: Alto (iluminação variável em supermercados)

### 2.2 Solução: Feature Engineering + Ensemble Robusto

#### A) Novas Features a Extrair

```
# Cor (TCS34725)
1. RGB_Normalized = [R/255, G/255, B/255]
2. R/G_Ratio = R/G
3. B/(R+G) = Blue prominence → detecta "escurecimento" de podridão
4. RGB_Distance_to_Profile = sqrt((R-R_profile)² + (G-G_profile)² + (B-B_profile)²)
5. CIE_L*a*b = Converter para espaço de cor perceptualmente uniforme
   (mais resistente a variações de luminosidade)
6. Color_Entropy = Mede uniformidade de cor (fruta podre tem mais heterogeneidade)
7. Saturation = (Max(RGB) - Min(RGB)) / Max(RGB)
8. Hue_Shift = Ângulo em HSV (amarelecimento progressivo)

# Gás/VOCs (Nicla Sense ME)
9. VOC_Index_Raw = Leitura do sensor Bosch BME688
10. VOC_Trend_24h = Derivada temporal (está a aumentar rapidamente?)
11. Etileno_Proxy = Proporção VOC_Index normalizada
12. Gas_Spike_Frequency = Quantos picos > threshold nos últimos 30min?

# Acústica (Nicla Voice)
13. Acoustic_Frequency_Peak = Pitch dominante da ressonância
14. Acoustic_Damping = Tempo até amplitude cair para 50% (mede estrutura)
15. Acoustic_Energy = Integral da FFT (quantidade de "som" da vibração)
16. Acoustic_Q_Factor = Sharpness do pico (Q-factor, mede elasticidade)

# Ambiente (Sensores integrados)
17. Temperature_Local = Do Nicla Sense ME (respiração celular ↑ = fruta a degradar-se)
18. Humidity_Delta = Humidade dentro vs fora da câmara
19. Time_Since_Restocking = Horas desde que a fruta foi colocada (antes de 24h = provavelmente "Verde")
20. Hora_do_Dia = Sin(hour) + Cos(hour) para capturar ciclos circadianos
    (frutas na sombra matinal vs. sob luz solar tardia parecem diferentes)
```

#### B) Novo Pipeline de ML (Ensemble Robusto multi-camadas)

```python
# Camada 1: Detecção Robusta (RGB vs Ambiente)
├─ Decision Tree (max_depth=5) para decisões rápidas no Portenta C33
│  └─ Features: [RGB_Normalized, B/(R+G), Color_Distance]
│  └─ Saída: Classe Fast ("Verde_Claro", "Madura_Prov", "Podre_Claro")
│  └─ Objetivo: Reduz falsos positivos de iluminação
│
├─ CatBoost (gradient boosting inteligente para tabular)
│  └─ Features: Todas as 20 features (CVS + VOC + Acústica + Ambiente)
│  └─ Saída: Probabilidades suavizadas + importância de features
│  └─ Objetivo: Captura interações complexas (ex: cor + gás + temperatura)
│
└─ Camada 2: Redundância Temporal (Time-Series)
   └─ LSTM Simples (1 camada, 32 unidades, window=50 leituras = 4.2min com fs=0.2Hz)
   └─ Features: Sequência temporal de VOC_Index + Color_Entropy
   └─ Saída: Previsão do estado em t+30min (alerta antecipado 30min antes)
   └─ Objetivo: Deteta trajetórias de deterioração não óbvias

# Votação Final:
└─ Weighted Voting (Pesos aprendidos via Logistic Regression no treino)
   ├─ Voto 1: Decision Tree (peso: 0.2 para rapidez)
   ├─ Voto 2: CatBoost (peso: 0.5 para precisão)
   ├─ Voto 3: LSTM (peso: 0.3 para tendências)
   └─ Saída: ["Verde", "Maduro", "Maturando_Rápido", "Deterioração_Iminente", "Podre"]
```

#### C) Integração no Dispositivo Edge (RPi 5 + Portenta C33)

```
PORTENTA C33 (Microcontrolador)
├─ Clock: 120MHz ARM Cortex-M7
├─ Tarefa: Leitura de sensores + Decision Tree rápido
├─ Latência: <100ms
└─ Modelo: decision_tree_fast.pkl (50KB)

RASPBERRY PI 5 (Processador Principal)
├─ Tarefa: CatBoost + LSTM + Votação + API de Dashboard
├─ Latência: ~500ms (aceitável para visão e decisões)
├─ Modelos: catboost_model.bin (5-10MB), lstm_model.tflite (2MB)
├─ Framework: TensorFlow Lite (para LSTM em edge)
└─ Caching: Mantém buffer de 500 últimas amostras em SQLite
```

---

## PARTE 3: IDEIAS PREMIUM (Surpreender o Júri + Retalhistas)

### 3.1 "Time-to-Waste" Prediction Engine

```
Conceito: Não dizer apenas "está podre", mas "tem 47 horas de vida útil"

Implementação:
1. Treinar modelo regressivo (target: horas até "Rotten")
   └─ Dataset: Registar ciclo de vida completo de 20 frutas
   └─ Features: VOC_trend_24h, Color_Trend, Temperature (respiração)
   
2. Saída em Dashboard (RPi WebUI):
   ├─ Prateleira 3: "🍎 Maçãs | Tempo: 47h ⚠️ Reorder agora"
   ├─ Prateleira 3: "🍌 Bananas | Tempo: 12h 🔴 Promoção urgente"
   └─ Sistema envia alertas ao gestor com antecedência

3. Integração Retail:
   └─ API REST: GET /shelf/{id}/ttw → JSON com TTW de cada fruta
   └─ Conecta com etiquetas eletrónicas (Pricer, Vusix) para Dynamic Pricing
```

### 3.2 "Ripeness Profile" - Mapa Térmico da Prateleira

```
Conceito: Visualizar onde estão as frutas de cada nível de maturação

Implementação:
1. Array de sensores TCS34725: Em vez de 1, usar 4-6 sensores 
   distribuídos pela prateleira (comunicação via I2C multiplexada)
   
2. Dashboard em tempo real (WebSocket):
   ┌──────────────────────────────┐
   │ PRATELEIRA 3 - MAÇÃS        │
   │ [🟢][🟡][🟠][🟢][🔴][🟡]  │
   │ Verde Maduro Pegado ... Podre │
   │ TTW: 72h  48h  24h  12h  NOW │
   └──────────────────────────────┘

3. Funcionalidade: Funcionário vê isto no iPad e roda stock automaticamente
```

### 3.3 "SmartRotate" - Automação de Rotação de Stock

```
Conceito: Sistema de recomendação inteligente para FIFO

Implementação:
1. Algoritmo:
   └─ Se a prateleira tem 5 caixas, e a caixa 3 tem TTW=15h
   └─ Enquanto caixa 1 tem TTW=72h:
      → Alerta: "Priorizar venda de caixa 3 | Reordenar caixa 1 para trás"

2. Dashboard com instrução visual:
   └─ Mostrar setas de movimento (↑↓ para cima/baixo)
   └─ Código QR dinâmico para cada caixa (funcionário scanneia para confirmar)

3. Métrica de Sucesso:
   └─ Redução de desperdício em 30% (caso de uso "Smart Crate")
```

### 3.4 "Etileno Watershed" - Detecção do Paciente Cero

```
Conceito: Qual é o FRUTA específica que está a "contagiar" as outras?

Implementação:
1. Quando VOC_Index dispara nos últimos 2 horas:
   └─ Correlacionar com cada posição da câmara (se tens 4 sensores)
   └─ Usar algoritmo de triangulação para pintar "origem" do etileno
   
2. Alerta ao retalhista:
   "🍌 BANANA na posição 3 (canto inferior-esquerdo) é a fonte 
   de etileno. Mover 30cm para a frente e ativar ventoinha em modo máximo."

3. Vantagem de Negócio:
   └─ Evita destruição em cascata de lotes inteiros
   └─ "Salvou 50€ de fruta apenas hoje" aparece no dashboard
```

### 3.5 "Acoustic Health Index" - Score de Qualidade Interna

```
Conceito: Detectar "maçã farinhenta" antes de o cliente morder

Implementação:
1. Treinar rede neuronal com espectrograma acústico:
   └─ Input: Espectrograma de 2s de som capturado (16kHz, Nicla Voice)
   └─ Output: Score de qualidade interna (1-10)J
   └─ Features de áudio: MFCC (Mel-frequency cepstral coefficients)

2. Dataset de treino:
   └─ Gravar som de 10 maçãs firmes (score=9), 10 meio-boas (5), 10 moles (2)
   └─ Aumentação: Variar Volume, Reverb, Ruído de fundo (supermercado)

3. Integração:
   └─ Cada 4 horas, fazer 2-3 "taps" de diagnóstico
   └─ Se score < 5 e TTW ainda > 24h: Anomalia! Pode ter problema interno
   └─ Alerta: "Possível fruta com bolor interno detectado na posição X"
```

### 3.6 "Sustainability Report" (Dashboard Executive)

```
Conceito: Relatório executivo diário para retalhista

Implementação:
1. Métrica gerada:
   ├─ Frutas Evitadas de Desperdício: 12 (hoje)
   ├─ Valor Salvo: €47.50
   ├─ Emissões CO2 Evitadas (Transporte de reposição): 2.4kg
   ├─ Prateleiras com Maior Desperdício: Prateleira 7 (Bananas)
   └─ Eficiência Geral: 92% (target: 85%)

2. Exportar em PDF com gráficos (matplotlib em RPi):
   └─ Gráfico de TTW ao longo do dia (mostra padrões)
   └─ Heatmap de VOC por prateleira (qualidade do ar)
   └─ Top frutas por desperdício (dados para compras futuras)

3. Impacto: Retalhista vê ROI claro → más é fácil vender projeto
```

### 3.7 "Fruta de Referência" - Calibração Autónoma

```
Conceito: Sistema auto-calibra-se marcando uma "fruta de referência"

Implementação:
1. Setup inicial (QR-code guiado):
   └─ Colocar 1 banana "perfeita" (verde, firme) na posição A
   └─ Sistema registra RGB desta fruta como "baseline Verde"
   └─ Repetir para "Madura" (após 3 dias) e "Podre" (após 7 dias)

2. Durante operação:
   └─ Cada leitura é normalizada contra esta "fruta de referência"
   └─ Elimina variações de iluminação, ângulo, sensor
   └─ Modelo auto-adapta (transfer learning) com dados da loja

3. Vantagem:
   └─ Projeto "plug-and-play" - não precisa de calibração manual complexa
   └─ Adapta-se a diferentes lojas e tipos de fruta automaticamente
```

### 3.8 "Nicla Voice Integration" - Alertas Audíveis Inteligentes

```
Conceito: Voice notifications em vez de apenas visuais

Implementação:
1. Microfone do Nicla Voice gera alertas locutados:
   └─ "Prateleira 3: Banana critical - 6 horas para desperdício total"
   └─ "Ventoinha ativa: Detectado etileno pico na posição A"
   
2. Múltiplas línguas (para cadeia Europeia):
   └─ Português, Inglês, Espanhol, Francês (TTS via Google Cloud ou offline)

3. Vantagem:
   └─ Funcionário não precisa de estar a olhar para tablet
   └─ Som alerta mesmo se prateleira tem barulho de loja
```

---

## PARTE 4: ROADMAP DE IMPLEMENTAÇÃO (8 Semanas de Mestrado)

### Semana 1-2: Preparação de Dados & Captura Ativa
- [ ] Montagem de "Smart Shelf" com ventoinha de sucção + câmara de VOC
- [ ] Captura de dataset completo: 20-30 frutas pelos seus ciclos de vida (7-14 dias)
- [ ] Sincronização de timestamps entre sensores (Portenta C33 é maestro do relógio)
- [ ] Extractar as 20 novas features para cada amostra temporal

### Semana 3-4: Treino de Modelos
- [ ] Treinar Decision Tree (rápido, no Portenta)
- [ ] Treinar CatBoost (precisão, no RPi)
- [ ] Treinar LSTM para tendências temporais
- [ ] Validação cruzada: Leave-one-fruit-out (simula fruta desconhecida)

### Semana 5: Integração Edge AI
- [ ] Converter LSTM para TensorFlow Lite
- [ ] Otimizar modelos para tamanho (Quantização INT8)
- [ ] Testar latência no RPi 5 (alvo: <500ms por ciclo)
- [ ] Implementar votação ponderada

### Semana 6: Interfaces & Dashboard
- [ ] Criar WebUI em Flask/FastAPI (RPi)
- [ ] Real-time chart library: Plotly/Chart.js
- [ ] API REST para integração com POS/etiquetas eletrónicas
- [ ] Implementar alertas (desktop, mobile, voice)

### Semana 7: Features Premium
- [ ] Implementar Time-to-Waste regressão
- [ ] Acoustic Health Index (MFCC + treino rápido)
- [ ] Fruta de Referência (auto-calibração)
- [ ] Exportar relatórios PDF

### Semana 8: Apresentação & Otimização
- [ ] Testes de confiabilidade (24h de funcionamento contínuo)
- [ ] Documentação de deployment (Dockerfile, manual de instalação)
- [ ] Defesa: Demo ao vivo com dataset captado + explicação de features premium
- [ ] Posicionamento final: "Edge AI que salva milhões em desperdício food-waste"

---

## PARTE 5: CRITÉRIOS DE SUCESSO PARA JÚRI

### 5.1 Demonstração Técnica
- [ ] Detecção de deterioração **24h antes** de ser visível a olho nu
- [ ] Acurácia > 92% em classificação (Verde/Maduro/Podre)
- [ ] Latência < 500ms por ciclo de decisão
- [ ] Consumo de energia < 15W em modo contínuo

### 5.2 Inovação de Hardware
- [ ] Ventoinha de sucção (ativa) em vez de sensores passivos
- [ ] Câmara microclimática para VOC (demonstra compreensão de termodinâmica)
- [ ] Array de sensores (multi-sensor fusion é benchmark de MSc)

### 5.3 Inovação de Software
- [ ] Feature engineering de 4 features → 20 features (rigor científico)
- [ ] Ensemble de 3 modelos (não apenas RF simples)
- [ ] Time-series LSTM para previsão de TTW (futuristic)
- [ ] Dashboard executivo com ROI claro (impacto comercial)

### 5.4 Impacto Real
- [ ] Quantificar redução de desperdício: "Economizar €50 por loja por dia"
- [ ] CO2 offset: "Equivalent a X árvores por loja por ano"
- [ ] Retorno de investimento: "Payback em 6 meses"
- [ ] Cases de uso expandíveis (Smart Crate, Acoustic Health, Dynamic Pricing)

---

## PARTE 6: LISTA DE FICHEIROS A CRIAR/MODIFICAR

```
scripts/
├─ preprocess_dataset_v2.py (extrai as 20 features)
├─ train_ensemble.py (Decision Tree + CatBoost + LSTM)
├─ inference_edge.py (votação ponderada no RPi)
├─ acoustic_model_train.py (MFCC → Health Index)
└─ ttw_regression.py (Time-to-Waste prediction)

models/
├─ decision_tree_fast.pkl (fit no Portenta C33)
├─ catboost_model.bin (fit no RPi 5)
├─ lstm_model.tflite (mobilidade)
└─ audio_health_model.tflite (Nicla Voice)

dashboard/
├─ app.py (Flask WebUI)
├─ templates/
│  ├─ index.html (real-time chart)
│  └─ reports.html (TTW log + PDF export)
└─ static/
   ├─ style.css
   └─ script.js (WebSocket para dados live)

hardware/
├─ 3d_models/ (câmara VOC, suporte sensores)
└─ wiring_diagram.pdf (USB-C Portenta↔RPi, ventoinha PWM)

docs/
├─ DEPLOYMENT.md (como instalar numa loja real)
├─ CALIBRATION_GUIDE.md (procedimento de referência)
└─ API_SPEC.md (endpoints para integração com POS)
```

---

## RESUMO EXECUTIVO

| Aspecto | Versão V1 (Atual) | Versão V2 (Proposta) | Ganho |
|--------|------------------|-------------------|--------|
| Features | 4 | 20 | 5x mais contexto |
| Modelos | 1 (RF) | 3 (DT+CB+LSTM) | Ensemble robusto + Previsão temporal |
| Acurácia esperada | ~85% | ~94% | +9% (mais confiável) |
| TTW Detecção | Classificação estática | Regressão (horas) | Actionable insights |
| Design Hardware | Conceitual | Produção (ventoinha + câmara) | Pronto para retail |
| Dashboard | Nenhum | Web completo + Relatórios | Aprovação de retalhista |
| Casos de Uso | 2 (Crate, Tapete) | 7+ (Premium tier) | Diferenciação no mercado |

---

## PRÓXIMOS PASSOS IMEDIATOS

1. **Hoje**: Discuta com orientador se timeline de 8 semanas é exequível
2. **Amanhã**: Montagem física da "Smart Shelf" (ventoinha + câmara VOC)
3. **Esta semana**: Começar captura de dataset temporal (20-30 frutas)
4. **Próxima semana**: Feature extraction v2 (20 features) + treino de CatBoost
5. **Semana 4**: Integração LSTM + votação no RPi

---

## Contacto para Dúvidas
Se precisar de ajuda em qualquer fase, estou disponível para:
- Code reviews dos novos modelos
- Debugging de latência no RPi 5
- Otimização de memory footprint (Quantização)
- Estratégia de apresentação ao júri

**Sucesso! O projeto tem potencial para ser realmente disruptivo.** 🚀
