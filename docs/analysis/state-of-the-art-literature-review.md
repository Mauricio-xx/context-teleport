# Estado del Arte: Revisión Bibliográfica para Context Teleport

## Resumen

Esta revisión bibliográfica complementa el informe de análisis de capacidades de Context Teleport (`eda-collaboration-features-report.md`). Se cubren las **4 áreas prioritarias** identificadas, con el objetivo de posicionar las contribuciones del proyecto respecto a la literatura existente e identificar gaps publicables.

---

## 1. Ecosistema Open-Source Silicon

### 1.1 PDKs Open-Source Principales

| PDK | Foundry | Nodo | Enfoque | Estado (2025) |
|-----|---------|------|---------|---------------|
| **SkyWater SKY130** | SkyWater | 130nm CMOS | Digital, Mixed-Signal, IoT | Maduro; >6,400 miembros en Slack; 50+ universidades |
| **IHP SG13G2** | IHP | 130nm BiCMOS | Analog, RF (hasta 100 GHz) | Activo; soporte OpenROAD + OpenLane; MPW gratuitos |
| **GF180MCU** | GlobalFoundries | 180nm | General-purpose | Estable; soportado por open_pdks |

**SkyWater SKY130**: PDK híbrido 180nm-130nm originalmente desarrollado por Cypress Semiconductor. La colaboración SkyWater-Google lo hizo completamente open-source, sin NDA requerido. Tiny Tapeout permite diseños desde $50 (Efabless). En 2024-2025, Cadence colaboró con SkyWater para crear un programa open-source de fabricación en proceso 130nm CMOS [1][2].

**IHP SG13G2**: PDK BiCMOS 130nm con SiGe HBTs entre los más rápidos del mundo. IHP publicó el PDK en GitHub (`IHP-GmbH/IHP-Open-PDK`). Dos flujos digitales open-source (OpenROAD y OpenLane) y un flujo analógico basado en xschem/ngspice/KLayout están soportados. MPW shuttle runs gratuitos para universidades programados a través de 2025-2026 [3][4].

**Ecosistema abierto**: `open_pdks` (R. Timothy Edwards) provee instalación unificada para SKY130, GF180MCU e IHP SG13G2. OpenSUSI (Japón, 2024) lanzó iniciativa open-silicon adicional. NIST y Google lanzaron Nano Accelerator y Open Cryo PDK sobre SKY130 [5].

### 1.2 Relevancia para Context Teleport

Context Teleport es el **primer proyecto que integra parsers específicos para artefactos de flujos open-source EDA** (LibreLane, ORFS, Magic DRC, Netgen LVS, Liberty) con un sistema de gestión de conocimiento portable. No se encontró ningún proyecto comparable que combine:
- Parsing de artefactos EDA → conocimiento estructurado para agentes AI
- Sincronización Git con merge a nivel de sección
- Soporte multi-herramienta (Claude Code, Cursor, Gemini, OpenCode)
- Skills pack específico para IHP SG13G2

**Gap identificado**: La comunidad open-source EDA carece de herramientas para capturar y compartir el conocimiento tácito generado durante el uso de PDKs open-source. Context Teleport llena este gap.

### 1.3 Referencias Clave

- [1] [SkyWater SKY130 Open-Source PDK](https://www.skywatertechnology.com/sky130-open-source-pdk/)
- [2] [Google/SkyWater PDK (GitHub)](https://github.com/google/skywater-pdk)
- [3] [IHP Open Source PDK](https://www.ihp-microelectronics.com/services/research-and-prototyping-service/fast-design-enablement/open-source-pdk)
- [4] Scholz, R. "The IHP OpenPDK Initiative", [ESSERC 2024](https://mos-ak.org/bruges_2024/publication/1_Scholz_ESSERC_2024_IHP_OpenPDK.pdf)
- [5] [open_pdks (GitHub)](https://github.com/RTimothyEdwards/open_pdks)

---

## 2. AI/LLM + Electronic Design Automation

### 2.1 Landscape General

El campo de LLM para EDA ha experimentado un crecimiento explosivo entre 2023-2025. Los trabajos se organizan en varias categorías:

#### 2.1.1 LLMs de Dominio Específico para Chip Design

**ChipNeMo** (NVIDIA, ICCAD 2023, arXiv:2311.00176): LLM adaptado al dominio de diseño de chips mediante tokenización adaptativa, pretraining continuo de dominio, alineación con instrucciones de dominio, y modelos de retrieval adaptados. Tres aplicaciones: chatbot de ingeniería, generación de scripts EDA, y resumen de bugs. Con 13B parámetros, iguala o supera a LLMs genéricos de 70B en tareas de chip design. Entrenado en 128 A100 GPUs con <1.5% del costo de pretraining original [6][7].

**Impacto**: ChipNeMo demostró que la adaptación de dominio es viable y necesaria para EDA, pero es un proyecto interno de NVIDIA sin disponibilidad pública.

#### 2.1.2 Agentes Autónomos para EDA

**ChatEDA** (IEEE TCAD, Vol. 43, No. 10, Oct 2024, arXiv:2308.10204): Agente autónomo que usa AutoMage (LLaMA2 70B fine-tuned con QLoRA) para descomponer tareas, generar scripts Python, y ejecutar flujos RTL-to-GDSII completos via OpenROAD. Benchmark ChatEDA-bench con 50 tareas. AutoMage2 logró 82% Grade A vs. 62% de GPT-4 [8][9].

**MCP4EDA** (arXiv:2507.19570, 2025): **Primer servidor MCP para automatización RTL-to-GDSII**. Integra Yosys, Icarus Verilog, OpenLane, GTKWave y KLayout en una interfaz LLM unificada. Contribución principal: optimización de síntesis backend-aware donde LLMs analizan métricas post-layout para refinar scripts TCL iterativamente. Mejoras de 15-30% en timing closure y 10-20% en reducción de área [10][11].

**AiEDA** (ACM FAIML 2025): Framework agentic AI en 4 etapas (arquitectura, RTL, síntesis, physical design) usando LangGraph/GPT-4o con OpenROAD para feedback. Usa RAG con MG-Verilog dataset [12].

**EDAid** (2025): Sistema de colaboración multi-agente donde múltiples agentes con pensamientos divergentes convergen hacia un objetivo común. Cada agente controlado por ChipLlama, LLMs expertos fine-tuned para automatización de flujos EDA [13].

**OpenROAD Agent** (ICLAD 2025): Generador de scripts self-correcting para OpenROAD. Trabajo relacionado: "EDA Corpus: A Large Language Model Dataset for Enhanced Interaction with OpenROAD" (LAD 2024) [14].

**AutoEDA** (arXiv:2508.01012, 2025): Automatización de flujos EDA mediante agentes LLM basados en microservicios.

#### 2.1.3 Surveys y Análisis del Campo

**LLM4EDA Survey** (arXiv:2401.12224, Jan 2024): Survey comprehensivo del progreso de LLMs en EDA, cubriendo generación RTL, verificación, optimización, y physical design.

**"A Survey of Research in Large Language Models for EDA"** (ACM TODAES, arXiv:2501.09655, Jan 2025): Survey actualizado del campo.

**"Large Language Models for EDA: Future or Mirage?"** (ACM TODAES, 2025): Análisis crítico de las capacidades reales vs. promesas de LLMs en EDA.

**"The Dawn of AI-Native EDA"** (arXiv:2403.07257, 2024): Propone el concepto de Large Circuit Models (LCM) — framework de modelos foundation alineados para cada etapa de diseño.

**"Foundation AI Models for VLSI Circuit Design and EDA"** (Xie et al., 2025): Survey de modelos foundation aplicados a circuitos VLSI.

#### 2.1.4 Verificación Asistida por AI

LLMs han logrado avances significativos en verificación funcional, especialmente en traducción de especificaciones NL a SystemVerilog assertions (SVAs). AssertLLM genera assertions directamente desde documentos de especificación antes de la fase RTL. En verificación asistida por AI para semiconductores, se reportan mejoras de 35.4% en cobertura funcional, 92.7% en precisión de generación de assertions, reducción de 47.2% en tiempo de localización de bugs, y 35.7% menos tiempo total de verificación [15].

### 2.2 Posicionamiento de Context Teleport

| Aspecto | Literatura existente | Context Teleport |
|---------|---------------------|------------------|
| **Objetivo** | Automatizar tareas EDA (RTL gen, script gen, verification) | Gestionar y compartir **conocimiento** generado durante tareas EDA |
| **Interacción** | LLM ↔ herramienta EDA (1:1) | Múltiples agentes ↔ múltiples herramientas ↔ conocimiento compartido |
| **Persistencia** | Dentro de una sesión / ejecución | Cross-sesión, cross-agente, cross-herramienta via Git |
| **Colaboración** | Single-user (ChipNeMo, ChatEDA) | Multi-usuario, multi-agente, multi-herramienta |
| **Artefactos EDA** | Input para LLM (prompts, RAG) | Parseados y almacenados como conocimiento estructurado reutilizable |
| **PDK knowledge** | Entrenamiento/fine-tuning | Skills portables y compartibles con feedback loop |

**Gap crítico identificado**: Toda la literatura de LLM+EDA se enfoca en **automatizar tareas individuales** (generación de código, script execution, verificación). **Ningún trabajo aborda la gestión del conocimiento colaborativo** generado por equipos usando estas herramientas. Context Teleport es complementario a ChatEDA/MCP4EDA: mientras ellos automatizan la ejecución, Context Teleport captura, estructura y comparte el conocimiento resultante.

### 2.3 Referencias Clave

- [6] Liu, M. et al. "ChipNeMo: Domain-Adapted LLMs for Chip Design", [arXiv:2311.00176](https://arxiv.org/abs/2311.00176), 2023
- [7] [NVIDIA EDA Research](https://research.nvidia.com/labs/electronic-design-automation/)
- [8] He, Z. et al. "ChatEDA: A Large Language Model Powered Autonomous Agent for EDA", [IEEE TCAD 2024](https://dl.acm.org/doi/abs/10.1109/TCAD.2024.3383347)
- [9] [ChatEDA (arXiv)](https://arxiv.org/abs/2308.10204)
- [10] "MCP4EDA: LLM-Powered MCP RTL-to-GDSII Automation", [arXiv:2507.19570](https://arxiv.org/abs/2507.19570)
- [11] [MCP4EDA GitHub](https://github.com/NellyW8/MCP4EDA)
- [12] "AI-Driven Automation for Digital Hardware Design: A Multi-Agent Generative Approach", [ACM FAIML 2025](https://dl.acm.org/doi/10.1145/3748382.3748388)
- [13] [Awesome-LLM4EDA (GitHub)](https://github.com/Thinklab-SJTU/Awesome-LLM4EDA)
- [14] Wu, B.-Y. et al. "OpenROAD Agent", ICLAD 2025
- [15] [AI-Driven Design Verification of Semiconductor ICs](https://www.ijisae.org/index.php/IJISAE/article/download/7693/6711/13087)

---

## 3. Gestión del Conocimiento para Equipos de Hardware

### 3.1 Architecture Decision Records (ADRs)

Los ADRs son un concepto establecido en ingeniería de software que captura decisiones arquitectónicas junto con su contexto y consecuencias. Un Architectural Decision (AD) es una elección de diseño justificada que aborda un requisito funcional o no-funcional que es arquitectónicamente significativo [16].

**Adopción en práctica**: Un estudio MSR en GitHub encontró que la adopción de ADRs sigue siendo baja, aunque crece cada año. ~50% de los repositorios con ADRs contienen solo 1-5 registros, sugiriendo que el concepto se ha probado pero no adoptado definitivamente. En repositorios con uso más sistemático, la documentación de decisiones fue una actividad de equipo de 2+ usuarios durante períodos prolongados [17].

**LLMs para generación de ADRs** (arXiv:2403.01709, Mar 2024): Estudio exploratorio sobre la capacidad de LLMs para generar ADRs automáticamente. Architectural Knowledge Management (AKM) incluye la gestión organizada de información sobre decisiones y diseño arquitectónico. ADRs documentan contexto de decisión, decisiones tomadas, y diversos aspectos, promoviendo transparencia, colaboración y comprensión. A pesar de sus beneficios, la adopción ha sido lenta por limitaciones de tiempo e inconsistencia [18].

**Aplicabilidad a hardware**: La definición formal incluye "software *and/or hardware* systems", indicando que los ADRs son aplicables al diseño de hardware, aunque su adopción en este dominio es mínima.

### 3.2 Gestión del Conocimiento en IC Design

**Collaborative Project and IP Management para IC Design** (IEEE, 2007): Trabajo temprano que propone plataformas de información integrando módulos de gestión de proyectos, gestión de conocimiento de diseño, y entornos de trabajo colaborativo para la industria IC [19].

**Design Data Management para Semiconductores** (Keysight/Cliosoft, 2024): DDM es crucial para eficiencia de colaboración multi-sitio, facilitando knowledge sharing y acelerando innovación en semiconductores. Keysight adquirió Cliosoft para herramientas de version control, integración de datos y herramientas, y colaboración en EDA. Nota relevante: Git proporciona "poor user experiences and inefficient workflows" para archivos binarios grandes típicos de EDA [20][21].

**Si2 Collaborative Data Model for AI/ML in EDA** (Si2, Jul 2024): Modelo de datos colaborativo para AI/ML en EDA, propuesto por la comunidad de proveedores y usuarios que innovan en estándares [22].

**Collaborative Product Design & Distributed Knowledge Management**: CPD es un proceso knowledge-intensive que abarca diseño conceptual, detallado, análisis, proceso y evaluación. La gestión distribuida del conocimiento de ingeniería es una tarea clave para industrias con equipos distribuidos [23].

### 3.3 Gap de Investigación

| Aspecto | Software Engineering | IC/Hardware Design |
|---------|---------------------|--------------------|
| ADRs | Bien establecidos (MADR, ADR Tools) | Virtualmente inexistentes |
| Knowledge Management Tools | Notion, Confluence, wikis | Propietarios (Cliosoft DDM, Perforce) |
| Version Control | Git (estándar) | Git para código, sistemas propietarios para datos de diseño |
| AI-assisted knowledge capture | Emergente (2024-2025) | No explorado |

**Gap crítico**: No existe un sistema de gestión del conocimiento diseñado específicamente para equipos de diseño de hardware que:
1. Capture conocimiento tácito de PDK de forma estructurada
2. Use ADRs para decisiones de diseño de chips
3. Integre parsers de artefactos EDA
4. Soporte colaboración cross-herramienta entre agentes AI

Context Teleport es **el primer sistema que aplica ADRs formales al diseño de hardware** con soporte de agentes AI.

### 3.4 Referencias Clave

- [16] [Architecture Decision Records (adr.github.io)](https://adr.github.io/)
- [17] "Using Architecture Decision Records in Open Source Projects – An MSR Study on GitHub", [ResearchGate](https://www.researchgate.net/publication/371709784_Using_Architecture_Decision_Records_in_Open_Source_Projects_-_An_MSR_Study_on_GitHub)
- [18] "Can LLMs Generate Architectural Design Decisions?", [arXiv:2403.01709](https://arxiv.org/html/2403.01709v1)
- [19] "Integrate Collaborative Project and IP Asset Management for IC Design", [IEEE Xplore](https://ieeexplore.ieee.org/document/4281522/)
- [20] [Keysight Semiconductor Design Data Management Best Practices](https://www.keysight.com/blogs/en/tech/sim-des/2024/4/15/semiconductor-design-data-management-best-practices)
- [21] [Keysight DDM Version Control for Semiconductor Design](https://semiwiki.com/eda/keysight-eda/335129-version-control-data-and-tool-integration-collaboration/)
- [22] [Si2 Collaborative Data Model for AI/ML in EDA](https://si2.org/wp-content/uploads/2024/07/memberpub_Si2_Collaborative_Data_Model_for_AIML_in_EDA.pdf)
- [23] "Enabling collaborative product design through distributed engineering knowledge management", [ResearchGate](https://www.researchgate.net/publication/223330344_Enabling_collaborative_product_design_through_distributed_engineering_knowledge_management)

---

## 4. Multi-Agent Context Sharing y MCP

### 4.1 Model Context Protocol (MCP)

**MCP** fue introducido por Anthropic en noviembre 2024 como un estándar abierto para estandarizar cómo los sistemas AI integran y comparten datos con herramientas y sistemas externos. Descrito como "USB-C for AI", MCP provee una interfaz universal JSON-RPC client-server para lectura de archivos, ejecución de funciones, y manejo de prompts contextuales [24][25].

**Adopción**: En marzo 2025, OpenAI adoptó MCP oficialmente. En diciembre 2025, Anthropic donó MCP a la Agentic AI Foundation (AAIF) bajo la Linux Foundation, co-fundada por Anthropic, Block y OpenAI. 97M descargas mensuales de SDK [26][27].

**MCP Spec 2025-11-25**: La especificación actual (noviembre 2025) define primitivas de prompts, resources, y tools como lenguaje compartido entre agentes [28].

### 4.2 Protocolos Complementarios

**A2A (Agent-to-Agent Protocol)** (Google, abril 2025): Protocolo para workflows colaborativos entre agentes. Complementa MCP: MCP estandariza acceso a capacidades (agente ↔ mundo exterior), A2A habilita workflows colaborativos (agente ↔ agente) [29].

**Survey de protocolos de interoperabilidad** (arXiv:2505.02279, mayo 2025): Identifica 4 protocolos clave:
- **MCP**: JSON-RPC client-server para invocación de herramientas
- **ACP** (Agent Communication Protocol): REST-native para respuestas multimodales asíncronas
- **A2A**: Peer-to-peer task outsourcing via Agent Cards
- **ANP** (Agent Network Protocol): Descubrimiento descentralizado con identidad DID [30]

### 4.3 Sistemas Multi-Agente con Conocimiento Compartido

**"Multi-Agent Collaboration Mechanisms: A Survey of LLMs"** (arXiv:2501.06322, Jan 2025): Survey comprehensivo de mecanismos de colaboración en Multi-Agent Systems (MAS) basados en LLMs. Cubre coordinación, knowledge sharing, y resolución colectiva de problemas [31].

**"Thought Communication in Multiagent Collaboration"** (NeurIPS 2025): Introduce paradigma de "thought communication" — agentes interactúan directamente "mind-to-mind" compartiendo pensamientos latentes, no solo tokens de lenguaje natural [32].

**"Analyzing Information Sharing and Coordination in Multi-Agent Planning"** (2025): Construye un MAS para planificación de viajes con un **notebook para compartición estructurada de información** y un **orquestador para coordinación reflexiva**. Directamente relevante al concepto de persistent knowledge via shared notebook [33].

**"Cache-to-Cache (C2C)"** (2025): Comunicación semántica directa entre LLMs usando KV-cache interno, sin generar texto. Relacionado con context sharing eficiente a nivel de modelo.

**CoALA: Cognitive Architectures for Language Agents** (TMLR, 2024): Framework con memoria modular, espacio de acciones, y toma de decisiones para agentes de lenguaje. El componente de memoria modular es directamente relevante a conocimiento persistente [34].

**"Advancing Multi-Agent Systems Through MCP"** (arXiv:2504.21030, abril 2025): Arquitectura, implementación y aplicaciones de sistemas multi-agente habilitados por MCP [35].

### 4.4 Posicionamiento de Context Teleport

| Aspecto | MCP estándar | A2A | Context Teleport |
|---------|-------------|-----|------------------|
| **Comunicación** | Agente ↔ herramienta (síncrono) | Agente ↔ agente (asíncrono) | Agente ↔ store ↔ agente (Git-backed) |
| **Persistencia** | En memoria (sesión) | Por tarea | Permanente (Git repo) |
| **Scope** | Conexión 1:1 | Workflow n:n | Equipo completo + control de visibilidad |
| **Knowledge** | No gestionado | No gestionado | Estructurado con ADRs, skills, metadata |
| **Merge** | N/A | N/A | Section-level merge + AI conflict resolution |
| **Offline** | No | No | Sí (Git local) |

**Gap crítico**: MCP habilita la *comunicación* entre agentes y herramientas. A2A habilita la *coordinación* entre agentes. **Ninguno aborda la persistencia y gestión del conocimiento generado** durante estas interacciones. Context Teleport llena este gap como una capa de *memoria colectiva* sobre MCP.

### 4.5 MCP4EDA vs. Context Teleport

**MCP4EDA** (arXiv:2507.19570) es el trabajo más cercano en la intersección MCP + EDA: un servidor MCP que controla herramientas EDA. Sin embargo:
- MCP4EDA automatiza la **ejecución** de flujos EDA via MCP
- Context Teleport gestiona el **conocimiento** generado durante flujos EDA via MCP
- Son complementarios: MCP4EDA podría usar Context Teleport para almacenar y compartir los insights generados durante sus optimizaciones iterativas

### 4.6 Referencias Clave

- [24] [Introducing the Model Context Protocol (Anthropic)](https://www.anthropic.com/news/model-context-protocol)
- [25] [Model Context Protocol (Wikipedia)](https://en.wikipedia.org/wiki/Model_Context_Protocol)
- [26] [One Year of MCP: November 2025 Spec Release](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/)
- [27] [MCP Official Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [28] [MCP & Multi-Agent AI: Building Collaborative Intelligence](https://onereach.ai/blog/mcp-multi-agent-ai-collaborative-intelligence/)
- [29] [Announcing the Agent2Agent Protocol (A2A) - Google](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [30] "A Survey of Agent Interoperability Protocols", [arXiv:2505.02279](https://arxiv.org/html/2505.02279v1)
- [31] "Multi-Agent Collaboration Mechanisms: A Survey of LLMs", [arXiv:2501.06322](https://arxiv.org/html/2501.06322v1)
- [32] "Thought Communication in Multiagent Collaboration", [NeurIPS 2025](https://neurips.cc/virtual/2025/poster/115550)
- [33] "Analyzing Information Sharing and Coordination in Multi-Agent Planning", 2025
- [34] "CoALA: Cognitive Architectures for Language Agents", TMLR 2024
- [35] "Advancing Multi-Agent Systems Through MCP", [arXiv:2504.21030](https://arxiv.org/html/2504.21030v1)

---

## 5. Merge y Edición Colaborativa Estructurada

### 5.1 CRDTs para Edición Colaborativa

**Peritext** (ACM CSCW 2022): CRDT para edición colaborativa de rich text. Soporta formateo inline pero explícitamente deja como trabajo futuro las estructuras de bloque (headings, listas, tablas). El paper reconoce que "further work is required to ensure edits to block structures can be merged while preserving author intent" [36][37].

**Eg-walker** (arXiv:2409.14252, Sep 2024): Algoritmo colaborativo eficiente para texto plano que iguala o supera a algoritmos centralizados sin requerir servidor central. Enfocado en texto plano, no estructurado [38].

**Tree CRDTs con Move Operations** (Kleppmann et al.): Operaciones de move altamente disponibles para árboles replicados, aplicable a sistemas de archivos distribuidos y documentos con estructura jerárquica (JSON, XML) [39].

**JSON CRDT Extensions** (Da & Kleppmann, PaPoC 2024): Extensiones de JSON CRDTs con operaciones de move [40].

### 5.2 Merge Estructurado en Version Control

El merge 3-way estándar de Git opera a nivel de línea. Herramientas como JDime (Java) y Spork (Java) implementan merge semiestructurado basado en AST. Sin embargo, **no se encontró ningún trabajo que implemente merge a nivel de sección para documentos markdown**.

### 5.3 Posicionamiento de Context Teleport

El **section-level merge** de Context Teleport (`merge_sections.py`) es una contribución técnica novel:
- Parsea documentos markdown en secciones delimitadas por headers `## `
- Compara cada sección independientemente en un merge 3-way
- Permite que dos ingenieros editen diferentes secciones del mismo documento sin conflicto
- No requiere CRDT ni servidor central (opera sobre Git)
- La resolución de conflictos asistida por LLM complementa el merge automático

**Gap identificado**: No existe en la literatura un algoritmo de merge a nivel de sección para documentos markdown en el contexto de gestión del conocimiento. Los CRDTs (Peritext, Eg-walker) abordan la edición en tiempo real de texto, pero no el merge offline de documentos estructurados en Git. El approach de Context Teleport es más práctico para equipos de ingeniería que usan Git como backbone.

### 5.4 Referencias Clave

- [36] Litt, G. et al. "Peritext: A CRDT for Collaborative Rich Text Editing", [ACM CSCW 2022](https://dl.acm.org/doi/10.1145/3555644)
- [37] [Peritext (Ink & Switch)](https://www.inkandswitch.com/peritext/)
- [38] "Collaborative Text Editing with Eg-walker", [arXiv:2409.14252](https://arxiv.org/html/2409.14252v1)
- [39] Kleppmann, M. "A highly-available move operation for replicated trees", [PDF](https://martin.kleppmann.com/papers/move-op.pdf)
- [40] Da, L. & Kleppmann, M. "Extending JSON CRDTs with move operations", PaPoC 2024

---

## 6. Venues y Workshops Relevantes

### 6.1 WOSET (Workshop on Open-Source EDA Technology)

WOSET 2024 se celebró el 18 de noviembre de 2024 (virtual). Co-chairs: M. Guthaus y J. Renau (UC Santa Cruz). Papers notables incluyen ORAssistant (RAG para OpenROAD), SoCMake, pyngspice, y FOSS CAD/EDA para desarrollo de workforce. Todos los submissions requieren repositorios open-source [41].

**Relevancia**: WOSET es el venue ideal para presentar los parsers de artefactos EDA y la integración con flujos open-source de Context Teleport.

### 6.2 Otros Venues Relevantes

| Venue | Tipo | Relevancia para Context Teleport |
|-------|------|----------------------------------|
| **DAC** (Design Automation Conference) | Conferencia premier | LLM+EDA, collaborative design |
| **ICCAD** | Conferencia premier | EDA tools, AI-assisted design |
| **DATE** | Conferencia premier | Design automation, European community |
| **WOSET** | Workshop | Open-source EDA tools y parsers |
| **OSDA** (Open Source Design Automation) | Workshop (co-located DATE) | Open-source EDA methodology |
| **ICSE** | Conferencia (Software Eng.) | Knowledge management, ADRs, skills |
| **CSCW** | Conferencia (Collaboration) | Section-level merge, collaborative editing |
| **ACM TODAES** | Journal | AI-assisted EDA workflows |
| **IEEE Access** | Journal (open access) | Multi-agent EDA collaboration |
| **Elsevier Integration, the VLSI Journal** | Journal | VLSI knowledge management |

### 6.3 Referencias

- [41] [WOSET Workshop](https://woset-workshop.github.io/)

---

## 7. Análisis de Gaps y Oportunidades de Publicación

### 7.1 Mapa de Gaps

```
                        ┌─────────────────────────────────────────┐
                        │      EXISTENTE EN LITERATURA            │
                        ├─────────────────────────────────────────┤
                        │ • LLM para generación RTL (ChipNeMo)   │
                        │ • Agentes EDA autónomos (ChatEDA)       │
                        │ • MCP como protocolo (spec + surveys)   │
                        │ • MCP para EDA (MCP4EDA)                │
                        │ • CRDTs para edición colaborativa       │
                        │ • ADRs en software engineering          │
                        │ • PDKs open-source (SKY130, SG13G2)     │
                        │ • Multi-agent collaboration surveys     │
                        └─────────────────────────────────────────┘

                        ┌─────────────────────────────────────────┐
                        │      GAPS (Context Teleport)            │
                        ├─────────────────────────────────────────┤
                        │ ★ Knowledge management para EDA teams   │
                        │ ★ ADRs aplicados a hardware design      │
                        │ ★ Section-level merge para markdown     │
                        │ ★ AI conflict resolution en Git         │
                        │ ★ EDA artifact parsing → structured KM  │
                        │ ★ Cross-tool context portability (5+)   │
                        │ ★ Skill lifecycle con feedback loop     │
                        │ ★ PDK tacit knowledge codification      │
                        │ ★ Multi-agent persistent shared memory  │
                        └─────────────────────────────────────────┘
```

### 7.2 Propuestas de Publicación Priorizadas

#### Propuesta 1: WOSET 2025 (Prioridad Máxima)
**Título tentativo**: "Context Teleport: A Portable Knowledge Store for Collaborative Open-Source EDA Workflows"

**Enfoque**: Parsers de artefactos EDA (DRC, LVS, Liberty, configs), integración con flujos OpenROAD/LibreLane, skills pack para IHP SG13G2, y caso de uso de MPW shuttle team.

**Fortalezas**:
- WOSET requiere open-source → Context Teleport cumple
- Complementa trabajos existentes como MCP4EDA y ORAssistant
- Caso de uso concreto con IHP SG13G2
- Ningún trabajo en WOSET cubre knowledge management

#### Propuesta 2: DAC/ICCAD 2025-2026
**Título tentativo**: "AI-Assisted Knowledge Management for Multi-Agent Collaborative Chip Design"

**Enfoque**: Framework completo de Context Teleport como sistema de knowledge management para equipos EDA multi-agente. Incluye: section-level merge, AI conflict resolution, cross-tool portability, skill lifecycle.

**Diferenciación respecto a**: ChatEDA (ejecución vs. conocimiento), MCP4EDA (complementario), ChipNeMo (dominio-adaptación vs. knowledge sharing).

#### Propuesta 3: CSCW/CHI 2026
**Título tentativo**: "Section-Level Merge with LLM Conflict Resolution for Collaborative Engineering Documentation"

**Enfoque**: El algoritmo de section-level merge y la resolución de conflictos asistida por LLM como contribución a la edición colaborativa. Comparación con CRDTs (Peritext, Eg-walker) mostrando que para equipos de ingeniería que usan Git, un approach basado en merge es más práctico.

#### Propuesta 4: ICSE/ESEC-FSE 2026
**Título tentativo**: "Architecture Decision Records for Hardware Design: Bridging Software Engineering Practices to EDA Teams"

**Enfoque**: Adopción de ADRs en diseño de hardware con soporte de agentes AI. Estudio del ciclo de vida de skills con feedback loop como forma de knowledge management continuo.

#### Propuesta 5: IEEE Access / ACM TODAES (Journal)
**Título tentativo**: "Multi-Agent Context Portability Framework for Heterogeneous AI-Assisted EDA Workflows"

**Enfoque**: Paper extenso cubriendo la arquitectura completa: formato neutro, adaptadores bidireccionales para 5 herramientas, protocolo MCP, sincronización Git con scope-awareness, y evaluación con equipo de 4 ingenieros en MPW shuttle.

---

## 8. Conclusiones

### 8.1 Estado del Arte Resumido

1. **LLM+EDA** es un campo explosivo (2023-2025) pero enfocado en **automatización de tareas**, no en gestión del conocimiento
2. **MCP** es el estándar de facto para integración de agentes AI con herramientas, con adopción masiva
3. **ADRs** están bien establecidos en software pero **no adoptados en hardware design**
4. **CRDTs** para edición colaborativa no cubren merge offline de documentos estructurados en Git
5. **PDKs open-source** (SKY130, SG13G2) están democratizando el chip design pero carecen de herramientas de knowledge management
6. **Sistemas multi-agente** investigan comunicación y coordinación pero no **persistencia de conocimiento** generado

### 8.2 Contribución Única de Context Teleport

Context Teleport ocupa una posición única en la intersección de 4 áreas que **no están conectadas en la literatura actual**:

```
    Open-Source EDA  ──────────┐
         ↓                     │
    EDA Artifact Parsing       │
         ↓                     ├── Context Teleport
    Knowledge Management  ─────┤    (intersección única)
         ↓                     │
    Multi-Agent MCP  ──────────┤
         ↓                     │
    Collaborative Merge  ──────┘
```

Ningún trabajo existente combina estas capacidades. Esta intersección multi-disciplinaria es la base más fuerte para publicaciones de alto impacto.

---

*Revisión bibliográfica completada el 2026-02-27. Basada en búsquedas en Google Scholar, arXiv, IEEE Xplore, ACM Digital Library, y web general. 40+ fuentes consultadas.*
