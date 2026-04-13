# PRD — Open WebUI Frontend

**Documento:** Product Requirements Document (Frontend)
**Producto:** Open WebUI v0.8.12
**Stack:** SvelteKit 2 + Svelte 5 + TypeScript + TailwindCSS 4 + Vite 5
**Versión PRD:** 1.0
**Fecha:** 2026-04-10
**Fuente:** Análisis exhaustivo de `Open-webui/src/`

---

## 1. Resumen ejecutivo

Open WebUI es una interfaz web tipo "ChatGPT" auto-hospedable, multilingüe (61 idiomas), con soporte para múltiples backends de LLM (Ollama, OpenAI, etc.), gestión de conocimiento (RAG), notas, canales colaborativos, ejecución de código (Pyodide), llamadas de voz/video, herramientas extensibles, y un panel de administración completo. Incorpora editor enriquecido (Tiptap), syntax highlighting (highlight.js + Shiki), renderizado matemático (KaTeX), diagramas (Mermaid), gráficos (Chart.js, Vega-Lite), mapas (Leaflet) y terminal (xterm.js).

**Objetivo del PRD:** Documentar todas las especificaciones técnicas, layout, librerías, elementos, efectos e iconografía necesarias para reconstruir o replicar el frontend con fidelidad.

---

## 2. Stack tecnológico

### 2.1 Framework principal

| Capa | Tecnología | Versión |
|---|---|---|
| Meta-framework | SvelteKit | ^2.5.27 |
| UI framework | Svelte | ^5.53.10 |
| Lenguaje | TypeScript | ^5.5.4 |
| Bundler | Vite | ^5.4.21 |
| Adapter | `@sveltejs/adapter-static` | ^3.0.2 (SSG, fallback `index.html`) |
| Style framework | TailwindCSS | ^4.0.0 |
| PostCSS | `@tailwindcss/postcss` | ^4.0.0 |
| Plugin tipografía | `@tailwindcss/typography` | ^0.5.13 |
| Plugin container queries | `@tailwindcss/container-queries` | ^0.1.1 |

**Modo de build:** SSG (Static Site Generation). Salida en `build/` con fallback `index.html` para SPA routing.

### 2.2 Editores y rich text

| Librería | Versión | Uso |
|---|---|---|
| `@tiptap/core` | ^3.0.7 | Editor base |
| `@tiptap/starter-kit` | ^3.0.7 | Extensiones básicas |
| `@tiptap/extension-bubble-menu` | ^3.0.7 | Menú flotante de selección |
| `@tiptap/extension-code-block-lowlight` | ^3.0.7 | Bloques de código con highlight |
| `@tiptap/extension-drag-handle` | ^3.4.5 | Handle de drag para items |
| `@tiptap/extension-file-handler` | ^3.0.7 | Drop de archivos |
| `@tiptap/extension-floating-menu` | ^3.0.7 | Menús flotantes |
| `@tiptap/extension-highlight` | ^3.3.0 | Resaltado de texto |
| `@tiptap/extension-image` | ^3.0.7 | Imágenes inline |
| `@tiptap/extension-link` | ^3.0.7 | Links |
| `@tiptap/extension-list` | ^3.0.7 | Listas |
| `@tiptap/extension-mention` | ^3.0.9 | @ menciones |
| `@tiptap/extension-table` | ^3.0.7 | Tablas |
| `@tiptap/extension-typography` | ^3.0.7 | Tipografía smart |
| `@tiptap/extension-youtube` | ^3.0.7 | Embeds de YouTube |
| `@tiptap/suggestion` | ^3.4.2 | Suggestion engine |
| `prosemirror-*` | múltiple | Capa baja del editor (state, view, model, schema, history, commands, keymap, markdown, tables) |
| `y-prosemirror` / `yjs` | ^1.3.7 / ^13.6.27 | Edición colaborativa CRDT |
| `codemirror` | ^6.0.1 | Editor de código (Settings, Functions, Tools) |
| `@codemirror/lang-python` | ^6.1.6 | |
| `@codemirror/lang-javascript` | ^6.2.2 | |
| `@codemirror/language-data` | ^6.5.1 | |
| `@codemirror/theme-one-dark` | ^6.1.2 | |
| `codemirror-lang-elixir` / `codemirror-lang-hcl` | | Lenguajes adicionales |

### 2.3 Renderizado de contenido

| Librería | Versión | Uso |
|---|---|---|
| `marked` | ^9.1.0 | Parser de Markdown |
| `dompurify` | ^3.2.6 | Sanitización HTML |
| `highlight.js` | ^11.9.0 | Syntax highlighting clásico |
| `shiki` | ^4.0.1 | Syntax highlighting moderno (TextMate) |
| `lowlight` | ^3.3.0 | Highlight para Tiptap |
| `katex` | ^0.16.22 | Renderizado de matemáticas LaTeX |
| `mermaid` | ^11.10.1 | Diagramas (flowchart, sequence, gantt, etc.) |
| `chart.js` | ^4.5.0 | Gráficos clásicos |
| `vega` / `vega-lite` | ^6.2.0 / ^6.4.1 | Visualizaciones declarativas |
| `leaflet` | ^1.9.4 | Mapas interactivos |
| `pdfjs-dist` | ^5.4.149 | Visor de PDF |
| `mammoth` | ^1.11.0 | Conversión .docx → HTML |
| `xlsx` | ^0.18.5 | Lectura/escritura Excel |
| `sql.js` | ^1.14.1 | SQLite en el navegador |
| `html2canvas-pro` | ^1.5.11 | Screenshots de elementos DOM |
| `jspdf` | ^4.0.0 | Exportación a PDF |

### 2.4 Editor + ejecución de código

| Librería | Uso |
|---|---|
| `pyodide` ^0.28.2 | Python en el navegador (worker) |
| `@pyscript/core` ^0.4.32 | PyScript runtime |
| `@xterm/xterm` ^6.0.0 | Terminal emulator |
| `@xterm/addon-fit` ^0.11.0 | Auto-fit del terminal |
| `@xterm/addon-web-links` ^0.12.0 | Links clickeables en terminal |
| `@xyflow/svelte` ^0.1.19 | Diagramas de nodos (flow charts) |

### 2.5 UI / UX libs

| Librería | Versión | Uso |
|---|---|---|
| `bits-ui` | ^2.0.0 | Headless UI primitives para Svelte |
| `tippy.js` | ^6.3.7 | Tooltips |
| `paneforge` | ^0.0.6 | Panes redimensionables (split layouts) |
| `@floating-ui/dom` | ^1.7.2 | Posicionamiento de tooltips/popovers |
| `focus-trap` | ^7.6.4 | Trap de foco en modales |
| `sortablejs` | ^1.15.6 | Drag & drop sortable |
| `svelte-sonner` | ^0.3.19 | Toasts/notificaciones |
| `svelte-confetti` | ^2.3.2 | Animación de confeti |
| `@sveltejs/svelte-virtual-list` | ^3.0.1 | Listas virtualizadas |
| `panzoom` | ^9.4.3 | Pan/zoom genérico |
| `fuse.js` | ^7.0.0 | Búsqueda fuzzy |
| `dayjs` | ^1.11.10 | Fechas |

### 2.6 Comunicación / red

| Librería | Uso |
|---|---|
| `socket.io-client` ^4.2.0 | WebSockets (chat en vivo, presence, channels) |
| `eventsource-parser` ^1.1.2 | Parser de SSE para streaming de LLM |
| `undici` ^7.3.0 | HTTP client |

### 2.7 Internacionalización

| Librería | Versión |
|---|---|
| `i18next` | ^23.10.0 |
| `i18next-browser-languagedetector` | ^7.2.0 |
| `i18next-resources-to-backend` | ^1.2.0 |
| `i18next-parser` (dev) | ^9.0.1 |

**Locales soportadas:** 61 idiomas en `src/lib/i18n/locales/` (ar, bg-BG, bn-BD, bs-BA, ca-ES, cs-CZ, da-DK, de-DE, el-GR, en-GB, en-US, es-ES, et-EE, eu-ES, fa-IR, fi-FI, fr-CA, fr-FR, he-IL, hi-IN, hr-HR, hu-HU, id-ID, it-IT, ja-JP, ka-GE, ko-KR, lt-LT, ms-MY, nb-NO, ne-NP, nl-NL, pa-IN, pl-PL, pt-BR, pt-PT, ro-RO, ru-RU, sk-SK, sr-RS, sv-SE, ta-IN, th-TH, tk-TW, tr-TR, uk-UA, ur-PK, vi-VN, zh-CN, zh-TW, etc.).

### 2.8 Storage local

| Librería | Uso |
|---|---|
| `idb` ^7.1.1 | IndexedDB wrapper (chats locales, archivos) |
| `localStorage` | Settings, sidebar width, theme, token |

### 2.9 Auth / cripto / utilidades

| Librería | Uso |
|---|---|
| `@azure/msal-browser` ^4.5.0 | Microsoft auth (OAuth) |
| `js-sha256` ^0.10.1 | SHA256 hashing |
| `crc-32` ^1.2.2 | Checksums |
| `uuid` ^9.0.1 | UUID v4 |
| `jszip` ^3.10.1 | Manipulación ZIP |
| `file-saver` ^2.0.5 | Descarga de archivos |
| `heic2any` ^0.0.4 | Conversión HEIC → JPG/PNG |
| `html-entities` ^2.5.3 | Decodificación HTML |
| `turndown` + `turndown-plugin-gfm` + `@joplin/turndown-plugin-gfm` | HTML → Markdown |

### 2.10 Modelos en navegador (cliente-side AI)

| Librería | Uso |
|---|---|
| `@huggingface/transformers` ^3.0.0 | Modelos transformer en el navegador (embeddings, ASR, etc.) |
| `kokoro-js` ^1.1.1 | TTS en navegador |
| `@mediapipe/tasks-vision` ^0.10.17 | Visión computacional (face detection en CallOverlay) |

### 2.11 Tipografías

Cargadas en `src/app.css` vía `@font-face`:

| Familia | Archivo | Uso |
|---|---|---|
| **Inter** | `Inter-Variable.ttf` | Cuerpo (default) |
| **Archivo** | `Archivo-Variable.ttf` | Headings (`.font-primary`) |
| **Mona Sans** | `Mona-Sans.woff2` | Branding |
| **Instrument Serif** | `InstrumentSerif-Regular.ttf` | Decorativa (`.font-secondary`) |
| **Vazirmatn** | `Vazirmatn-Variable.ttf` | Soporte RTL (árabe, persa, etc.) |
| **JetBrainsMono** | (usado en CSS) | Code blocks |

**Stack font del sistema** (definido en `tailwind.css`):
```css
-apple-system, BlinkMacSystemFont, 'Inter', 'Vazirmatn', ui-sans-serif,
system-ui, 'Segoe UI', Roboto, Ubuntu, Cantarell, 'Noto Sans', sans-serif,
'Helvetica Neue', Arial, 'Apple Color Emoji', 'Segoe UI Emoji',
'Segoe UI Symbol', 'Noto Color Emoji'
```

---

## 3. Sistema de diseño

### 3.1 Paleta de colores

**Modo:** Dark mode controlado por clase (`darkMode: 'class'` en `tailwind.config.js`).

**Grays personalizados** (en `tailwind.css`, formato OKLCH):

| Token | Valor OKLCH | Uso |
|---|---|---|
| `gray-50` | `oklch(0.98 0 0)` | Fondos claros sutiles |
| `gray-100` | `oklch(0.94 0 0)` | Bordes light |
| `gray-200` | `oklch(0.92 0 0)` | Default border |
| `gray-300` | `oklch(0.85 0 0)` | Inputs idle |
| `gray-400` | `oklch(0.77 0 0)` | Placeholders |
| `gray-500` | `oklch(0.69 0 0)` | Texto muted |
| `gray-600` | `oklch(0.51 0 0)` | Texto secundario |
| `gray-700` | `oklch(0.42 0 0)` | Hover dark elements |
| `gray-800` | `oklch(0.32 0 0)` | Surface dark |
| `gray-850` | `oklch(0.27 0 0)` | Surface dark más oscuro |
| `gray-900` | `oklch(0.20 0 0)` | Background dark elevado |
| `gray-950` | `oklch(0.16 0 0)` | Background dark base |

**Colores de fondo de body:**
- Light: `#fff` con texto `#000`
- Dark: `#171717` con texto `#eee`

**Acento:** `sky` (Tailwind default) para mentions/suggestions:
```css
.mention { @apply text-sky-800 dark:text-sky-200 bg-sky-300/15 dark:bg-sky-500/15; }
```

**Estado checkbox checked:** `blue-600` con focus ring `blue-500`.

### 3.2 Tipografía

| Clase | Familia | Uso |
|---|---|---|
| (default) | Inter / Vazirmatn | Cuerpo de la app |
| `.font-primary` | Archivo, Vazirmatn | Headings, branding |
| `.font-secondary` | InstrumentSerif | Decorativa |
| `.font-mono` | JetBrainsMono | Code blocks |

**Escalado dinámico de UI** (custom):
```css
:root { --app-text-scale: 1; }
html { font-size: calc(1rem * var(--app-text-scale, 1)); }
```
Controlado por slider en `Settings → Interface`. También escala items del sidebar (`#sidebar-chat-item`).

**Plugin tipografía Tailwind** con presets:
- `.input-prose` / `.input-prose-sm` — para inputs ricos
- `.markdown-prose` / `.markdown-prose-sm` / `.markdown-prose-xs` — para mensajes renderizados

### 3.3 Espaciado y dimensiones

| Token | Valor |
|---|---|
| Sidebar default | **260px** |
| Sidebar mínimo | **220px** |
| Sidebar máximo | **480px** |
| `--sidebar-width` | Variable CSS dinámica |
| `--app-text-scale` | Variable CSS para scaling de UI |
| `padding.safe-bottom` | `env(safe-area-inset-bottom)` (iOS notch) |
| Border radius scrollbar | `9999px` (pill) |
| Scrollbar size | `0.45rem` (h/w) |

**Tamaños de modal** (en `common/Modal.svelte`): `xs`, `sm`, `md`, `lg`, `xl`, `2xl`, `3xl`.

### 3.4 Iconografía

**Sistema:** Custom SVG components en `src/lib/components/icons/` (**176 iconos**).

**Estilo:** Heroicons-inspired (24×24, stroke `1.5`, line-cap/join `round`, color `currentColor`).

**Plantilla estándar** (todos los iconos siguen este formato):
```svelte
<script lang="ts">
    export let className = 'size-4';
    export let strokeWidth = '1.5';
</script>

<svg
    aria-hidden="true"
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke-width={strokeWidth}
    stroke="currentColor"
    class={className}
>
    <path stroke-linecap="round" stroke-linejoin="round" d="..." />
</svg>
```

**Categorías de iconos** (~176 archivos):

- **Navegación/flechas:** ArrowLeft, ArrowRight, ArrowUpCircle, ArrowDownTray, ArrowUpTray, ArrowPath, ArrowUturnLeft/Right, ArrowsPointingOut, ChevronDown/Up/Left/Right, ChevronUpDown, ArrowUpLeft, ArrowTurnDownRight
- **Acciones:** Plus, PlusSmall, Minus, XMark, Check, CheckCircle, CheckBox, Trash, Pencil, PencilSolid, Copy, Share, Download, Upload, Save, Refresh, Reload, Edit, Eye, EyeSlash
- **Chat:** ChatBubble, ChatBubbleOval, ChatBubbleDotted, ChatBubbleDottedChecked, ChatBubbles, ChatCheck, ChatPlus
- **Multimedia:** Camera, CameraSolid, Microphone, MicrophoneSolid, Speaker, SpeakerWave, Music, Photo, PhotoSolid, Image, Film, VideoCamera, Headphones
- **Archivos:** Document, DocumentText, Folder, FolderOpen, FolderPlus, File, FileItem, ArchiveBox, ClipboardCheck, ClipboardDocumentList
- **Sistema:** Cog6, Cog8, AdjustmentsHorizontal, AdjustmentsHorizontalOutline, Wrench, Bolt, Lightning, Server, Database, Code, CodeBracket, CommandLine, Terminal
- **Usuario/social:** User, UserCircle, UserPlus, UserGroup, Users, Avatar, Identification, Shield, ShieldCheck
- **Estados:** Spinner, Loader, Heart, HeartFilled, Star, StarFilled, Bookmark, BookmarkSlash, Bell, BellOff, AppNotification
- **UI:** Bars3BottomLeft, BarsArrowUp, Sidebar, Window, Squares2x2, RectangleStack, ViewColumns
- **Texto/formato:** Bold, Italic, Underline, Strikethrough, ListBullet, ListOrdered, Heading, Quote, Link, Hashtag, Mention
- **Otros:** Sparkles (AI), Sun, Moon, Map, Globe, GlobeAlt, Compass, Search, MagnifyingGlass, Filter, Funnel, Tag, Calendar, CalendarSolid, Clock, Bell, Lock, Unlock, Key, BookOpen, Beaker, Puzzle, Cube, Gift, Trophy, ChartBar, ChartPie, Pin, Brain, Flag, Megaphone, Crown, Robot, Rocket, Lego

**Sizing convention:** Las clases utilitarias `size-3`, `size-3.5`, `size-4`, `size-5`, `size-6`, `size-8` (Tailwind) controlan dimensiones.

---

## 4. Estructura de rutas (SvelteKit)

```
src/routes/
├── +layout.svelte                    # Root: i18n provider, theme setup
├── +error.svelte                     # Error boundary global
│
├── (app)/                            # Layout autenticado principal
│   ├── +layout.svelte                # App shell: Sidebar + content
│   ├── +page.svelte                  # Home / nuevo chat
│   │
│   ├── c/[id]/+page.svelte           # Chat por ID
│   │
│   ├── channels/[id]/+page.svelte    # Chat de canal
│   │
│   ├── home/                         # Home section
│   │   ├── +layout.svelte
│   │   └── +page.svelte
│   │
│   ├── notes/                        # Sistema de notas
│   │   ├── +layout.svelte
│   │   ├── +page.svelte              # Lista
│   │   ├── new/+page.svelte          # Nueva
│   │   └── [id]/+page.svelte         # Editar
│   │
│   ├── playground/                   # Pruebas de API
│   │   ├── +layout.svelte
│   │   ├── +page.svelte
│   │   ├── completions/+page.svelte
│   │   └── images/+page.svelte
│   │
│   ├── workspace/                    # Personalización del usuario
│   │   ├── +layout.svelte
│   │   ├── +page.svelte
│   │   ├── knowledge/                # Bases de conocimiento RAG
│   │   │   ├── +page.svelte
│   │   │   ├── create/+page.svelte
│   │   │   └── [id]/+page.svelte
│   │   ├── models/                   # Modelos personalizados
│   │   │   ├── +page.svelte
│   │   │   ├── create/+page.svelte
│   │   │   └── edit/+page.svelte
│   │   ├── prompts/                  # Plantillas de prompts
│   │   │   ├── +page.svelte
│   │   │   ├── create/+page.svelte
│   │   │   └── [id]/+page.svelte
│   │   ├── skills/                   # Skills (ej. Claude-style)
│   │   │   ├── +page.svelte
│   │   │   ├── create/+page.svelte
│   │   │   └── edit/+page.svelte
│   │   └── tools/                    # Herramientas / functions
│   │       ├── +page.svelte
│   │       ├── create/+page.svelte
│   │       └── edit/+page.svelte
│   │
│   └── admin/                        # Panel admin (rol admin)
│       ├── +page.svelte
│       ├── analytics/
│       │   ├── +page.svelte
│       │   └── [tab]/+page.svelte
│       ├── evaluations/
│       │   ├── +page.svelte
│       │   └── [tab]/+page.svelte
│       ├── functions/
│       │   ├── +page.svelte
│       │   ├── create/+page.svelte
│       │   └── edit/+page.svelte
│       ├── settings/
│       │   ├── +page.svelte
│       │   └── [tab]/+page.svelte
│       └── users/
│           ├── +page.svelte
│           └── [tab]/+page.svelte
│
├── auth/                             # Login / signup
│   └── +page.svelte
│
├── error/+page.svelte                # Página de error
├── s/[id]/+page.svelte               # Chat compartido público (read-only)
└── watch/+page.svelte                # Modo "watch" (demo full-screen)
```

---

## 5. Layout principal

### 5.1 Estructura del shell

```
┌────────────────────────────────────────────────────────────────┐
│                     APP SHELL (+layout.svelte)                  │
├──────────────────┬─────────────────────────────────────────────┤
│                  │           Navbar (10.2 KB)                  │
│                  │  ┌────────────────────────────────────────┐ │
│                  │  │ Banner (cerrable, opcional)            │ │
│                  │  ├────────────────────────────────────────┤ │
│   SIDEBAR        │  │ Model Selector ▼   │ Title  │ ⚙ Share  │ │
│   260px          │  └────────────────────────────────────────┘ │
│   (resizable     │                                              │
│    220-480px)    │           CONTENT AREA                       │
│                  │      (Chat / Notes / Workspace /             │
│   - Header       │       Admin / Playground / Channels)        │
│   - Pinned       │                                              │
│   - Channels     │                                              │
│   - Search       │                                              │
│   - Folders      │                                              │
│   - Chat list    │                                              │
│   - Footer       │                                              │
│     (UserMenu)   │                                              │
│                  │                                              │
└──────────────────┴─────────────────────────────────────────────┘
```

### 5.2 Sidebar (`src/lib/components/layout/Sidebar.svelte` — 41.4 KB)

**Dimensiones:**
- Default: **260px**
- Mínimo: **220px**
- Máximo: **480px**
- Resize: drag en el borde derecho
- Persistencia: `localStorage.sidebarWidth`
- Mobile: oculto, controlado por store `showSidebar`
- Variable CSS: `--sidebar-width`

**Estructura interna:**

```
Sidebar Container
│
├── Header (sticky top)
│   ├── Home icon + "Open WebUI" (clickable → /)
│   ├── Search button (abre SearchModal)
│   └── New chat button
│
├── Pinned Models Section (PinnedModelList.svelte)
│   └── PinnedModelItem.svelte × N
│
├── Channels Section (si habilitado)
│   ├── ChannelItem.svelte × N
│   └── + New Channel
│
├── Main Chat List (scrollable, paginado)
│   ├── SearchInput.svelte (búsqueda chats con FuseJS)
│   ├── Folders (Folders.svelte → RecursiveFolder.svelte)
│   │   └── Carpetas anidadas con drag & drop
│   └── ChatItem.svelte × N
│       ├── Title (editable inline)
│       ├── Hover menu (ChatMenu.svelte)
│       ├── Drag-to-reorder
│       └── Pin / Archive / Delete / Move
│
└── Footer
    └── UserMenu.svelte
        ├── Avatar + Name
        ├── User status (UserStatusModal.svelte)
        ├── Settings → SettingsModal
        └── Sign out
```

**Subcomponentes** (`layout/Sidebar/`):

| Archivo | Tamaño | Descripción |
|---|---|---|
| `ChatItem.svelte` | 15.2 KB | Item individual de chat |
| `ChatMenu.svelte` | 13.5 KB | Context menu del chat |
| `ChannelItem.svelte` | 6.9 KB | Item de canal |
| `ChannelModal.svelte` | 8.8 KB | Crear/editar canal |
| `UserMenu.svelte` | 11.9 KB | Menú de usuario |
| `SearchInput.svelte` | 9.5 KB | Búsqueda en sidebar |
| `Folders.svelte` | 1.4 KB | Wrapper de carpetas |
| `RecursiveFolder.svelte` | 17.7 KB | Renderer recursivo |
| `PinnedModelList.svelte` | 3.2 KB | Lista modelos pinned |
| `PinnedModelItem.svelte` | 2.0 KB | Item modelo pinned |
| `UserStatusModal.svelte` | 4.2 KB | Selector de estado |

**Layout dinámico del sidebar item:**
```css
#sidebar-chat-item {
    min-height: calc(32px * var(--app-text-scale, 1));
    padding-inline: calc(11px * var(--app-text-scale, 1));
    padding-block: calc(6px * var(--app-text-scale, 1));
}
```

---

## 6. Interfaz de chat

**Archivo principal:** `src/lib/components/chat/Chat.svelte` (81.9 KB)

### 6.1 Estructura del chat

```
Chat Container (PaneGroup — paneforge, redimensionable)
│
├── Pane: Main Chat
│   ├── Navbar.svelte (10.2 KB)
│   │   ├── Banner (Banner.svelte cerrable)
│   │   ├── Model Selector ▼ (ModelSelector.svelte)
│   │   ├── Chat title (editable)
│   │   ├── Sidebar toggle (mobile)
│   │   ├── Settings icon → SettingsModal
│   │   ├── Share icon → ShareChatModal
│   │   └── Menu (archive, move, delete, tags)
│   │
│   ├── Messages.svelte (13.9 KB)
│   │   ├── Auto-scroll inteligente (sticky bottom)
│   │   ├── Skeleton loading (Skeleton.svelte)
│   │   ├── Empty state (ChatPlaceholder.svelte → Suggestions.svelte)
│   │   ├── Message × N
│   │   │   ├── UserMessage.svelte (21.5 KB)
│   │   │   │   ├── Avatar + nombre
│   │   │   │   ├── Attachments (FileItem.svelte)
│   │   │   │   ├── Contenido (markdown / texto)
│   │   │   │   ├── Edit / Delete / Copy
│   │   │   │   └── Regenerate
│   │   │   │
│   │   │   └── ResponseMessage.svelte (47.3 KB)
│   │   │       ├── Avatar / nombre del modelo
│   │   │       ├── ContentRenderer.svelte
│   │   │       │   ├── Markdown.svelte
│   │   │       │   ├── CodeBlock.svelte (16.5 KB)
│   │   │       │   │   ├── Syntax highlight (highlight.js)
│   │   │       │   │   ├── Mermaid render
│   │   │       │   │   ├── Vega-Lite render
│   │   │       │   │   ├── Pyodide run
│   │   │       │   │   └── Copy / Run / Save
│   │   │       │   ├── Citations.svelte
│   │   │       │   ├── KatexRenderer.svelte
│   │   │       │   └── HTMLToken.svelte (sanitized)
│   │   │       ├── WebSearchResults.svelte
│   │   │       ├── Follow-ups
│   │   │       ├── RateComment.svelte (👍/👎)
│   │   │       ├── Status history (steps)
│   │   │       └── Copy / Regenerate / Continue
│   │   │
│   │   └── MultiResponseMessages.svelte (modelos en paralelo)
│   │
│   └── MessageInput.svelte (66.9 KB)
│       ├── RichTextInput.svelte (38.1 KB) ← Tiptap editor
│       │   ├── Mentions @model / @tool
│       │   ├── Slash commands
│       │   ├── Tables, lists, code blocks
│       │   └── Autocomplete
│       │
│       ├── Toolbar inferior
│       │   ├── # Attach files
│       │   ├── / Slash prompts (Commands/CommandSuggestionList)
│       │   ├── @ Mention (model/tool)
│       │   ├── 🎤 Voice recording (VoiceRecording.svelte)
│       │   ├── 📞 Voice call (CallOverlay.svelte)
│       │   ├── 🌐 Web search toggle
│       │   ├── 🛠 Tool servers (ToolServersModal)
│       │   ├── 💻 Terminal (TerminalMenu.svelte)
│       │   ├── 🔌 Integrations (IntegrationsMenu.svelte)
│       │   ├── ⚙ Valves (Valves.svelte)
│       │   └── Send/Stop button (Spinner durante stream)
│       │
│       ├── File attachments (FileItem.svelte horizontal scroll)
│       │
│       ├── Drag & drop overlay (FilesOverlay.svelte)
│       │
│       └── Modals
│           ├── AttachWebpageModal.svelte
│           └── InputVariablesModal.svelte
│
├── Pane: ChatControls (lateral derecho, opcional)
│   ├── ChatControls.svelte (15.8 KB)
│   │   ├── Temperature slider
│   │   ├── Top-p / Top-k
│   │   ├── System prompt
│   │   ├── Tools selector (checkboxes)
│   │   ├── Knowledge selector
│   │   └── JSON params avanzados
│   │
│   └── Artifacts.svelte (8.3 KB)
│       ├── Title
│       ├── Code / HTML preview
│       └── Copy / Download
│
└── Overlays globales
    ├── CallOverlay.svelte (26.7 KB) — voz/video full-screen
    ├── FileNav.svelte (47.7 KB) — explorador de archivos
    ├── PyodideFileNav.svelte
    ├── XTerminal.svelte
    ├── SearchModal.svelte
    ├── ShortcutsModal.svelte
    └── TagChatModal.svelte
```

### 6.2 Renderizado de Markdown

**Pipeline:** `marked` → `dompurify` → componentes Svelte custom.

**Carpeta:** `src/lib/components/chat/Messages/Markdown/`

| Archivo | Función |
|---|---|
| `Markdown.svelte` | Top-level parser |
| `MarkdownTokens.svelte` (14.9 KB) | Renderizado de tokens block-level |
| `MarkdownInlineTokens.svelte` (4.4 KB) | Renderizado inline |
| `KatexRenderer.svelte` | Math LaTeX (`$...$`, `$$...$$`) |
| `AlertRenderer.svelte` | Callouts/admonitions |
| `ConsecutiveDetailsGroup.svelte` | Grupo de `<details>` |
| `HTMLToken.svelte` | HTML raw sanitizado |
| `Source.svelte` / `SourceToken.svelte` | Citas con fuentes |
| `MarkdownInlineTokens/CodespanToken.svelte` | Inline code |
| `MarkdownInlineTokens/TextToken.svelte` | Text plano |
| `MarkdownInlineTokens/MentionToken.svelte` | Menciones |

**Features de markdown soportadas:**
- Tablas con exportación a CSV
- Bloques de código con syntax highlight (40+ lenguajes)
- LaTeX inline y display
- Callouts/Alerts (`> [!NOTE]`)
- Footnotes
- Citations con fuentes
- Mentions (`@`)
- Strikethrough
- HTML passthrough sanitizado
- Mermaid diagrams (rendered en CodeBlock)
- Vega-Lite charts (rendered en CodeBlock)

---

## 7. Inventario completo de componentes

**Total estimado:** ~400+ componentes Svelte distribuidos en:

### 7.1 `components/admin/` — Administración

- `Analytics.svelte` + `Analytics/Dashboard.svelte`, `ChartLine.svelte`, `ModelUsage.svelte`, `UserUsage.svelte`, `AnalyticsModelModal.svelte`
- `Evaluations.svelte` + `Feedbacks.svelte`, `FeedbackModal.svelte`, `Leaderboard.svelte`, `ModelActivityChart.svelte`
- `Functions.svelte` + `FunctionEditor.svelte`, `FunctionMenu.svelte`, `AddFunctionMenu.svelte`
- `Settings.svelte` + tabs:
  - `General.svelte`, `Models.svelte` (`ModelList`, `ModelMenu`, `ModelSelector`, `ManageModelsModal`)
  - `Connections.svelte` (`OllamaConnection`, `OpenAIConnection`)
  - `Audio.svelte`, `CodeExecution.svelte`, `Database.svelte`, `Documents.svelte`, `Images.svelte`
  - `Integrations.svelte`, `Interface.svelte` (+ `Banners.svelte`)
  - `WebSearch.svelte`, `Pipelines.svelte`
- `Users.svelte` + `Users/Groups/*` (modales de grupos)

### 7.2 `components/chat/` — Chat principal

Ver sección 6.1 para detalle completo.

### 7.3 `components/channel/` — Canales colaborativos

- `Channel.svelte` (9.9 KB)
- `ChannelInfoModal.svelte`
- `MessageInput.svelte` (32 KB, variante para canales)
- `Messages.svelte`
- `Navbar.svelte`
- `PinnedMessagesModal.svelte`
- `Thread.svelte`
- `WebhooksModal.svelte`, `WebhookItem.svelte`

### 7.4 `components/common/` — UI reutilizable (44 archivos)

**Modales y overlays:**
- `Modal.svelte` (3.4 KB) — base con focus trap, sizes `xs|sm|md|lg|xl|2xl|3xl`
- `Drawer.svelte` (2.1 KB) — drawer lateral
- `Overlay.svelte` — backdrop
- `ConfirmDialog.svelte` (5.1 KB)

**Inputs y forms:**
- `Checkbox.svelte` (1.8 KB) — custom con SVG checkmark inline
- `Select.svelte` (3.3 KB)
- `Selector.svelte` (2.7 KB)
- `Switch.svelte` — toggle
- `Dropdown.svelte` (4.7 KB), `DropdownSub.svelte` (3.9 KB), `DropdownOptions.svelte`
- `InputModal.svelte`
- `SensitiveInput.svelte` — password con `-webkit-text-security: disc`
- `Textarea.svelte`

**Rich text:**
- `RichTextInput.svelte` (38.1 KB) — Tiptap editor con extensiones
- `RichTextInput/` — extensiones custom

**File handling:**
- `FileItem.svelte` (5.8 KB) — card de archivo
- `FileItemModal.svelte` (21.8 KB) — preview/details
- `AddFilesPlaceholder.svelte` — drop zone

**Display:**
- `Banner.svelte` (4.3 KB) — info banner cerrable
- `Badge.svelte`
- `ChatList.svelte` (3.5 KB)
- `Pagination.svelte` (2.1 KB)
- `Collapsible.svelte` (4.5 KB)
- `Tags.svelte` + `Tags/`
- `Valves.svelte` + `Valves/`

**Multimedia:**
- `Image.svelte` (1.4 KB)
- `ImagePreview.svelte` (5.4 KB)
- `PDFViewer.svelte` (7.6 KB) — pdfjs
- `FullHeightIframe.svelte` (5.9 KB)
- `SlideShow.svelte` (1.1 KB)
- `Emoji.svelte` (0.4 KB), `EmojiPicker.svelte` (5.1 KB)

**Code & editing:**
- `CodeEditor.svelte` (8.1 KB) — CodeMirror
- `CodeEditorModal.svelte` (1.6 KB)
- `SVGPanZoom.svelte` (3.3 KB)

**Misc:**
- `Tooltip.svelte` (2.7 KB) — Tippy.js wrapper
- `HotkeyHint.svelte` (0.9 KB)
- `Spinner.svelte`, `Loader.svelte` (1.0 KB)
- `Folder.svelte` (5.4 KB)
- `Marquee.svelte` (0.5 KB)
- `DragGhost.svelte` (0.9 KB)
- `ToolCallDisplay.svelte`
- `Sidebar.svelte` (variante genérica)

### 7.5 `components/layout/`

- `Sidebar.svelte` (41.4 KB) — sidebar principal (ya descrito)
- `Navbar/Menu.svelte` (14.4 KB)
- `Navbar/Overlay/`
- `ArchivedChatsModal.svelte`
- `ChatsModal.svelte` (17.4 KB)
- `FilesModal.svelte` (10.9 KB)
- `SharedChatsModal.svelte`
- `SearchModal.svelte` (12.3 KB)
- `UpdateInfoToast.svelte`
- `Overlay/AccountPending.svelte`

### 7.6 `components/notes/`

- `NoteEditor.svelte` (40.5 KB) — editor enriquecido (Tiptap)
- `Notes.svelte` (19.8 KB)
- `NotePanel.svelte` (2.6 KB)
- `AIMenu.svelte` (1.5 KB)
- `RecordMenu.svelte` (2.0 KB)
- Subcarpetas `NoteEditor/`, `Notes/`

### 7.7 `components/playground/`

- `Chat.svelte` (13.9 KB)
- `Completions.svelte` (4.8 KB)
- `Images.svelte` (8.3 KB)

### 7.8 `components/workspace/`

- `Knowledge.svelte` (10.2 KB) + `Knowledge/KnowledgeBase.svelte` (29.9 KB)
- `Models.svelte` (24.5 KB) + `Models/ModelEditor.svelte` (26.0 KB)
- `Prompts.svelte` (15.8 KB)
- `Skills.svelte` (16.2 KB)
- `Tools.svelte` (20.6 KB) + `Tools/ToolkitEditor.svelte` (10.6 KB)

### 7.9 `components/app/` — Electron

- `AppSidebar.svelte` (1.8 KB)

### 7.10 Top-level modals

- `OnBoarding.svelte` (3.0 KB) — wizard inicial
- `ChangelogModal.svelte` (3.5 KB)
- `ImportModal.svelte` (3.2 KB)
- `AddConnectionModal.svelte` (22.0 KB)
- `AddTerminalServerModal.svelte` (26.0 KB)
- `AddToolServerModal.svelte` (30.5 KB)
- `NotificationToast.svelte` (2.8 KB)

---

## 8. Stores globales (Svelte stores)

**Archivo:** `src/lib/stores/index.ts`

### 8.1 Configuración / sistema

| Store | Tipo | Descripción |
|---|---|---|
| `WEBUI_NAME` | `Writable<string>` | Nombre de la app |
| `WEBUI_VERSION` | `Writable<string>` | Versión |
| `WEBUI_DEPLOYMENT_ID` | `Writable<string>` | ID deploy |
| `config` | `Writable<Config>` | Config completa del backend |
| `user` | `Writable<SessionUser>` | Usuario actual |
| `theme` | `Writable<'light'\|'dark'\|'system'>` | Tema |
| `mobile` | `Writable<boolean>` | Detección mobile |
| `socket` | `Writable<Socket>` | Conexión Socket.IO |

### 8.2 Electron app

| Store | Descripción |
|---|---|
| `isApp` | Si está en Electron |
| `appInfo`, `appData` | Info de la app |

### 8.3 Chat

| Store | Descripción |
|---|---|
| `chatId` | ID del chat actual |
| `chatTitle` | Título |
| `chats` | Lista de chats |
| `pinnedChats` | Pinned |
| `tags`, `folders` | Tags y carpetas |
| `selectedFolder` | Carpeta activa |
| `currentChatPage` | Paginación del sidebar |
| `temporaryChatEnabled` | Modo temporal (no guarda) |
| `scrollPaginationEnabled` | Toggle paginación scroll |
| `chatRequestQueues` | Cola de prompts pendientes |

### 8.4 Channels (canales colaborativos)

| Store | Descripción |
|---|---|
| `channels` | Lista de canales |
| `channelId` | Canal activo |
| `activeUserIds` | Usuarios online en canales |
| `activeChatIds` | Chats activos |

### 8.5 Modelos / herramientas

| Store | Descripción |
|---|---|
| `models` | Lista de modelos disponibles |
| `MODEL_DOWNLOAD_POOL` | Estado de descargas |
| `knowledge` | Bases de conocimiento |
| `tools`, `skills`, `functions` | Listas |
| `toolServers`, `terminalServers` | Servidores |
| `pyodideWorker` | Worker Pyodide persistente |
| `TTSWorker` | Worker TTS |
| `audioQueue` | Cola de audio |

### 8.6 UI / overlays

| Store | Descripción |
|---|---|
| `sidebarWidth` | Ancho actual (default 260) |
| `showSidebar` | Visibilidad |
| `showSearch` | SearchModal |
| `showSettings` | SettingsModal |
| `showShortcuts` | ShortcutsModal |
| `showArchivedChats` | ArchivedChatsModal |
| `showChangelog` | ChangelogModal |
| `showControls` | ChatControls panel |
| `showEmbeds` | Embeds panel |
| `showOverview` | Overview panel |
| `showArtifacts` | Artifacts panel |
| `showCallOverlay` | CallOverlay (voz/video) |
| `showFileNav` | FileNav panel |
| `showFileNavPath`, `showFileNavDir` | Path/dir del FileNav |
| `selectedTerminalId` | Terminal activo |
| `artifactCode`, `artifactContents` | Contenido del artifact |
| `embed` | Embed activo |
| `banners` | Lista de banners |
| `settings` | Settings del usuario |
| `isLastActiveTab` | Tab activo |
| `playingNotificationSound` | Sonido sonando |
| `USAGE_POOL` | Tokens en uso |
| `shortCodesToEmojis` | Mapa emoji |

---

## 9. Sistema de APIs (frontend → backend)

**Carpeta:** `src/lib/apis/`

| Subcarpeta | Endpoint backend | Función |
|---|---|---|
| `analytics/` | `/api/v1/analytics` | Métricas y estadísticas |
| `audio/` | `/api/v1/audio` | TTS / STT |
| `auths/` | `/api/v1/auths` | Login, signup, OAuth |
| `channels/` | `/api/v1/channels` | Canales colaborativos |
| `chats/` | `/api/v1/chats` | CRUD chats |
| `configs/` | `/api/v1/configs` | Config del sistema |
| `evaluations/` | `/api/v1/evaluations` | Feedback y leaderboard |
| `files/` | `/api/v1/files` | Upload y gestión |
| `folders/` | `/api/v1/folders` | Carpetas de chats |
| `functions/` | `/api/v1/functions` | Functions admin |
| `groups/` | `/api/v1/groups` | Grupos de usuarios |
| `images/` | `/api/v1/images` | Generación de imágenes |
| `knowledge/` | `/api/v1/knowledge` | Bases de conocimiento (RAG) |
| `memories/` | `/api/v1/memories` | Memoria persistente |
| `models/` | `/api/v1/models` | Modelos custom |
| `notes/` | `/api/v1/notes` | Notas |
| `ollama/` | `/ollama` | Backend Ollama |
| `openai/` | `/openai` | Backend OpenAI |
| `prompts/` | `/api/v1/prompts` | Plantillas de prompts |
| `retrieval/` | `/api/v1/retrieval` | RAG / búsqueda |
| `skills/` | `/api/v1/skills` | Skills |
| `streaming/` | SSE | Streaming de respuestas |
| `tasks/` | `/api/v1/tasks` | Tareas asíncronas |
| `terminal/` | `/api/v1/terminal` | Terminales remotos |
| `tools/` | `/api/v1/tools` | Tools |
| `users/` | `/api/v1/users` | Gestión de usuarios |
| `utils/` | helpers | |

**URLs base** (`src/lib/constants.ts`):
```typescript
WEBUI_BASE_URL       = '' (prod) / 'http://localhost:8080' (dev)
WEBUI_API_BASE_URL   = '${WEBUI_BASE_URL}/api/v1'
OLLAMA_API_BASE_URL  = '${WEBUI_BASE_URL}/ollama'
OPENAI_API_BASE_URL  = '${WEBUI_BASE_URL}/openai'
AUDIO_API_BASE_URL   = '${WEBUI_BASE_URL}/api/v1/audio'
IMAGES_API_BASE_URL  = '${WEBUI_BASE_URL}/api/v1/images'
RETRIEVAL_API_BASE_URL = '${WEBUI_BASE_URL}/api/v1/retrieval'
```

---

## 10. Animaciones y efectos visuales

### 10.1 Keyframes definidos en `app.css`

**Shimmer (text loading):**
```css
@keyframes shimmer {
    0% { background-position: 100% 0; }
    100% { background-position: -100% 0; }
}
.shimmer {
    background: linear-gradient(110deg, #b4b4b4 0%, #b4b4b4 43%, #e8e8e8 50%, #b4b4b4 57%, #b4b4b4 100%);
    background-size: 200% 100%;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 1.5s cubic-bezier(0.7, 0, 1, 0.4) infinite;
    color: #b4b4b4;
}
/* Dark mode variant */
:global(.dark) .shimmer {
    background: linear-gradient(110deg, #9a9a9a 0%, #9a9a9a 43%, #5e5e5e 50%, #9a9a9a 57%, #9a9a9a 100%);
    /* ... */
}
```
Uso: feedback "thinking" en respuestas.

**Smooth fade-in:**
```css
@keyframes smoothFadeIn {
    0%   { opacity: 0; transform: translateY(-10px); }
    100% { opacity: 1; transform: translateY(0); }
}
.status-description { animation: smoothFadeIn 0.2s forwards; }
```

### 10.2 Transiciones Svelte

**Carpeta:** `src/lib/utils/transitions/`

Transiciones custom (slide, fade, scale) usadas en modales, drawers, dropdowns.

### 10.3 Scrollbars

**Custom styling** (Webkit-only):
```css
::-webkit-scrollbar       { width: 0.45rem; height: 0.45rem; }
::-webkit-scrollbar-thumb { background: rgba(215,215,215,0.6); border-radius: 9999px; }
.dark ::-webkit-scrollbar-thumb { background: rgba(67,67,67,0.6); }
```

**Variantes:**
- `.scrollbar-hidden` — visible solo on hover/focus
- `.scrollbar-none` — completamente oculto

### 10.4 Otros efectos

- **Drag region (Electron):** `.drag-region` y `.no-drag-region` (`-webkit-app-region`)
- **Confeti:** `svelte-confetti` para celebraciones (onboarding completo)
- **Toasts:** `svelte-sonner` (notificaciones flotantes)
- **Tippy themes:** `tippy-box[data-theme~='dark']` con `bg-gray-950 text-xs border border-gray-900 shadow-xl rounded-lg`
- **Mention pills:** `text-sky-800/200 bg-sky-300/15 dark:bg-sky-500/15` con `border-radius: 0.4rem`
- **AI autocompletion ghost text:** `.ai-autocompletion::after { color: #a0a0a0; content: attr(data-suggestion); }`

### 10.5 Iconografía animada

- **Spinner:** `Spinner.svelte` con animación CSS `animate-spin`
- **Loader:** `Loader.svelte` (variante alternativa)
- **Marquee:** `Marquee.svelte` para texto en scroll continuo

---

## 11. Internacionalización (i18n)

**Sistema:** `i18next` con detección automática del navegador.

**Locales disponibles** (61 en `src/lib/i18n/locales/`):
- ar, ar-BH, az-AZ, bg-BG, bn-BD, bo-TB, bs-BA, ca-ES, ceb-PH, cs-CZ
- da-DK, de-DE, dg-DG, el-GR, en-GB, en-US, es-ES, et-EE, eu-ES, fa-IR
- fi-FI, fr-CA, fr-FR, he-IL, hi-IN, hr-HR, hu-HU, id-ID, ie-GA, it-IT
- ja-JP, ka-GE, ko-KR, lt-LT, ms-MY, my-MM, nb-NO, ne-NP, nl-NL, pa-IN
- pl-PL, pt-BR, pt-PT, ro-RO, ru-RU, sk-SK, sr-RS, sv-SE, ta-IN, te-IN
- th-TH, ti-ER, tk-TW, tl-PH, tr-TR, uk-UA, ur-PK, vi-VN, yue-Hant, zh-CN, zh-TW

**Configuración:**
- Parser: `i18next-parser` con `i18next-parser.config.ts`
- Source plug: `i18next-resources-to-backend` (carga lazy de JSON)
- Detector: `i18next-browser-languagedetector` (querystring → cookie → localStorage → navigator)
- Soporte RTL nativo (árabe, hebreo, persa) vía font Vazirmatn
- `direction: 'auto'` en placeholders de inputs

---

## 12. Utilidades (`src/lib/utils/`)

| Archivo | Función |
|---|---|
| `index.ts` | Helpers generales (debounce, throttle, format, etc.) |
| `audio.ts` | Audio playback queue, recording |
| `characters/` | Avatares y character cards |
| `codeHighlight.ts` | Syntax highlighting wrapper |
| `codemirror.ts` | CodeMirror config |
| `connections.ts` | Conexiones a backends |
| `excelToTable.ts` | Excel → markdown table |
| `google-drive-picker.ts` | Google Drive file picker |
| `marked/` | Custom marked extensions |
| `onedrive-file-picker.ts` | OneDrive file picker |
| `pptxToHtml.ts` | PowerPoint → HTML |
| `text-scale.ts` | Control de `--app-text-scale` |
| `transitions/` | Transiciones Svelte custom |

---

## 13. Características destacadas

### 13.1 Llamada de voz/video (CallOverlay)

**Archivo:** `src/lib/components/chat/MessageInput/CallOverlay.svelte` (26.7 KB)

- Audio en tiempo real (Whisper STT + TTS)
- Video cámara opcional (MediaPipe Tasks Vision para face detection)
- Visualización RMS del micrófono
- Transcripción en vivo
- Controles: mute, cámara on/off, hang up
- Subcomponente: `CallOverlay/VideoInputMenu.svelte`

### 13.2 Ejecución de código (Pyodide)

- Pyodide worker persistente (`pyodideWorker` store)
- File system virtual (`PyodideFileNav.svelte`)
- Ejecución desde code blocks markdown
- Integración con `XTerminal.svelte` (xterm.js)

### 13.3 Artifacts

- `Artifacts.svelte` (8.3 KB) — pane lateral con preview
- HTML/SVG/code preview en vivo
- Iframe sandboxed para HTML
- Copy/download

### 13.4 Knowledge bases (RAG)

- `workspace/knowledge/` con CRUD completo
- `Knowledge/KnowledgeBase.svelte` (29.9 KB) — gestión documentos
- Upload de múltiples archivos
- Vinculación a modelos (system prompt augmentation)

### 13.5 Tool servers / functions

- `AddToolServerModal.svelte` (30.5 KB)
- `AddTerminalServerModal.svelte` (26.0 KB)
- Editor de funciones con CodeMirror (Python)
- Valves (parámetros configurables por tool)

### 13.6 Drag & drop global

- Archivos al input (FilesOverlay.svelte)
- Chats al sidebar (folders, reorder)
- Mensajes (RecursiveFolder.svelte handlers)
- `DragGhost.svelte` para preview visual

### 13.7 Edición colaborativa

- `yjs` + `y-prosemirror` en notas y canales
- Cursores remotos con nombres de usuario
- Estilo cursor: `border-color: orange; bg-color: rgb(250,129,0)`

---

## 14. Atajos de teclado

**Archivo:** `src/lib/shortcuts.ts`

Modal para mostrarlos: `ShortcutsModal.svelte` (`Ctrl/Cmd + /`)

Ejemplos típicos:
- `Ctrl/Cmd + Shift + O` — Nuevo chat
- `Ctrl/Cmd + Shift + ;` — Copiar último code block
- `Ctrl/Cmd + Shift + S` — Toggle sidebar
- `Ctrl/Cmd + K` — Buscar
- `Ctrl/Cmd + ,` — Settings
- `Ctrl/Cmd + Enter` — Enviar mensaje
- `Esc` — Cerrar modal

`HotkeyHint.svelte` muestra el atajo dentro de tooltips/menús.

---

## 15. Tipos de archivo soportados

**Definidos en `src/lib/constants.ts`:**

**MIME types:**
```
application/epub+zip, application/pdf, text/plain, text/csv, text/xml,
text/html, text/x-python, text/css, text/markdown,
application/vnd.openxmlformats-officedocument.wordprocessingml.document,
application/octet-stream, application/x-javascript,
audio/mpeg, audio/wav, audio/ogg, audio/x-m4a
```

**Extensiones:**
```
md, rst, go, py, java, sh, bat, ps1, cmd, js, ts, css, cpp, hpp, h, c, cs,
htm, html, sql, log, ini, pl, pm, r, dart, dockerfile, env, php, hs, hsc,
lua, nginxconf, conf, m, mm, plsql, perl, rb, rs, db2, scala, bash, swift,
vue, svelte, msg, ex, exs, erl, tsx, jsx, hs, lhs, kt, kts, ...
```

---

## 16. Build, scripts y dev workflow

### 16.1 Scripts de `package.json`

```json
{
  "dev": "npm run pyodide:fetch && vite dev --host",
  "dev:5050": "npm run pyodide:fetch && vite dev --port 5050",
  "build": "npm run pyodide:fetch && vite build",
  "build:watch": "npm run pyodide:fetch && vite build --watch",
  "preview": "vite preview",
  "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
  "lint": "eslint . --fix && svelte-check && pylint backend/",
  "format": "prettier --plugin-search-dir --write \"**/*.{js,ts,svelte,css,md,html,json}\"",
  "i18n:parse": "i18next --config i18next-parser.config.ts && prettier --write \"src/lib/i18n/**/*.{js,json}\"",
  "cy:open": "cypress open",
  "test:frontend": "vitest --passWithNoTests",
  "pyodide:fetch": "node scripts/prepare-pyodide.js"
}
```

### 16.2 Engines

- Node: `>=18.13.0 <=22.x.x`
- npm: `>=6.0.0`

### 16.3 Testing

- **Unit:** `vitest` (`test:frontend`)
- **E2E:** `cypress` (`cy:open`)
- **Type-check:** `svelte-check` con TypeScript

### 16.4 Linting / formato

- `eslint` con `eslint-plugin-svelte`, `@typescript-eslint`
- `prettier` con `prettier-plugin-svelte`
- `eslint-config-prettier` (compatibilidad)

---

## 17. Resumen del flujo de la app

```
1. Usuario abre la app
   → +layout.svelte (root) inicializa i18n, theme, socket
   → (app)/+layout.svelte verifica auth → /auth si no
   → Carga config, user, models, settings, chats

2. Sidebar visible
   → Carga chats, folders, channels, pinned models
   → Search disponible (FuseJS)

3. Usuario hace clic en "New Chat" o un chat existente
   → Navega a /c/[id] o /
   → Chat.svelte monta:
     - Navbar con model selector
     - Messages (vacío o con historia)
     - MessageInput (Tiptap)

4. Usuario escribe y envía
   → MessageInput envía via Socket.IO o REST stream
   → Backend hace inferencia
   → Respuesta llega vía SSE/Socket
   → ResponseMessage se actualiza incrementalmente
   → Markdown/code/charts/math se renderizan en vivo

5. Características adicionales disponibles:
   → @ menciones (modelos, tools)
   → / slash commands (prompts)
   → # archivos
   → Voz / video / Pyodide / Tools
   → Artifacts en pane lateral
   → ChatControls (params del modelo)
```

---

## 18. Notas para reconstrucción

### 18.1 Decisiones clave de diseño

1. **Svelte 5 + SvelteKit 2** con `adapter-static` (SSG, no SSR runtime)
2. **TailwindCSS 4** con tokens OKLCH (mejor consistencia perceptual)
3. **Iconos custom** (no librería externa) — 176 SVG components con API consistente
4. **Stores Svelte** para estado global (no librería de state management externa)
5. **Tiptap** para todo input enriquecido (chat, notas, canales)
6. **Socket.IO** para tiempo real (chats, channels, presencia)
7. **i18next** con 61 idiomas, RTL nativo
8. **PaneForge** para layouts redimensionables (chat ↔ artifacts)
9. **bits-ui** para primitives accesibles (no Radix, es Svelte-native)
10. **Pyodide en worker** para no bloquear UI durante ejecución de Python

### 18.2 Patrones consistentes

- **Componentes con `class={className}` exportable** para customización desde el padre
- **Props con valores default** (TypeScript)
- **Stores `Writable` con `writable(initialValue)`**
- **Modales basados en `Modal.svelte` base** con `bind:show`
- **Iconos con `className` y `strokeWidth` props**
- **Async/await en todas las llamadas API**
- **i18n con `$i18n.t('key')` reactivo**

### 18.3 Convenciones de nombres

- Componentes: `PascalCase.svelte`
- Stores: `camelCase` (writables)
- Constants: `UPPER_SNAKE_CASE`
- Subcarpetas: `PascalCase/` para componentes relacionados
- Páginas: `+page.svelte`, layouts: `+layout.svelte` (SvelteKit standard)

### 18.4 Accesibilidad

- Iconos con `aria-hidden="true"` por default
- Focus traps en modales (`focus-trap`)
- Labels apropiados en inputs
- Soporte de teclado en todos los menús
- ARIA en elementos interactivos
- Soporte RTL para idiomas árabes/hebreos

---

## 19. Apéndice — Lista completa de archivos clave

| Categoría | Archivo | Tamaño |
|---|---|---|
| Layout principal | `layout/Sidebar.svelte` | 41.4 KB |
| Chat orchestrator | `chat/Chat.svelte` | 81.9 KB |
| Input de mensaje | `chat/MessageInput.svelte` | 66.9 KB |
| Respuesta del modelo | `chat/Messages/ResponseMessage.svelte` | 47.3 KB |
| Mensaje del usuario | `chat/Messages/UserMessage.svelte` | 21.5 KB |
| Container de mensajes | `chat/Messages.svelte` | 13.9 KB |
| Editor Tiptap | `common/RichTextInput.svelte` | 38.1 KB |
| File explorer | `chat/FileNav.svelte` | 47.7 KB |
| Voz/video call | `chat/MessageInput/CallOverlay.svelte` | 26.7 KB |
| Settings modal | `chat/SettingsModal.svelte` | 26.7 KB |
| Code block | `chat/Messages/CodeBlock.svelte` | 16.5 KB |
| Chat controls | `chat/ChatControls.svelte` | 15.8 KB |
| Notes editor | `notes/NoteEditor.svelte` | 40.5 KB |
| Knowledge base | `workspace/Knowledge/KnowledgeBase.svelte` | 29.9 KB |
| Model editor | `workspace/Models/ModelEditor.svelte` | 26.0 KB |
| Add tool server | `AddToolServerModal.svelte` | 30.5 KB |
| Add terminal server | `AddTerminalServerModal.svelte` | 26.0 KB |
| Add connection | `AddConnectionModal.svelte` | 22.0 KB |
| File item modal | `common/FileItemModal.svelte` | 21.8 KB |
| Recursive folder | `layout/Sidebar/RecursiveFolder.svelte` | 17.7 KB |
| Channel chat | `channel/Channel.svelte` | 9.9 KB |
| Channel input | `channel/MessageInput.svelte` | 32.0 KB |
| Search modal | `layout/SearchModal.svelte` | 12.3 KB |
| Chats modal | `layout/ChatsModal.svelte` | 17.4 KB |
| Markdown tokens | `chat/Messages/Markdown/MarkdownTokens.svelte` | 14.9 KB |

---

## 20. Versionado del PRD

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-04-10 | Versión inicial — análisis exhaustivo del frontend de Open WebUI v0.8.12 |

---

**Fin del PRD.**
