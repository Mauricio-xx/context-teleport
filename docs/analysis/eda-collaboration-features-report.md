# Informe de Análisis: Context Teleport - Capacidades de Colaboración para Equipos EDA/PDK/Chip Design

## Contexto

Este documento presenta un análisis exhaustivo del proyecto **Context Teleport** y sus capacidades actuales orientadas al desarrollo colaborativo entre equipos de personas en el área de electrónica, sistemas EDA (Electronic Design Automation), desarrollo de PDK (Process Design Kit) y diseño de chips. El objetivo es servir como base para una búsqueda del estado del arte en literatura científica (IEEE, Elsevier, ACM) y evaluar potenciales publicaciones.

---

## 1. Descripción General del Proyecto

**Context Teleport** es un almacén de contexto portátil, respaldado por Git, diseñado para agentes de codificación basados en IA. Su propósito fundamental es resolver el problema de **contexto atrapado** (trapped context): el conocimiento acumulado por agentes de IA durante sesiones de trabajo queda encerrado en formatos propietarios de herramientas específicas, en una sola máquina, sin forma estándar de compartirlo entre dispositivos, equipos o herramientas diferentes.

- **Lenguaje**: Python 3.11+
- **Licencia**: AGPL-3.0-or-later
- **Schema actual**: v0.4.0
- **Protocolo**: MCP (Model Context Protocol) con 23 tools, 13 resources, 4 prompts
- **Herramientas soportadas**: Claude Code, OpenCode, Codex, Gemini CLI, Cursor

### Archivos clave del proyecto
- `src/ctx/mcp/server.py` - Servidor MCP (23 tools, 13 resources, 4 prompts)
- `src/ctx/sync/git_sync.py` - Motor de sincronización Git
- `src/ctx/core/store.py` - Almacén de contexto
- `src/ctx/core/merge_sections.py` - Merge a nivel de sección markdown
- `src/ctx/eda/` - Módulo completo de soporte EDA
- `src/ctx/adapters/` - Adaptadores cross-tool (5 herramientas)
- `src/ctx/sources/github.py` - Importador de issues de GitHub

---

## 2. Arquitectura de Colaboración

### 2.1 Modelo de Datos Colaborativo

El bundle de contexto (`.context-teleport/`) está diseñado explícitamente para colaboración multi-persona y multi-agente:

```
.context-teleport/
  manifest.json              # Metadata del proyecto + miembros del equipo
  knowledge/*.md             # Entradas de conocimiento (una por archivo)
  knowledge/.meta.json       # Atribución de autoría por entrada
  knowledge/.scope.json      # Control de visibilidad (public/private/ephemeral)
  knowledge/decisions/*.md   # ADRs (Architecture Decision Records)
  skills/<name>/SKILL.md     # Skills compartidos entre agentes
  skills/<name>/.usage.ndjson    # Tracking de uso (append-only)
  skills/<name>/.feedback.ndjson # Feedback (append-only)
  skills/<name>/.proposals/      # Propuestas de mejora
  state/active.json          # Estado activo de sesión (local)
  state/roadmap.json         # Roadmap del proyecto (sincronizado)
  preferences/team.json      # Preferencias del equipo (sincronizadas)
  preferences/user.json      # Preferencias personales (local)
  history/sessions.ndjson    # Historial de sesiones (append-only)
```

### 2.2 Identificación de Agentes y Atribución

Cada agente se identifica mediante la variable de entorno `MCP_CALLER`:
- `mcp:claude-code`, `mcp:cursor`, `mcp:opencode`, `mcp:gemini`

Toda escritura (conocimiento, decisiones, skills, sesiones, feedback) registra automáticamente qué agente realizó la acción, cuándo, y desde qué herramienta. Esto permite **trazabilidad completa** de contribuciones.

### 2.3 Sistema de Scoping (Control de Visibilidad)

Tres niveles de alcance aplicados uniformemente a conocimiento, decisiones y skills:

| Scope | Sincronizado vía Git | Exportado a adaptadores | Persiste entre sesiones |
|---|---|---|---|
| **public** (default) | Sí | Sí | Sí |
| **private** | No (gitignored) | No | Sí |
| **ephemeral** | No (gitignored) | No | No (se limpia con state clear) |

**Innovación**: Los archivos `.scope.json` sidecar **sí se sincronizan**, por lo que los colaboradores saben qué entradas tienen alcance restringido (sin ver el contenido).

---

## 3. Motor de Sincronización Git (Sync Engine)

### 3.1 Flujo Push/Pull

- **Push**: Filtrado por scope (solo archivos públicos), staging selectivo, commit, push
- **Pull**: Fetch + merge con detección de conflictos y múltiples estrategias de resolución

### 3.2 Merge a Nivel de Sección (Section-Level Merge)

**Archivo**: `src/ctx/core/merge_sections.py`

La innovación principal del sync engine: en lugar de tratar archivos markdown como unidades atómicas, el motor:
1. Parsea las versiones base, ours y theirs en secciones (divididas por headers `## `)
2. Compara cada sección independientemente
3. Merge sección por sección:
   - Sección sin cambios en ambos lados → mantener
   - Sección cambiada en un solo lado → tomar la versión cambiada
   - Sección cambiada en ambos lados → conflicto (solo para esa sección)
   - Secciones nuevas → incluir del lado que las agregó

**Implicación para EDA**: Cuando dos ingenieros editan diferentes secciones del mismo documento de conocimiento (ej. uno agrega información de timing y otro de DRC), los cambios se fusionan automáticamente sin conflicto.

### 3.3 Resolución de Conflictos

Cuatro estrategias implementadas:
1. **ours** (default): mantener versión local
2. **theirs**: tomar versión remota
3. **interactive**: TUI terminal por archivo
4. **agent** (la más sofisticada): El agente de IA inspecciona y resuelve conflictos a través de un flujo de 4 pasos via MCP tools:
   - `context_sync_pull(strategy="agent")` → detecta conflictos, persiste estado
   - `context_conflict_detail(file_path)` → inspección detallada con análisis por sección
   - `context_resolve_conflict(file_path, content)` → resolución por archivo
   - `context_merge_finalize()` → aplicar resoluciones y commit

**Estado persistente**: `.pending_conflicts.json` almacena el estado del conflicto entre llamadas MCP (necesario porque MCP es stateless).

---

## 4. Soporte Específico para EDA

### 4.1 Detección Automática de Proyectos EDA

**Archivo**: `src/ctx/eda/detect.py`

El sistema detecta automáticamente 4 tipos de proyecto EDA:

| Tipo | Marcadores | Skills sugeridos |
|---|---|---|
| **librelane** | `config.json` con `DESIGN_NAME` y `meta.version` 2/3 | configure-librelane, configure-pdn, debug-drc, debug-lvs, debug-timing |
| **orfs** (OpenROAD Flow Scripts) | `config.mk` con `DESIGN_NAME` o `PLATFORM` | configure-pdn, debug-drc, debug-lvs, debug-timing |
| **pdk** | directorio `libs.tech/` | debug-drc, debug-lvs, port-design |
| **analog** | `xschemrc`, `.xschemrc`, archivos `*.sch` | xschem-simulate, characterize-device, debug-drc, debug-lvs |

También detecta la variable de entorno `PDK_ROOT` y trata de inferir el nombre del PDK.

### 4.2 Parsers de Artefactos EDA (6 parsers)

**Directorio**: `src/ctx/eda/parsers/`

Protocolo base (`EdaImporter`): interfaz `can_parse()` + `parse()` + `describe()` que produce `ImportItem` (tipo, key, contenido markdown, fuente).

#### 4.2.1 LibreLane Config Parser (`librelane.py`)
- Parsea `config.json` de LibreLane (v2/v3)
- Extrae: nombre del diseño, PDK, flow stages, parámetros de diseño, configuración física, PDN, timing, overrides de PDK
- Categoriza parámetros en: Design, Physical, PDN, Timing, PDK-Specific Overrides
- Key: `librelane-config-<design>`

#### 4.2.2 LibreLane Metrics Parser (`metrics.py`)
- Parsea `state_in.json` de runs de LibreLane
- Extrae métricas de: síntesis, timing (WNS/TNS), DRC, LVS, routing, power
- Categoriza métricas automáticamente por prefijos de key
- Soporta modo directorio (escanea múltiples archivos de métricas)
- Key: `eda-metrics-<design>`

#### 4.2.3 Magic DRC Parser (`drc.py`)
- **Streaming parser**: no carga archivos completos (reportes DRC pueden tener millones de líneas)
- Extrae reglas de violación y conteos por regla
- Detecta archivos por: sufijo `.rpt`, nombre con "drc", o patrón de contenido
- Genera tabla ordenada por count descendente
- Key: `drc-summary-<design>`

#### 4.2.4 Netgen LVS Parser (`lvs.py`)
- Parsea reportes de comparación LVS de Netgen
- Extrae: resultado final (match/no-match), cell equivalences, device/net counts, pin mismatches, warnings
- Soporta tanto archivos individuales como directorios
- Key: `lvs-summary-<design>`

#### 4.2.5 ORFS Config Parser (`orfs.py`)
- Parsea `config.mk` de OpenROAD Flow Scripts
- Maneja: `export VAR = value`, `+=`, `?=`, continuaciones de línea con `\`
- Categoriza variables en: Process, Design, Libraries, Floorplan, Placement, Power, Routing, Timing, Checks
- Preserva comentarios inline como rationale
- Key: `orfs-config-<design>`

#### 4.2.6 Liberty Parser (`liberty.py`)
- Parsea headers de archivos Liberty `.lib` (no carga definiciones de celdas)
- Extrae: nombre de librería, corner PVT (process/voltage/temperature), unidades, default limits
- Infiere corner PVT del nombre de librería (e.g., `sg13g2_stdcell_typ_1p20V_25C`)
- **Modo directorio**: escanea todos los `.lib` y genera tabla de corners disponibles
- Key: `liberty-corners-<library-family>`

### 4.3 EDA Skills Pack

Repositorio separado de skills pre-construidos para tareas EDA comunes:
- `configure-librelane` - Configuración de flujos LibreLane
- `configure-pdn` - Redes de distribución de potencia
- `debug-drc` - Debug de violaciones DRC
- `debug-lvs` - Debug de mismatches LVS
- `debug-timing` - Análisis de reportes de timing
- `xschem-simulate` - Simulaciones con xschem
- `characterize-device` - Caracterización de dispositivos
- `port-design` - Portabilidad entre PDKs

### 4.4 Flujo de Trabajo EDA Individual (Ejemplo Documentado)

El ejemplo documentado en `docs/examples/eda-project.md` muestra un flujo individual con IHP SG13G2 130nm BiCMOS PDK:

1. Init proyecto + auto-detección de tipo LibreLane
2. Import de config → conocimiento estructurado del diseño
3. Run DRC → import resultados como conocimiento
4. Run LVS → import resultados
5. Import metrics del flow
6. Iteración: re-import sobrescribe con datos actualizados
7. Import de issues de GitHub del repo del PDK (IHP-Open-PDK)
8. Creación de skills específicos del proyecto (e.g., `sg13g2-pdn-config`)
9. Tracking de estado y blockers

### 4.5 Flujo de Trabajo Multi-Equipo EDA: MPW Shuttle

**Archivo**: `docs/examples/eda-team.md` (459 líneas)

Escenario completo de **4 ingenieros preparando un MPW shuttle run** con IHP SG13G2:

**Roles y herramientas**:
| Ingeniero | Herramienta AI | Dominio |
|---|---|---|
| Lukas | Claude Code | PDK cell library, device characterization, model updates |
| Amira | Cursor | LibreLane design flow, chip tapeout, timing closure |
| Jan | Gemini | DRC/LVS rule development, verification |
| Sofia | OpenCode | Analog design (xschem), bandgap/LNA simulation |

**Flujo de propagación cross-domain documentado**:
1. **Lukas** descubre que la resistencia de via5 es 4.5 ohm (no 2.8 como dice el PDK) → registra conocimiento + decisión
2. **Amira** pull, su agente (Cursor) analiza impacto: IR-drop sube de 12mV a ~19mV → decide apretar pitch de straps PDN
3. **Jan** pull, busca referencias del metal stack → encuentra la errata de via5 → ajusta sus reglas de verificación DRC
4. **Sofia** pull, su agente (OpenCode) evalúa: corriente de su bandgap es 10uA, impacto negligible → continúa con sus caracterizaciones

**Patrones demostrados**:
- **Propagación cross-dominio**: Medición PDK (Claude Code) → Decisión de flujo (Cursor) → Actualización de reglas (Gemini)
- **Import de artefactos EDA**: config, DRC, LVS, metrics importados como conocimiento estructurado
- **GitHub issue bridge**: Issues cerrados del PDK importados como baseline de decisiones
- **Colaboración 4 herramientas**: Claude Code + Cursor + Gemini + OpenCode compartiendo un store
- **Section-level merge**: Actualizaciones simultáneas al metal stack fusionadas automáticamente
- **Ciclo de feedback de skills**: `debug-drc` calificado bajo → propuesta → mejora aceptada
- **Skill específico del proyecto**: Checklist de MPW shuttle destilado de la experiencia del equipo
- **Handoff de sesión**: Amira → Lukas con preservación completa de contexto y blockers

**Relevancia para publicación**: Este ejemplo demuestra el escenario más fuerte de la herramienta - donde un hallazgo en un dominio (resistencia de via) genera un efecto cascada documentado y trazable a través de múltiples dominios y herramientas. Es el tipo de escenario que no tiene equivalente en la literatura actual de collaborative EDA.

---

## 5. Sistema de Gestión del Conocimiento

### 5.1 Conocimiento Estructurado
- Entradas markdown individuales con keys determinísticos
- Búsqueda full-text con ranking de relevancia (`context_search`)
- Acceso por dotpath genérico (`context_get`, `context_set`)
- Metadatos de autoría y timestamp

### 5.2 Architecture Decision Records (ADRs)
- Formato estándar ADR: Context, Decision, Consequences
- Numeración secuencial automática
- Estados: proposed, accepted, deprecated, superseded
- Inmutabilidad por diseño (solo se agregan nuevos, nunca se modifican)

### 5.3 Historial de Sesiones
- Log NDJSON append-only de resúmenes de sesión
- Registra: agente, resumen, knowledge agregado, decisiones tomadas, skills usados
- Merge-friendly (cada sesión es una línea independiente)

---

## 6. Sistema de Skills con Ciclo de Vida Completo

### 6.1 Creación y Almacenamiento
- Formato SKILL.md (YAML frontmatter + markdown body)
- Creación via MCP, CLI, o import de adaptadores

### 6.2 Tracking y Feedback
- Eventos de uso en `.usage.ndjson` (append-only)
- Ratings 1-5 con comentarios en `.feedback.ndjson`
- Estadísticas agregadas (SkillStats): uso, rating promedio, flag de atención

### 6.3 Propuestas de Mejora
- Los agentes proponen mejoras (nuevo contenido + rationale + diff)
- Review humano: accept/reject via CLI
- Push upstream a repos compartidos de skills via `gh` CLI

### 6.4 Auto-mejora Continua
- Skills con avg_rating < 3.0 y 2+ ratings se marcan como "needs attention"
- El servidor MCP incluye estas flags en las instrucciones dinámicas de onboarding
- Los agentes son informados proactivamente sobre skills que necesitan mejora

---

## 7. Interoperabilidad Cross-Tool

### 7.1 Adaptadores Bidireccionales
5 adaptadores para import/export entre:
- Claude Code (`.claude/mcp.json`, `.claude/skills/`)
- OpenCode (`opencode.json`)
- Codex (`AGENTS.md`, `.codex/instructions.md`)
- Gemini (`.gemini/settings.json`)
- Cursor (`.cursor/mcp.json`)

### 7.2 Servidor MCP Unificado
- Un solo binario funciona como CLI (con args en TTY) o como servidor MCP (stdin piped)
- Onboarding dinámico: instrucciones generadas del estado actual del store
- Auto-push on shutdown como safety net

### 7.3 GitHub Issue Bridge
- Import de issues como conocimiento estructurado
- Ranking inteligente de comentarios por relevancia (autor, asociación, reacciones, contenido)
- Issues cerrados convertibles a Decision Records automáticamente
- Filtrado por labels, estado, fecha

---

## 8. Innovaciones Técnicas Clave

| Innovación | Descripción | Relevancia Científica |
|---|---|---|
| **Section-level merge para markdown** | Merge 3-way a nivel de secciones `## ` en lugar de archivo completo | Resolución de conflictos en documentación colaborativa |
| **LLM-driven conflict resolution** | Agentes de IA resuelven conflictos de merge inspeccionando versiones y produciendo resoluciones | AI-assisted collaborative development |
| **EDA artifact parsing to structured knowledge** | Conversión de artefactos EDA (DRC, LVS, Liberty, configs) a conocimiento estructurado para agentes AI | AI-EDA integration, knowledge extraction |
| **Cross-tool context portability** | Formato neutro + adaptadores bidireccionales para 5 herramientas AI | Tool interoperability standards |
| **Skill lifecycle with feedback loop** | Skills compartibles con tracking de uso, feedback, propuestas de mejora, y upstream contribution | Collaborative knowledge management |
| **Scope-aware git sync** | Sincronización Git que respeta boundaries de visibilidad (public/private/ephemeral) | Privacy-aware collaboration |
| **Streaming EDA parsers** | Parseo eficiente de reportes DRC potencialmente masivos sin cargar en memoria | Scalable EDA data processing |
| **Deterministic key naming for re-import** | Keys determinísticos permiten actualizar artefactos sin acumular duplicados | Iterative design workflow support |
| **GitHub issue bridge with comment ranking** | Importación inteligente de issues de repos de PDKs open-source | Community knowledge aggregation |
| **Agent identity attribution** | Trazabilidad completa de qué agente/herramienta escribió cada pieza de contexto | Multi-agent accountability |

---

## 9. Áreas de Investigación Sugeridas para Búsqueda Bibliográfica

### 9.1 Colaboración en Diseño EDA / IC Design
- Collaborative EDA workflows
- Knowledge management in IC/VLSI design teams
- Design knowledge capture and reuse in semiconductor engineering
- PDK collaboration and community-driven PDK development

### 9.2 AI/LLM en Electronic Design Automation
- LLM-assisted chip design / EDA
- AI agents for hardware design verification (DRC, LVS)
- Machine learning for design rule debugging
- Natural language interfaces for EDA tools

### 9.3 Gestión del Conocimiento Colaborativo
- Knowledge management systems for engineering teams
- Architecture Decision Records (ADRs) in software/hardware engineering
- Collaborative context sharing in distributed development
- Version control for design knowledge

### 9.4 Model Context Protocol y Agentes AI
- MCP (Model Context Protocol) and AI agent interoperability
- Multi-agent collaboration systems
- Context portability across AI tools
- Skill-based agent architectures

### 9.5 Open-source EDA / Silicon
- Open-source PDK ecosystems (IHP SG13G2, SkyWater SKY130, GF180MCU)
- LibreLane, OpenROAD, Magic, Netgen, xschem toolchains
- Collaborative verification in open silicon projects
- Community-driven standard cell library development

### 9.6 Merge y Resolución de Conflictos
- Structured merge algorithms for semi-structured documents
- AI-assisted conflict resolution in version control
- Section-level merge strategies for collaborative editing
- CRDT alternatives for document collaboration

---

## 10. Resumen Ejecutivo para Potencial Publicación

**Context Teleport** presenta una combinación única de:

1. **Formato neutro de contexto** para agentes de IA con soporte multi-tool
2. **Soporte de dominio EDA** con parsers especializados para artefactos de diseño de chips
3. **Sincronización Git inteligente** con merge a nivel de sección y resolución de conflictos asistida por LLM
4. **Sistema de skills con ciclo de vida completo** incluyendo feedback, mejora y contribución upstream
5. **Flujos de trabajo colaborativos** específicos para equipos de diseño electrónico

Las contribuciones principales que podrían constituir publicaciones:

| Contribución Potencial | Venue Sugerido |
|---|---|
| AI-assisted knowledge management for collaborative EDA workflows | IEEE/ACM DAC, ICCAD, DATE |
| Section-level merge algorithm for structured design documentation | ACM CSCW, Elsevier JSS |
| Multi-agent context sharing framework for hardware design | IEEE Access, ACM TODAES |
| Open-source EDA artifact parsing for LLM integration | WOSET (Workshop on Open-Source EDA Technology) |
| Skill lifecycle management for AI agents in engineering teams | ICSE, ESEC/FSE |
| LLM-driven conflict resolution in collaborative design | CHI, UIST |

---

## 11. EDA Skills Pack - Detalle de Dominio Específico IHP SG13G2

El proyecto incluye un **pack de 8 skills EDA especializados** (`eda-skills-pack/`) con conocimiento profundo del PDK IHP SG13G2 130nm BiCMOS. Este pack es relevante para la publicación porque demuestra la viabilidad de codificar conocimiento experto de PDK en formato consumible por agentes AI.

### Skills y su Cobertura Técnica

| Skill | Contenido Técnico | Herramientas |
|---|---|---|
| `configure-librelane` | 50+ parámetros documentados para flujo RTL-to-GDS, configs mínimas/estándar/full-chip, pdk-conditionals | LibreLane, OpenROAD |
| `debug-drc` | Reglas DRC por categoría (PreCheck/Main/Extra), falsos positivos conocidos, violaciones FEOL/BEOL con fixes, gotchas de IHP (sin tapcells, sin via gen, grid 0.005um) | KLayout DRC |
| `debug-lvs` | Dispositivos reconocidos (MOSFETs, BJTs SiGe 350GHz fT, MIM caps, resistores), categorías de mismatch, extracción de parámetros | KLayout LVS, Netgen |
| `debug-timing` | Corners PVT (slow/typ/fast), guías de clock period para 130nm (15-30ns), fixes priorizados para setup/hold | OpenROAD/OpenSTA |
| `configure-pdn` | Metal stack IHP (Metal1-5 + TopMetal1/2 thick), max unslotted width 30um, scripts TCL completos | LibreLane PDN, ORFS |
| `characterize-device` | Metodología gm/ID, modelos PSP 103.6, lookup tables para sg13_lv/hv nmos/pmos | pygmid, xschem, ngspice |
| `xschem-simulate` | Setup completo (PDK clone, OpenVAF compilation, spiceinit), flujo schematic-to-sim, tipos de análisis | xschem, ngspice |
| `port-design` | Tabla de diferencias Sky130→IHP (voltajes, modelos, metal stack, std cells), procedimientos completos de migración analog/digital | Multi-tool |

### Relevancia para Publicación

Este skills pack demuestra:
1. **Codificación de conocimiento tácito de PDK** en formato portable y compartible
2. **Conocimiento acumulativo**: cada skill contiene información que típicamente toma semanas descubrir (falsos positivos DRC, gotchas de IHP, etc.)
3. **Reusabilidad cross-agent**: el mismo skill funciona en Claude Code, Cursor, OpenCode, etc.
4. **Dominio BiCMOS avanzado**: cubre tanto digital (CMOS) como tecnologías especializadas (BJTs SiGe HBT de 350 GHz)

---

## 12. Próximos Pasos: Búsqueda Bibliográfica

Basándose en la selección del usuario, la búsqueda del estado del arte cubrirá las **4 áreas** simultáneamente, priorizando por orden:

### Prioridad 1: Open-source Silicon Ecosystem
**Keywords**: open-source PDK, IHP SG13G2, SkyWater SKY130, collaborative chip design, open silicon, community EDA
**Venues**: WOSET, IEEE JSSC, ESSCIRC, DAC, CICC

### Prioridad 2: AI/LLM + EDA Collaboration
**Keywords**: LLM chip design, AI-assisted EDA, natural language hardware, LLM verification DRC LVS, AI agent semiconductor
**Venues**: DAC, ICCAD, DATE, ASP-DAC, MLCAD

### Prioridad 3: Knowledge Management for Hardware Teams
**Keywords**: design knowledge management VLSI, design reuse IC, architecture decision records hardware, collaborative design documentation
**Venues**: IEEE TODAES, Elsevier JSS, IEEE Access, Integration the VLSI Journal

### Prioridad 4: Multi-Agent Context Sharing
**Keywords**: multi-agent collaboration, MCP model context protocol, AI tool interoperability, context portability agents, skill-based AI
**Venues**: ICSE, CSCW, AAAI, NeurIPS (Agent workshops), AAMAS

El formato de publicación se decidirá después de identificar los gaps en la literatura.

---

## Verificación

Este informe se basa en la lectura directa de:
- Código fuente completo del proyecto (113 archivos Python, ~5,885 LOC)
- Documentación completa (52 archivos Markdown)
- EDA Skills Pack (8 skills especializados para IHP SG13G2)
- README, CONTRIBUTING, y archivos de configuración
- Ejemplos documentados de flujos de trabajo EDA y multi-agente

No se requieren cambios en el código. Este documento es solo para análisis y referencia para la búsqueda bibliográfica posterior.
