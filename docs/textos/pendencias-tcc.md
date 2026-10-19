# Pendências e pontos de atenção do TCC

Estes pontos foram encontrados na revisão do documento `Documento_ST1_Pulso_REV01`.

## Inconsistências

- [ ] **Os preços se contradizem.** A seção 1.4 fala em R$ 300 de hardware e R$ 80/mês, e a 7.1 em R$ 550 e R$ 500/mês. As MRRs do roadmap usam R$ 80, e o TAM/SAM/SOM usa R$ 500. É preciso escolher um único valor e revisar as contas.
- [ ] **O termo "TAM" aparece com dois sentidos.** Na seção 1.5 ele é R$ 7,2 mi/mês (Brasil, top 50); na 7.2 é R$ 48 bi (mundo inteiro).
- [ ] **A detecção de queda** está no Canvas ("alerta de queda em <3 s"), mas o acelerômetro não aparecia no hardware. Ele já foi incluído no projeto ideal (LIS2DH12).
- [ ] **Erro de digitação** na seção 4.1: "minerado do Grupo Votorantin" deve ser "mineradora do Grupo Votorantim".

## Partes a preencher

- [ ] 5.1: resultados da validação (meta de 50 respostas, percentuais e gráficos)
- [ ] Figura 1: infográfico de funcionamento (usar `figuras/sistema/Figura_infografico_mina.png`)
- [ ] Figuras 2 e 3: fotos dos canvas preliminares
- [ ] Figuras 5 e 6: prints do digital twin e foto do protótipo
- [ ] Figura 7: road map visual
- [ ] Figura 8: planilha financeira
- [ ] Seção 8: links do pitch, dos slides e do repositório
- [ ] Referências completas: ANM, IBRAM e NR-22

## Sugestões

- Citar a **certificação ATEX** como próxima etapa do hardware. Ela exige limitação de corrente na bateria e encapsulamento (segurança intrínseca).
- Citar a **LGPD**: BPM e SpO2 são dados de saúde, classificados como sensíveis (art. 11).
