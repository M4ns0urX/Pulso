# Visão geral do projeto

## O problema

A mineração subterrânea no Brasil movimenta cerca de **R$ 130 bilhões por ano** e tem aproximadamente **180 mil trabalhadores no subsolo**. É um dos ambientes de trabalho mais perigosos do país, com risco de desabamento, gases tóxicos, baixa oxigenação, calor e acidentes com máquinas.

Mesmo assim, o controle desses trabalhadores ainda é feito, na maioria das operações, por **crachá e planilha**. Quando o operário entra na mina, ele vira um **"trabalhador invisível"**: a superfície não tem a localização exata dele, não tem dados sobre seu estado de saúde e ele não tem um botão de SOS.

Em 2020 foram registrados **107 acidentes graves e 16 mortes** em minas subterrâneas. No caso de Cleiton Oliveira de Souza, atingido por uma rocha numa mina na Bahia, o corpo só foi retirado na manhã seguinte, porque não havia localização precisa no subsolo.

## A solução: Pulso, o EPI conectado

A Pulso é uma braçadeira usada no braço durante todo o turno. Ela oferece:

- **monitoramento de BPM e SpO2**, enviado a cada 5 segundos;
- **localização UWB** com cerca de ±10 cm de precisão, sem depender de GPS;
- **botão SOS**, que envia um alerta imediato com a posição exata;
- **rede LoRa subterrânea**, sem depender de Wi-Fi ou sinal de celular;
- **certificação IP68**, com a certificação ATEX (ambientes explosivos) prevista.

Os dados vão para um **dashboard** na sala de controle, que mostra o mapa da mina com cada trabalhador, os sinais vitais e os alertas automáticos.

**Estágio atual:** existe um **digital twin** funcional, ou seja, uma simulação completa de sensores, rede, localização e dashboard. A migração para o hardware físico está em andamento, e o projeto já foi validado em contato com a equipe de desenvolvimento da **NEXA Resources**.

## Mercado

| | |
|---|---|
| **Cliente (quem paga)** | Área de HSE/SSMA e Operações das mineradoras |
| **Usuário (quem usa)** | Trabalhador no subsolo |
| **Beneficiário** | Sala de controle e investidores com critérios ESG |
| **Foco inicial** | As 50 maiores operações subterrâneas, com cerca de 90 mil trabalhadores |
| **Empresas-alvo** | Vale, NEXA, Kinross, Anglo American, AngloGold Ashanti, Mineração Caraíba e outras |

O momento é favorável por três motivos:
- a **revisão da NR-22** deve passar a exigir monitoramento individual;
- cresce a **pressão ESG** por metas de "zero fatality";
- **sensores UWB, BLE e LoRa** ficaram mais baratos.

## Concorrentes

| Concorrente | Limitação |
|---|---|
| iSmarch | Sem localização UWB e sem certificação ATEX |
| Ztrax | Rastreia máquinas, não trabalhadores |
| SmartX HUB | Sem integração entre biometria e localização |
| Crachá + planilha | Nenhum dado em tempo real, sem SOS |
| **Pulso** | **Integra BPM, SpO2, UWB, SOS e LoRa num único produto** |

## Modelo de negócio

O modelo é híbrido: **venda do hardware** (pagamento único por trabalhador) mais uma **assinatura SaaS** (mensal por trabalhador), que inclui o dashboard, o suporte e os relatórios de conformidade.

## Roadmap (24 meses)

| Período | Marco | Meta |
|---|---|---|
| Meses 0–6 | MVP físico | Investimento seed de R$ 800 mil |
| Meses 6–12 | Piloto pago com 100 trabalhadores | MRR de cerca de R$ 8 mil |
| Meses 12–18 | Certificação ATEX e 3 operações | MRR de cerca de R$ 120 mil |
| Meses 18–24 | Escala nas grandes mineradoras | MRR de cerca de R$ 400 mil |
