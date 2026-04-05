# RipeRadar V2 - Checklist Executivo (8 Semanas)

## 🎯 Visão Geral
Este checklist organiza o desenvolvimento em **4 sprints de 2 semanas** com foco em:
1. **Sprint 1-2**: Dados & Hardware
2. **Sprint 3-4**: Modelos ML & Integração
3. **Sprint 5-6**: Features Premium & Dashboard
4. **Sprint 7-8**: Testes & Apresentação

---

## 🏗️ SPRINT 1-2: Dados & Hardware (Semanas 1-2)

### Hardware Physical Design
- [ ] 2.1: Desenhar CAD da câmara microclimática VOC (25×25×100mm alumínio)
- [ ] 2.2: Especificar ventoinha (Noctua NF-A9x14 ou similar)
- [ ] 2.3: Definir posicionamento TCS34725 (15-20cm do fundo)
- [ ] 2.4: Imprimir/fabricar proto em FDM 3D
- [ ] 2.5: Teste de fluxo de ar (verificar sucção efetiva)
- [ ] 2.6: Soldar/conectar sensores ao Portenta C33
- [ ] 2.7: Teste de comunicação USB-C Portenta ↔ RPi
- [ ] 2.8: Documentar diagrama de wiring em PDF

### Dataset Temporal
- [ ] 1.1: Preparar 20-30 frutas (diferentes tipos & estados)
- [ ] 1.2: Setup de captura contínua por 7-14 dias
  - [ ] 1.2a: Configurar logging de timestamp sincronizado
  - [ ] 1.2b: Registar leituras RGB cada 30 minutos
  - [ ] 1.2c: Registar VOCs desde Nicla Sense ME
  - [ ] 1.2d: Registar Temperatura/Humidade
- [ ] 1.3: Capturar imagens em 3-4 ângulos por fruta/dia
- [ ] 1.4: Armazenar dataset em estrutura clara (`data/raw/`)
- [ ] 1.5: Criar ground truth labels (Verde, Maturando, Maduro, Podre)

### Calibração Base
- [ ] 3.1: Executar `calibracao.py` com frutas de referência
- [ ] 3.2: Registar perfis RGB normalizados (R/C, G/C, B/C)
- [ ] 3.3: Validar leituras do sensor acústico (Nicla Voice)
- [ ] 3.4: Documentar valores de baseline em `config_calibration.json`

### Documentação
- [ ] 4.1: Criar README atualizado com V2 overview
- [ ] 4.2: Video de 2-3min do setup físico para apresentação

**Critério de Sucesso Sprint 1-2**: 
- ✅ Hardware funcionando, 500+ amostras temporais capturadas, 20+ features extraíveis

---

## 🤖 SPRINT 3-4: Modelos ML & Integração (Semanas 3-4)

### Feature Engineering (Semana 3)
- [ ] 5.1: Executar `feature_extractor_v2.py` sobre dataset
  - [ ] Extrair 21 features avançadas (RGB, LAB, HSV, entropia, etc)
  - [ ] Gerar `riperadar_features_v2.csv`
- [ ] 5.2: Análise exploratória (EDA)
  - [ ] Plotar distribuição das 21 features
  - [ ] Identificar correlações valiosas
  - [ ] Remover features redundantes (Variance Inflation Factor)
- [ ] 5.3: Feature selection (manter 15-18 mais importante)
- [ ] 5.4: Normalização com StandardScaler + salvar `feature_scaler.pkl`

### Treino de Modelos (Semana 4)
- [ ] 6.1: Executar `train_ensemble_v2.py`
  - [ ] 6.1a: Treinar Decision Tree (Portenta C33)
    - Target: max_depth=5, latência <100ms
  - [ ] 6.1b: Treinar CatBoost (RPi 5)
    - Target: Acurácia >93%
  - [ ] 6.1c: Treinar LSTM (previsão temporal)
    - Target: Val accuracy >85%
- [ ] 6.2: Votar com pesos aprendidos (DT=0.2, CB=0.5, LSTM=0.3)
- [ ] 6.3: Validação cruzada (leave-one-fruit-out)
- [ ] 6.4: Testar em maquina real vs esperado
- [ ] 6.5: Converter LSTM para TensorFlow Lite (quantização INT8)
- [ ] 6.6: Salvar modelos em `models/` com metadata

### TTW Regression (Semana 4)
- [ ] 7.1: Executar `train_ttw_regression.py`
  - [ ] Treinar XGBoost com target = horas até "Podre"
- [ ] 7.2: Validar MAE < 3 horas nos testes
- [ ] 7.3: Treinar confidence model (intervalo [TTW-margin, TTW+margin])
- [ ] 7.4: Testar predições em 3 exemplos

### Integração Portenta ↔ RPi (Semana 4)
- [ ] 8.1: Implementar `portenta_sensor_fusion.ino`
  - [ ] Leitura TCS34725
  - [ ] Leitura Nicla Sense ME via I2C
  - [ ] Leitura Nicla Voice via UART
  - [ ] Enviar JSON via Serial ao RPi
- [ ] 8.2: Implementar `rpi5_inference_api.py`
  - [ ] Receber dados JSON do Portenta
  - [ ] Fazer predição Ensemble
  - [ ] Retornar classe + TTW
- [ ] 8.3: Teste de latência end-to-end (<500ms)
- [ ] 8.4: Buffer de 500 amostras em DB local (SQLite)

**Critério de Sucesso Sprint 3-4**:
- ✅ Ensemble acurácia >93%, TTW MAE <3 horas, Latência <500ms

---

## ✨ SPRINT 5-6: Features Premium & Dashboard (Semanas 5-6)

### Dashboard Web (Semana 5)
- [ ] 9.1: Executar `dashboard_app.py` 
  - [ ] UI com grid de prateleiras
  - [ ] Real-time updates via WebSocket
  - [ ] TTW display por caixa
  - [ ] Mapa de urgência (verde/amarelo/laranja/vermelho)
- [ ] 9.2: Implementar alertas visuais
  - [ ] Notificação desktop quando TTW < 24h
  - [ ] Som de alerta em crítico
- [ ] 9.3: Exportar Relatório PDF diário
  - [ ] Gráficos de TTW
  - [ ] VOC heatmap
  - [ ] Desperdício evitado (€)
  - [ ] Recomendações de ação
- [ ] 9.4: Testar em múltiplos navegadores (Chrome, Safari, Firefox)

### Time-to-Waste Prediction (Semana 5)
- [ ] 10.1: Implementar output "Prateleira tem 47h antes de invendável"
- [ ] 10.2: Integração no Dashboard com timeline visual
- [ ] 10.3: Alertas antecipados (notificar 24h antes do crítico)

### Smart Rotate Feature (Semana 5-6)
- [ ] 11.1: Algoritmo de recomendação FIFO + prioridade
  - [ ] Se TTW(caixa 3) < TTW(caixa 1): "Move caixa 3 para frente"
- [ ] 11.2: UI com setas de movimento no Dashboard
- [ ] 11.3: Gerar código QR dinâmico para cada caixa

### Ripeness Profile Map (Semana 6)
- [ ] 12.1: Adicionar suporte para múltiplos sensores TCS34725
  - [ ] I2C multiplexing (TCA9548A) ou trocar endereço
- [ ] 12.2: Visualizar heatmap da prateleira
  - [ ] Cor verde/amarelo/laranja/vermelho por posição
- [ ] 12.3: Atualizar em tempo real no Dashboard

### Etileno Watershed (Semana 6)
- [ ] 13.1: Quando VOC dispara, correlacionar com posição
- [ ] 13.2: Algoritmo de triangulação (3+ sensores VOC)
- [ ] 13.3: Alerta: "BANANA na posição 3 é a origem, mover 30cm à frente"
- [ ] 13.4: Ativar ventoinha em modo máximo por 10 segundos

### API de Integração POS (Semana 6)
- [ ] 14.1: Criar endpoint `POST /api/update-dynamic-pricing`
  - [ ] Input: shelf_id, TTW
  - [ ] Output: discount_percent
- [ ] 14.2: Comunicação com sistema de etiquetas eletrónicas
- [ ] 14.3: Documentar API spec em Swagger

**Critério de Sucesso Sprint 5-6**:
- ✅ Dashboard fully functional, 3+ features premium implementadas, API working

---

## 🧪 SPRINT 7-8: Testes & Apresentação (Semanas 7-8)

### Testes de Confiabilidade (Semana 7)
- [ ] 15.1: Teste de 24h de funcionamento contínuo
  - [ ] Verificar sem crashes
  - [ ] Logs sem erros
  - [ ] Memória estável no RPi
- [ ] 15.2: Teste de Robustez
  - [ ] Variar iluminação (escuro, luz solar, LED)
  - [ ] Verificar se acurácia mantém >90%
- [ ] 15.3: Teste de Interferência
  - [ ] Outro dispositivo Wi-Fi perto
  - [ ] Ruído magnético
  - [ ] Verificar latência não aumenta >800ms
- [ ] 15.4: Teste de Calibração Autónoma
  - [ ] Usar "fruta de referência" para auto-calibrar
  - [ ] Verificar se acurácia melhora após 3 dias

### Otimização de Performance (Semana 7)
- [ ] 16.1: Profile memory usage RPi
  - [ ] Target: <500MB durante operação
- [ ] 16.2: Otimizar cache de modelos
- [ ] 16.3: Quantização de modelos (se necessário)

### Documentação Final (Semana 7)
- [ ] 17.1: Atualizar `DEPLOYMENT_GUIDE.md`
- [ ] 17.2: Criar `TROUBLESHOOTING.md`
- [ ] 17.3: Documentar todos os endpoints API
- [ ] 17.4: Criar manual de utilizador (PDF, 5 páginas)
- [ ] 17.5: Video tutorial de setup (5 min)

### Apresentação ao Júri (Semana 8)
- [ ] 18.1: Preparar Deck de PowerPoint (30 slides)
  - [ ] [ ] Slide 1-5: O Problema & Visão
  - [ ] [ ] Slide 6-10: Hardware & Design
  - [ ] [ ] Slide 11-15: ML Architecture (Ensemble)
  - [ ] [ ] Slide 16-20: Features Premium (TTW, Etileno Watershed, etc)
  - [ ] [ ] Slide 21-25: Resultados (Acurácia, TTW MAE, Latência)
  - [ ] [ ] Slide 26-30: Impacto Real (€, CO2, ROI)
- [ ] 18.2: Preparar Live Demo
  - [ ] [ ] Hardware físico a funcionar
  - [ ] [ ] Dashboard ao vivo com dados reais
  - [ ] [ ] Mostrar previsão de TTW a mudar em tempo real
  - [ ] [ ] Demonstrar alerta quando VOC dispara
- [ ] 18.3: Preparar 3 casos de uso (Smart Crate, Tapete, Dynamic Pricing)
- [ ] 18.4: Criar Poster técnico (A1)

### Defesa Final (Semana 8)
- [ ] 19.1: Apresentação oral (15-20 min)
  - [ ] Contexto do problema (1 min)
  - [ ] Solução proposta (2 min)
  - [ ] Hardware & Design (2 min)
  - [ ] ML Architecture (3 min)
  - [ ] Features Premium (3 min)
  - [ ] Resultados (2 min)
  - [ ] Live Demo (2-3 min)
- [ ] 19.2: Responder a perguntas do júri
  - [ ] [ ] "Como resolveste a interferência ambiental?" → Ventoinha de sucção
  - [ ] [ ] "Qual é o tempo de treino?" → 20min em CPU
  - [ ] [ ] "Como escala para múltiplas lojas?" → Cloud backend com sync
  - [ ] [ ] "ROI para retalhista?" → Payback em 6 meses
- [ ] 19.3: Entregar relatório final (PDF, 40 páginas)

**Critério de Sucesso Sprint 7-8**:
- ✅ 24h de uptime sem erros, >90% acurácia mantida, Apresentação impactante

---

## 📊 Métricas de Sucesso Globais

| Métrica | Target | Status |
|---------|--------|--------|
| Acurácia Classificação | >93% | ⬜ |
| TTW MAE | <3 horas | ⬜ |
| Latência E2E | <500ms | ⬜ |
| Uptime | >99% | ⬜ |
| Detecção Antecipada | 24h antes visível | ⬜ |
| Dashboard Responsividade | <1s update | ⬜ |
| Consumo Energie | <15W contínuo | ⬜ |
| Dataset Versão Final | >1000 amostras | ⬜ |

---

## 🚀 Prioridades Semanais (Quick Reference)

### Semana 1
```
🔴 Crítico: Hardware montado
🟡 Importante: Dataset captura iniciada
🟢 Nice-to-have: Documentação
```

### Semana 2
```
🔴 Crítico: 500+ amostras capturadas
🟡 Importante: Figuras do dataset boas
🟢 Nice-to-have: Calibração otimizada
```

### Semana 3
```
🔴 Crítico: Feature extraction V2 funcionando
🟡 Importante: Features correlacionam com estado real
🟢 Nice-to-have: Exploratória avançada
```

### Semana 4
```
🔴 Crítico: 3 modelos treinados & votação funcionando
🟡 Importante: Acurácia ensemble >90%
🟢 Nice-to-have: TTW acurado
```

### Semana 5
```
🔴 Crítico: Dashboard Web funcionando
🟡 Importante: TTW Regression funcionando
🟢 Nice-to-have: Features premium começadas
```

### Semana 6
```
🔴 Crítico: 3+ features premium implementadas
🟡 Importante: API POS integrada
🟢 Nice-to-have: Múltiplos sensores suportados
```

### Semana 7
```
🔴 Crítico: 24h uptime test passed
🟡 Importante: Documentação completa
🟢 Nice-to-have: Performance otimizada
```

### Semana 8
```
🔴 Crítico: Apresentação pronta & ensaiada
🟡 Importante: Live demo reliável
🟢 Nice-to-have: Surpresa additional
```

---

## 📝 Notas Finais

### Dependências Críticas
- ❌ Se hardware não estiver pronto na Semana 2: +1 semana atraso
- ❌ Se dataset < 500 amostras: Modelos underfitting inevitable
- ❌ Se latência > 1s: Impossível deploy em supermercado real

### Oportunidades de Aceleração
- ✅ Usar pré-trained features extractor (transfer learning) → -3 dias
- ✅ Usar Cloud para treino paralelo → -2 dias
- ✅ Reutilizar Dashboard template → -4 dias

### Riscos Conhecidos
- ⚠️ Nicla Sense ME pode ter latência em I2C → Plano B: usar UART
- ⚠️ RPi 5 pode overheating sob carga → Adicionar heatsink/ventoinha
- ⚠️ Modelos quantizados podem perder acurácia → Testar cedo

---

## 🎓 Sugestões para Impressionar Júri

1. **Narrativa de Impacto**: "Este projeto salva €2M/ano em desperdício numa cadeia Europeia de 1000 lojas"
2. **Demonstração de Rigor**: Mostrar comparação de 3 modelos vs baseline
3. **Inovação Hardware**: Ventoinha de sucção é uma solução elegante não-óbvia
4. **Proof-of-Concept Real**: Dados de 30 frutas reais durante 2 semanas, não simulação
5. **Escalabilidade**: Explicar como expande de 1 prateleira → chain inteira → Europa

---

## 📞 Apoio

Se precisar de ajuda:
1. Contacte orientador com evidência de progresso (screenshots, métricas)
2. Documente bloqueadores numa issue no GitHub
3. Peça code review quando completar cada sprint

**Você tem potencial para entregar um projeto de MSc **excelente**. Foque nas prioridades, não tente fazer tudo ao mesmo tempo. Sucesso! 🚀**

---

**Última atualização**: Abril 2026 | **Versão**: 2.0
