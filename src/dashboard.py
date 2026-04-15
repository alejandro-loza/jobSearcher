"""
Dashboard web ultra-moderno de JobSearcher focalizado en trazabilidad y Chatbot.
"""
from datetime import datetime
from src.db.tracker import JobTracker

def generate_dashboard_html() -> str:
    """ Genera el HTML completo para el dashboard moderno. """
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    return f"""<!DOCTYPE html>
<html lang="es" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JobSearcher | AI Recruitment Assistant</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        primary: {{
                            50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd', 
                            400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8', 
                            800: '#1e40af', 900: '#1e3a8a', 950: '#172554',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        .glass {{
            background: rgba(31, 41, 55, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .scrollbar-hide::-webkit-scrollbar {{ display: none; }}
        .scrollbar-hide {{ -ms-overflow-style: none; scrollbar-width: none; }}
        
        @keyframes float {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-10px); }}
            100% {{ transform: translateY(0px); }}
        }}
        .pulse-soft {{ animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: .7; }}
        }}
    </style>
</head>
<body class="bg-[#0b0f1a] text-gray-200 min-h-screen selection:bg-primary-500/30">

    <!-- Sidebar Mini -->
    <aside class="fixed left-0 top-0 h-full w-20 flex flex-col items-center py-8 glass z-50 border-r border-white/5">
        <div class="mb-12 text-primary-500">
            <i data-lucide="zap" class="w-8 h-8 fill-current"></i>
        </div>
        <nav class="flex flex-col gap-8">
            <button onclick="showSection('home')" class="nav-btn text-primary-400 p-3 bg-primary-500/10 rounded-xl transition-all" title="Resumen">
                <i data-lucide="layout-dashboard" class="w-6 h-6"></i>
            </button>
            <button onclick="showSection('jobs')" class="nav-btn text-gray-400 p-3 hover:text-white transition-all" title="Buscados">
                <i data-lucide="briefcase" class="w-6 h-6"></i>
            </button>
            <button onclick="showSection('apps')" class="nav-btn text-gray-400 p-3 hover:text-white transition-all" title="Aplicaciones">
                <i data-lucide="send" class="w-6 h-6"></i>
            </button>
            <button onclick="showSection('linkedin')" class="nav-btn text-gray-400 p-3 hover:text-white transition-all" title="LinkedIn">
                <i data-lucide="message-square" class="w-6 h-6"></i>
            </button>
        </nav>
        <div class="mt-auto space-y-6">
            <button onclick="refreshData()" class="text-gray-400 hover:text-white transition-all">
                <i data-lucide="refresh-cw" class="w-5 h-5"></i>
            </button>
            <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-primary-600 to-indigo-600 flex items-center justify-center font-bold text-xs ring-2 ring-white/10 shadow-lg" title="User Profile">
                AL
            </div>
        </div>
    </aside>

    <!-- Main Content -->
    <main class="ml-20 p-8 pt-6 max-w-7xl mx-auto">
        <!-- Header -->
        <header class="flex justify-between items-end mb-10">
            <div>
                <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-500">
                    Dashboard Maestro
                </h1>
                <p class="text-gray-500 text-sm mt-1 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-green-500 pulse-soft"></span>
                    JobSearcher Orchestrator Activo · <span id="last-update">{now}</span>
                </p>
            </div>
            <div class="flex gap-4">
                <button onclick="triggerSearch()" class="px-6 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-primary-600/20 flex items-center gap-2">
                    <i data-lucide="search" class="w-4 h-4"></i>
                    Búsqueda Manual
                </button>
                <button onclick="triggerApplyAll()" class="px-6 py-2.5 bg-white/5 hover:bg-white/10 text-white border border-white/10 rounded-xl text-sm font-semibold transition-all flex items-center gap-2">
                    <i data-lucide="zap" class="w-4 h-4"></i>
                    Aplicar a todo
                </button>
            </div>
        </header>

        <!-- SECTIONS CONTAINER -->
        <div id="section-home">
            <!-- Stats Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
                <div class="glass p-6 rounded-3xl group hover:border-primary-500/30 transition-all">
                    <div class="flex justify-between items-start mb-4">
                        <div class="p-3 bg-blue-500/10 rounded-2xl text-blue-500">
                            <i data-lucide="binoculars" class="w-6 h-6"></i>
                        </div>
                        <span class="text-xs font-semibold text-gray-500">+12% hoy</span>
                    </div>
                    <div class="text-4xl font-bold mb-1" id="stat-total">0</div>
                    <div class="text-sm text-gray-500 font-medium">Jobs encontrados</div>
                </div>
                <div class="glass p-6 rounded-3xl group hover:border-primary-500/30 transition-all">
                    <div class="flex justify-between items-start mb-4">
                        <div class="p-3 bg-primary-500/10 rounded-2xl text-primary-500">
                            <i data-lucide="send" class="w-6 h-6"></i>
                        </div>
                    </div>
                    <div class="text-4xl font-bold mb-1" id="stat-applied">0</div>
                    <div class="text-sm text-gray-500 font-medium">Aplicaciones enviadas</div>
                </div>
                <div class="glass p-6 rounded-3xl group hover:border-primary-500/30 transition-all">
                    <div class="flex justify-between items-start mb-4">
                        <div class="p-3 bg-green-500/10 rounded-2xl text-green-500">
                            <i data-lucide="calendar" class="w-6 h-6"></i>
                        </div>
                    </div>
                    <div class="text-4xl font-bold mb-1" id="stat-interviews">0</div>
                    <div class="text-sm text-gray-500 font-medium">Entrevistas logradas</div>
                </div>
                <div class="glass p-6 rounded-3xl group hover:border-primary-500/30 transition-all">
                    <div class="flex justify-between items-start mb-4">
                        <div class="p-3 bg-red-500/10 rounded-2xl text-red-500">
                            <i data-lucide="x-circle" class="w-6 h-6"></i>
                        </div>
                    </div>
                    <div class="text-4xl font-bold mb-1" id="stat-rejected">0</div>
                    <div class="text-sm text-gray-500 font-medium">Rechazos / Cerrados</div>
                </div>
                <div class="glass p-6 rounded-3xl group hover:border-emerald-500/30 transition-all">
                    <div class="flex justify-between items-start mb-4">
                        <div class="p-3 bg-emerald-500/10 rounded-2xl text-emerald-400">
                            <i data-lucide="activity" class="w-6 h-6"></i>
                        </div>
                    </div>
                    <div class="text-4xl font-bold mb-1 text-emerald-400" id="stat-active">0</div>
                    <div class="text-sm text-gray-500 font-medium">Procesos Activos</div>
                </div>
                <div class="glass p-6 rounded-3xl group hover:border-gray-500/30 transition-all">
                    <div class="flex justify-between items-start mb-4">
                        <div class="p-3 bg-gray-500/10 rounded-2xl text-gray-400">
                            <i data-lucide="ghost" class="w-6 h-6"></i>
                        </div>
                    </div>
                    <div class="text-4xl font-bold mb-1 text-gray-400" id="stat-ghosted">0</div>
                    <div class="text-sm text-gray-500 font-medium">Ghosted</div>
                </div>
            </div>

            <!-- Pipeline Visual (Kanban Lite) -->
            <h2 class="text-xl font-bold mb-6 flex items-center gap-2">
                <i data-lucide="trending-up" class="w-5 h-5 text-primary-500"></i>
                Pipeline de Proceso
            </h2>
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-10 overflow-x-auto pb-4 scrollbar-hide" id="pipeline-container">
                <!-- Se llena dinamico -->
            </div>
        </div>

        <div id="section-jobs" class="hidden">
             <!-- Jobs Section Header -->
             <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
                <div>
                    <h2 class="text-xl font-bold flex items-center gap-2">
                        <i data-lucide="briefcase" class="w-5 h-5 text-primary-500"></i>
                        Vacantes Encontradas
                    </h2>
                    <p class="text-xs text-gray-500 mt-1">Actualización cada 3 horas · <span id="jobs-count">0</span> vacantes</p>
                </div>
                <div class="flex flex-wrap gap-3">
                    <!-- Search -->
                    <div class="relative">
                        <i data-lucide="search" class="w-4 h-4 absolute left-3 top-2.5 text-gray-500"></i>
                        <input type="text" id="jobs-search" placeholder="Buscar empresa o puesto..."
                            class="bg-white/5 border border-white/10 rounded-xl py-2 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 w-64"
                            oninput="filterJobs()">
                    </div>
                </div>
             </div>

             <!-- Jobs Filter Tabs -->
             <div class="flex flex-wrap gap-2 mb-6">
                <button onclick="setJobFilter('all')" class="job-filter-btn px-4 py-2 rounded-xl text-xs font-bold transition-all bg-primary-600 text-white" data-filter="all">
                    Todos
                </button>
                <button onclick="setJobFilter('found')" class="job-filter-btn px-4 py-2 rounded-xl text-xs font-bold transition-all bg-white/5 text-gray-400 hover:bg-white/10" data-filter="found">
                    Nuevos
                </button>
                <button onclick="setJobFilter('applied')" class="job-filter-btn px-4 py-2 rounded-xl text-xs font-bold transition-all bg-white/5 text-gray-400 hover:bg-white/10" data-filter="applied">
                    Aplicados
                </button>
                <button onclick="setJobFilter('pending_apply')" class="job-filter-btn px-4 py-2 rounded-xl text-xs font-bold transition-all bg-white/5 text-gray-400 hover:bg-white/10" data-filter="pending_apply">
                    Pendientes
                </button>
                <button onclick="setJobFilter('ghosted')" class="job-filter-btn px-4 py-2 rounded-xl text-xs font-bold transition-all bg-white/5 text-gray-400 hover:bg-white/10" data-filter="ghosted">
                    👻 Ghosted
                </button>
                <button onclick="setJobFilter('rejected')" class="job-filter-btn px-4 py-2 rounded-xl text-xs font-bold transition-all bg-white/5 text-gray-400 hover:bg-white/10" data-filter="rejected">
                    Rechazados
                </button>
                <span class="border-l border-white/10 mx-2"></span>
                <button onclick="setJobScoreFilter(75)" class="job-score-btn px-4 py-2 rounded-xl text-xs font-bold transition-all bg-white/5 text-gray-400 hover:bg-white/10" data-min="75">
                    Score >= 75%
                </button>
                <button onclick="setJobScoreFilter(85)" class="job-score-btn px-4 py-2 rounded-xl text-xs font-bold transition-all bg-white/5 text-gray-400 hover:bg-white/10" data-min="85">
                    Premium >= 85%
                </button>
             </div>

             <!-- Jobs Stats Row -->
             <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                <div class="glass p-4 rounded-2xl text-center">
                    <div class="text-2xl font-bold text-white" id="jobs-stat-total">0</div>
                    <div class="text-[10px] text-gray-500 uppercase font-bold">Total</div>
                </div>
                <div class="glass p-4 rounded-2xl text-center">
                    <div class="text-2xl font-bold text-blue-400" id="jobs-stat-found">0</div>
                    <div class="text-[10px] text-gray-500 uppercase font-bold">Nuevos</div>
                </div>
                <div class="glass p-4 rounded-2xl text-center">
                    <div class="text-2xl font-bold text-green-400" id="jobs-stat-applied">0</div>
                    <div class="text-[10px] text-gray-500 uppercase font-bold">Aplicados</div>
                </div>
                <div class="glass p-4 rounded-2xl text-center">
                    <div class="text-2xl font-bold text-yellow-400" id="jobs-stat-pending">0</div>
                    <div class="text-[10px] text-gray-500 uppercase font-bold">Pendientes</div>
                </div>
                <div class="glass p-4 rounded-2xl text-center">
                    <div class="text-2xl font-bold text-primary-400" id="jobs-stat-high">0</div>
                    <div class="text-[10px] text-gray-500 uppercase font-bold">Score >= 75%</div>
                </div>
             </div>

             <!-- Jobs Table -->
             <div class="glass rounded-3xl overflow-hidden mb-10">
                <div class="overflow-x-auto" style="max-height: 70vh;">
                    <table class="w-full text-left text-sm">
                        <thead class="bg-white/5 border-b border-white/5 text-gray-500 uppercase text-[10px] tracking-wider font-bold sticky top-0 z-10" style="background: rgba(11,15,26,0.95);">
                            <tr>
                                <th class="px-5 py-4 cursor-pointer hover:text-white" onclick="sortJobs('match_score')">Score</th>
                                <th class="px-5 py-4 cursor-pointer hover:text-white" onclick="sortJobs('title')">Job / Empresa</th>
                                <th class="px-5 py-4">Ubicación</th>
                                <th class="px-5 py-4 cursor-pointer hover:text-white" onclick="sortJobs('status')">Status</th>
                                <th class="px-5 py-4">Actividad</th>
                                <th class="px-5 py-4 cursor-pointer hover:text-white" onclick="sortJobs('found_at')">Fecha</th>
                                <th class="px-5 py-4">Ver</th>
                            </tr>
                        </thead>
                        <tbody id="jobs-tbody" class="divide-y divide-white/5">
                        </tbody>
                    </table>
                </div>
                <!-- Pagination -->
                <div class="flex justify-between items-center px-6 py-4 border-t border-white/5">
                    <span class="text-xs text-gray-500">Mostrando <span id="jobs-showing">0</span> de <span id="jobs-total-filtered">0</span></span>
                    <div class="flex gap-2">
                        <button onclick="jobsPage(-1)" class="px-3 py-1 bg-white/5 rounded-lg text-xs hover:bg-white/10">Anterior</button>
                        <span class="px-3 py-1 text-xs text-gray-400" id="jobs-page-info">1 / 1</span>
                        <button onclick="jobsPage(1)" class="px-3 py-1 bg-white/5 rounded-lg text-xs hover:bg-white/10">Siguiente</button>
                    </div>
                </div>
             </div>

             <!-- Job Detail Modal -->
             <div id="job-modal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] hidden flex items-center justify-center p-4" onclick="if(event.target===this)closeJobModal()">
                <div class="glass rounded-3xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-8">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <h3 class="text-xl font-bold text-white" id="modal-title"></h3>
                            <p class="text-sm text-gray-400" id="modal-company"></p>
                        </div>
                        <button onclick="closeJobModal()" class="text-gray-400 hover:text-white p-1">
                            <i data-lucide="x" class="w-5 h-5"></i>
                        </button>
                    </div>
                    <div class="flex flex-wrap gap-3 mb-4">
                        <span class="px-3 py-1 rounded-lg text-xs font-bold" id="modal-score-badge"></span>
                        <span class="px-3 py-1 bg-white/5 rounded-lg text-xs text-gray-400" id="modal-location"></span>
                        <span class="px-3 py-1 bg-white/5 rounded-lg text-xs text-gray-400" id="modal-salary"></span>
                        <span class="px-3 py-1 bg-white/5 rounded-lg text-xs text-gray-400" id="modal-source"></span>
                    </div>
                    <!-- Tabs -->
                    <div class="flex gap-1 mb-4 border-b border-white/10">
                        <button onclick="switchModalTab('desc')" id="tab-desc" class="px-4 py-2 text-xs font-bold text-white border-b-2 border-primary-500">Descripción</button>
                        <button onclick="switchModalTab('activity')" id="tab-activity" class="px-4 py-2 text-xs font-bold text-gray-500 border-b-2 border-transparent hover:text-gray-300">Actividad</button>
                    </div>
                    <div id="tab-desc-content">
                        <div class="text-sm text-gray-300 leading-relaxed whitespace-pre-line max-h-[35vh] overflow-y-auto mb-4 scrollbar-hide" id="modal-description"></div>
                        <a id="modal-url" href="#" target="_blank" class="px-5 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-semibold inline-flex items-center gap-2">
                            <i data-lucide="external-link" class="w-4 h-4"></i> Ver Vacante
                        </a>
                    </div>
                    <div id="tab-activity-content" class="hidden">
                        <div id="modal-timeline" class="text-xs max-h-[40vh] overflow-y-auto scrollbar-hide"></div>
                    </div>
                </div>
             </div>
        </div>

        <div id="section-apps" class="hidden">
             <h2 class="text-xl font-bold mb-6">Pipeline de Aplicaciones</h2>
             <div class="glass rounded-3xl overflow-hidden mb-10">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="bg-white/5 border-b border-white/5 text-gray-500 uppercase text-[10px] tracking-wider font-bold">
                            <tr>
                                <th class="px-6 py-4">Puesto / Empresa</th>
                                <th class="px-6 py-4">Etapa</th>
                                <th class="px-6 py-4">Fecha Aplic.</th>
                                <th class="px-6 py-4">Notas</th>
                            </tr>
                        </thead>
                        <tbody id="apps-tbody" class="divide-y divide-white/5">
                            <!-- Se llena dinamico -->
                        </tbody>
                    </table>
                </div>
             </div>
        </div>

        <div id="section-linkedin" class="hidden">
             <h2 class="text-xl font-bold mb-6">LinkedIn Conversations</h2>
             <div id="conv-list" class="grid gap-4">
                 <!-- Se llena dinamico -->
             </div>
        </div>

    </main>

    <!-- FLOATING CHAT WIDGET -->
    <div class="fixed bottom-8 right-8 z-[100] flex flex-col items-end">
        <!-- Chat Area -->
        <div id="chat-container" class="hidden mb-4 w-[400px] h-[580px] glass rounded-[2.5rem] flex flex-col overflow-hidden shadow-2xl border-white/10 animate-in slide-in-from-bottom-5 duration-300">
            <!-- Header -->
            <div class="p-6 bg-primary-600/20 border-b border-white/5 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-primary-500 flex items-center justify-center text-white relative">
                        <i data-lucide="bot" class="w-6 h-6"></i>
                        <span class="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-[#161d2a] rounded-full"></span>
                    </div>
                    <div>
                        <h4 class="font-bold text-sm">JobBot AI</h4>
                        <p class="text-[10px] text-primary-400">En línea · Master Agent</p>
                    </div>
                </div>
                <button onclick="toggleChat()" class="text-gray-400 hover:text-white">
                    <i data-lucide="x" class="w-5 h-5"></i>
                </button>
            </div>
            
            <!-- Messages Area -->
            <div id="chat-messages" class="flex-1 overflow-y-auto p-6 space-y-4 scroll-smooth scrollbar-hide">
                <div class="flex gap-3 max-w-[85%]">
                    <div class="w-8 h-8 rounded-full bg-primary-500/10 flex items-center justify-center text-primary-500 flex-shrink-0">
                        <i data-lucide="bot" class="w-4 h-4"></i>
                    </div>
                    <div class="bg-primary-500/10 p-3 rounded-2xl rounded-tl-none text-sm leading-relaxed">
                        ¡Hola Alejandro! 👋 Soy tu asistente personal. ¿En qué puedo ayudarte hoy? 
                        Puedo buscar jobs, mostrarte tu progreso o aplicar a vacantes pendientes.
                    </div>
                </div>
            </div>

            <!-- Input Area -->
            <div class="p-6 border-t border-white/5 bg-[#0b0f1a]/50">
                <div class="relative">
                    <input type="text" id="chat-input" 
                        class="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-4 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 transition-all"
                        placeholder="Escribe un mensaje..."
                        onkeypress="if(event.key === 'Enter') sendMessage()">
                    <button onclick="sendMessage()" class="absolute right-2 top-2 p-1.5 bg-primary-600 text-white rounded-xl hover:bg-primary-500 transition-all">
                        <i data-lucide="send" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
        </div>

        <!-- Toggle Button -->
        <button onclick="toggleChat()" class="w-16 h-16 bg-primary-600 hover:bg-primary-500 text-white rounded-full flex items-center justify-center shadow-xl shadow-primary-500/20 transition-all hover:scale-105 active:scale-95 group relative">
            <i data-lucide="message-square" class="w-7 h-7 group-hover:hidden"></i>
            <i data-lucide="chevron-down" class="w-7 h-7 hidden group-hover:block transition-all"></i>
            <span class="absolute -top-1 -right-1 w-5 h-5 bg-red-500 border-2 border-[#161d2a] rounded-full text-[10px] font-bold flex items-center justify-center">1</span>
        </button>
    </div>

    <script>
        // -- NAVIGATION --
        function showSection(id) {{
            const sections = ['home', 'jobs', 'apps', 'linkedin'];
            sections.forEach(s => {{
                document.getElementById('section-' + s).classList.toggle('hidden', s !== id);
            }});
            
            // Update btn styles
            document.querySelectorAll('.nav-btn').forEach(btn => {{
                const isTarget = btn.title.toLowerCase().includes(id.substring(0,3));
                btn.classList.toggle('text-primary-400', isTarget);
                btn.classList.toggle('bg-primary-500/10', isTarget);
                btn.classList.toggle('text-gray-400', !isTarget);
                btn.classList.toggle('bg-transparent', !isTarget);
            }});
        }}

        // -- JOBS STATE --
        let allJobs = [];
        let filteredJobs = [];
        let currentJobFilter = 'all';
        let currentMinScore = 0;
        let currentJobSort = 'found_at';
        let jobSortAsc = false;
        let jobPageNum = 0;
        const JOBS_PER_PAGE = 50;

        function scoreColor(s) {{
            if (s >= 85) return 'text-green-400 bg-green-500/10';
            if (s >= 75) return 'text-primary-400 bg-primary-500/10';
            if (s >= 50) return 'text-yellow-400 bg-yellow-500/10';
            return 'text-gray-500 bg-white/5';
        }}

        function statusBadge(st) {{
            const m = {{
                'found':               'bg-blue-500/10 text-blue-400',
                'applied':             'bg-green-500/10 text-green-400',
                'pending_apply':       'bg-yellow-500/10 text-yellow-400',
                'rejected':            'bg-red-500/10 text-red-400',
                'interview_scheduled': 'bg-purple-500/10 text-purple-400',
                'ghosted':             'bg-gray-500/10 text-gray-400',
                'applying':            'bg-blue-400/10 text-blue-300',
                'apply_failed':        'bg-orange-500/10 text-orange-400',
                'apply_needs_manual':  'bg-yellow-500/10 text-yellow-300',
                'offer_received':      'bg-emerald-500/10 text-emerald-400',
            }};
            return m[st] || 'bg-white/5 text-gray-400';
        }}

        function statusLabel(st) {{
            const m = {{
                'found': 'Nuevo', 'applied': 'Aplicado', 'pending_apply': 'Pendiente',
                'rejected': 'Rechazado', 'interview_scheduled': '📅 Entrevista',
                'ghosted': '👻 Ghosted', 'applying': 'Aplicando...',
                'apply_failed': 'Falló', 'apply_needs_manual': 'Manual',
                'offer_received': '🎯 Oferta',
            }};
            return m[st] || st;
        }}

        function activityBadge(j) {{
            const icons = [];
            if (j.status === 'interview_scheduled' || j.status === 'offer_received')
                icons.push('<span title="Proceso activo" class="text-emerald-400">🔥</span>');
            if (j.status === 'applied' || j.status === 'interview_scheduled')
                icons.push('<span title="Ver actividad" class="text-blue-400 text-xs">📧</span>');
            if (j.status === 'ghosted')
                icons.push('<span title="Sin respuesta">👻</span>');
            return icons.length ? icons.join(' ') : '<span class="text-gray-600 text-xs">—</span>';
        }}

        function sourceBadge(src) {{
            const m = {{
                'linkedin': 'bg-blue-600/10 text-blue-400',
                'indeed': 'bg-indigo-500/10 text-indigo-400',
                'glassdoor': 'bg-green-600/10 text-green-400',
            }};
            return m[src] || 'bg-white/5 text-gray-400';
        }}

        function setJobFilter(f) {{
            currentJobFilter = f;
            jobPageNum = 0;
            document.querySelectorAll('.job-filter-btn').forEach(b => {{
                const active = b.dataset.filter === f;
                b.className = `job-filter-btn px-4 py-2 rounded-xl text-xs font-bold transition-all ${{active ? 'bg-primary-600 text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'}}`;
            }});
            filterJobs();
        }}

        function setJobScoreFilter(min) {{
            currentMinScore = currentMinScore === min ? 0 : min;
            jobPageNum = 0;
            document.querySelectorAll('.job-score-btn').forEach(b => {{
                const active = parseInt(b.dataset.min) === currentMinScore;
                b.className = `job-score-btn px-4 py-2 rounded-xl text-xs font-bold transition-all ${{active ? 'bg-primary-600 text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'}}`;
            }});
            filterJobs();
        }}

        function sortJobs(field) {{
            if (currentJobSort === field) jobSortAsc = !jobSortAsc;
            else {{ currentJobSort = field; jobSortAsc = field === 'title'; }}
            filterJobs();
        }}

        function filterJobs() {{
            const q = (document.getElementById('jobs-search')?.value || '').toLowerCase();
            filteredJobs = allJobs.filter(j => {{
                if (currentJobFilter !== 'all' && j.status !== currentJobFilter) return false;
                if (currentMinScore > 0 && (j.match_score || 0) < currentMinScore) return false;
                if (q && !(j.title || '').toLowerCase().includes(q) && !(j.company || '').toLowerCase().includes(q) && !(j.location || '').toLowerCase().includes(q)) return false;
                return true;
            }});
            filteredJobs.sort((a, b) => {{
                let va = a[currentJobSort] ?? '', vb = b[currentJobSort] ?? '';
                if (typeof va === 'number') return jobSortAsc ? va - vb : vb - va;
                return jobSortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
            }});
            renderJobsPage();
        }}

        function jobsPage(dir) {{
            const maxP = Math.max(0, Math.ceil(filteredJobs.length / JOBS_PER_PAGE) - 1);
            jobPageNum = Math.max(0, Math.min(maxP, jobPageNum + dir));
            renderJobsPage();
        }}

        function renderJobsPage() {{
            const start = jobPageNum * JOBS_PER_PAGE;
            const page = filteredJobs.slice(start, start + JOBS_PER_PAGE);
            const totalPages = Math.max(1, Math.ceil(filteredJobs.length / JOBS_PER_PAGE));

            document.getElementById('jobs-count').innerText = allJobs.length;
            document.getElementById('jobs-total-filtered').innerText = filteredJobs.length;
            document.getElementById('jobs-showing').innerText = page.length;
            document.getElementById('jobs-page-info').innerText = `${{jobPageNum + 1}} / ${{totalPages}}`;

            // Stats
            document.getElementById('jobs-stat-total').innerText = allJobs.length;
            document.getElementById('jobs-stat-found').innerText = allJobs.filter(j => j.status === 'found').length;
            document.getElementById('jobs-stat-applied').innerText = allJobs.filter(j => j.status === 'applied').length;
            document.getElementById('jobs-stat-pending').innerText = allJobs.filter(j => j.status === 'pending_apply').length;
            document.getElementById('jobs-stat-high').innerText = allJobs.filter(j => (j.match_score || 0) >= 75).length;

            const tbody = document.getElementById('jobs-tbody');
            tbody.innerHTML = page.map((j, i) => {{
                const activityIcons = activityBadge(j);
                return `
                <tr class="hover:bg-white/[0.03] cursor-pointer" onclick="openJobTimeline('${{j.id}}', '${{(j.title||'').replace(/'/g,"\\'")}}',${{start + i}})">
                    <td class="px-5 py-3.5">
                        <div class="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${{scoreColor(j.match_score || 0)}}">
                            ${{j.match_score || 0}}
                        </div>
                    </td>
                    <td class="px-5 py-3.5">
                        <div class="font-semibold text-white text-sm line-clamp-1 max-w-xs">${{j.title || 'N/A'}}</div>
                        <div class="text-xs text-gray-500">${{j.company || 'N/A'}}</div>
                    </td>
                    <td class="px-5 py-3.5 text-xs text-gray-400 max-w-[100px] truncate">${{j.location && j.location !== 'nan' ? j.location : 'Remote'}}</td>
                    <td class="px-5 py-3.5">
                        <span class="text-[10px] px-2.5 py-1 rounded-lg font-bold uppercase ${{statusBadge(j.status)}}">${{statusLabel(j.status)}}</span>
                    </td>
                    <td class="px-5 py-3.5 text-sm">${{activityIcons}}</td>
                    <td class="px-5 py-3.5 text-xs text-gray-500">${{(j.found_at || '').substring(5, 16).replace('T', ' ')}}</td>
                    <td class="px-5 py-3.5">
                        <button onclick="event.stopPropagation();openJobTimeline('${{j.id}}','${{(j.title||'').replace(/'/g,"\\'")}}', ${{start+i}})"
                            class="p-1.5 px-3 bg-white/5 rounded-lg text-[10px] hover:bg-primary-500/20 hover:text-primary-400 transition-all inline-flex items-center gap-1">
                            <i data-lucide="panel-right" class="w-3 h-3"></i> Ver
                        </button>
                    </td>
                </tr>`;
            }}).join('') || '<tr><td colspan="7" class="text-center py-10 text-gray-500 italic">No se encontraron vacantes con estos filtros</td></tr>';
            lucide.createIcons();
        }}

        function openJobModal(idx) {{ openJobTimeline(filteredJobs[idx]?.id, filteredJobs[idx]?.title, idx); }}

        async function openJobTimeline(jobId, jobTitle, idx) {{
            const j = filteredJobs[idx] || {{}};
            // Header inmediato
            document.getElementById('modal-title').innerText = j.title || jobTitle || 'N/A';
            document.getElementById('modal-company').innerText = (j.company || '') + (j.location && j.location !== 'nan' ? ' · ' + j.location : ' · Remote');
            const sb = document.getElementById('modal-score-badge');
            sb.innerText = (j.match_score || 0) + '% match';
            sb.className = `px-3 py-1 rounded-lg text-xs font-bold ${{scoreColor(j.match_score || 0)}}`;
            document.getElementById('modal-location').innerText = j.location && j.location !== 'nan' ? j.location : 'Remote';
            document.getElementById('modal-salary').innerText = j.salary || '—';
            document.getElementById('modal-source').innerText = (j.source || '').toUpperCase();
            document.getElementById('modal-description').innerText = (j.description || 'Sin descripción disponible').substring(0, 2000);
            document.getElementById('modal-url').href = j.url || '#';
            document.getElementById('modal-timeline').innerHTML = '<div class="text-gray-500 text-xs py-4 text-center">Cargando actividad...</div>';
            document.getElementById('job-modal').classList.remove('hidden');

            // Fetch timeline
            try {{
                const data = await fetch(`/api/job/${{jobId}}/timeline`).then(r => r.json());
                renderTimeline(data);
            }} catch(e) {{
                document.getElementById('modal-timeline').innerHTML = '<div class="text-gray-600 text-xs py-4 text-center">Sin actividad registrada</div>';
            }}
        }}

        function renderTimeline(data) {{
            const el = document.getElementById('modal-timeline');
            const sections = [];

            // Aplicaciones
            if (data.applications?.length) {{
                const a = data.applications[0];
                sections.push(`<div class="mb-3">
                    <div class="text-[10px] text-gray-500 uppercase font-bold mb-1">Aplicación</div>
                    <div class="flex items-center gap-2 text-xs">
                        <span class="text-[10px] px-2 py-0.5 rounded font-bold uppercase ${{statusBadge(a.status)}}">${{statusLabel(a.status)}}</span>
                        <span class="text-gray-500">${{(a.applied_at||'').substring(0,10)}}</span>
                        <span class="text-gray-600">${{a.method||''}}</span>
                        ${{a.attempt_count > 1 ? `<span class="text-orange-400 text-[10px]">${{a.attempt_count}} intentos</span>` : ''}}
                    </div>
                    ${{a.failure_reason ? `<div class="text-orange-400 text-[10px] mt-1">${{a.failure_reason}}</div>` : ''}}
                </div>`);
            }}

            // Días desde aplicación
            if (data.days_since_applied !== null && data.days_since_applied !== undefined) {{
                const d = data.days_since_applied;
                const color = d >= 21 ? 'text-gray-400' : d >= 7 ? 'text-yellow-400' : 'text-green-400';
                sections.push(`<div class="text-xs ${{color}} mb-3">⏱ ${{d}} días desde aplicación</div>`);
            }}

            // Entrevistas
            if (data.interviews?.length) {{
                sections.push(`<div class="mb-3">
                    <div class="text-[10px] text-gray-500 uppercase font-bold mb-1">📅 Entrevistas</div>
                    ${{data.interviews.map(i => `
                        <div class="text-xs text-purple-300 mb-1">
                            ${{(i.scheduled_at||'').substring(0,16).replace('T',' ')}}
                            ${{i.interviewer ? '· ' + i.interviewer : ''}}
                            <span class="text-[10px] text-purple-500">${{i.status}}</span>
                        </div>
                    `).join('')}}
                </div>`);
            }}

            // Emails
            if (data.emails?.length) {{
                sections.push(`<div class="mb-3">
                    <div class="text-[10px] text-gray-500 uppercase font-bold mb-1">📧 Emails (${{data.emails.length}})</div>
                    ${{data.emails.slice(0,3).map(e => {{
                        const sentIcon = {{'positive':'✅','interview':'📅','negative':'❌'}}[e.sentiment] || '📧';
                        return `<div class="text-xs mb-1.5 border-l-2 border-white/10 pl-2">
                            <span class="mr-1">${{sentIcon}}</span>
                            <span class="text-white/80">${{(e.subject||'Sin asunto').substring(0,50)}}</span>
                            <span class="text-gray-500 ml-1 text-[10px]">${{(e.received_at||'').substring(0,10)}}</span>
                        </div>`;
                    }}).join('')}}
                </div>`);
            }}

            // LinkedIn
            if (data.linkedin?.length) {{
                sections.push(`<div class="mb-3">
                    <div class="text-[10px] text-gray-500 uppercase font-bold mb-1">💬 LinkedIn</div>
                    ${{data.linkedin.slice(0,2).map(c => `
                        <div class="text-xs mb-1 flex items-center gap-2">
                            <span class="text-white/80">${{c.participant_name||'?'}}</span>
                            <span class="text-[10px] text-gray-500">${{(c.participant_title||'').substring(0,35)}}</span>
                            <span class="text-[10px] px-1.5 py-0.5 bg-white/5 rounded text-gray-400">${{c.state}}</span>
                        </div>
                    `).join('')}}
                </div>`);
            }}

            el.innerHTML = sections.length
                ? sections.join('<div class="border-t border-white/5 my-2"></div>')
                : '<div class="text-gray-600 text-xs py-4 text-center">Sin actividad registrada aún</div>';
        }}

        function closeJobModal() {{
            document.getElementById('job-modal').classList.add('hidden');
            switchModalTab('desc');
        }}

        function switchModalTab(tab) {{
            document.getElementById('tab-desc-content').classList.toggle('hidden', tab !== 'desc');
            document.getElementById('tab-activity-content').classList.toggle('hidden', tab !== 'activity');
            document.getElementById('tab-desc').className = `px-4 py-2 text-xs font-bold border-b-2 ${{tab==='desc'?'text-white border-primary-500':'text-gray-500 border-transparent hover:text-gray-300'}}`;
            document.getElementById('tab-activity').className = `px-4 py-2 text-xs font-bold border-b-2 ${{tab==='activity'?'text-white border-primary-500':'text-gray-500 border-transparent hover:text-gray-300'}}`;
        }}

        // -- DATA LOADING --
        async function refreshData() {{
            try {{
                // Stats
                const stats = await fetch('/api/stats').then(r => r.json());
                document.getElementById('stat-total').innerText = stats.total_found || 0;
                document.getElementById('stat-applied').innerText = stats.applied || 0;
                document.getElementById('stat-interviews').innerText = stats.interviews_scheduled || 0;
                document.getElementById('stat-rejected').innerText = stats.rejected || 0;
                document.getElementById('stat-active').innerText = stats.active_processes || 0;
                document.getElementById('stat-ghosted').innerText = stats.ghosted || 0;

                // Jobs — load all
                allJobs = await fetch('/api/jobs?status=all&limit=2000').then(r => r.json());
                filterJobs();

                // Apps
                const apps = await fetch('/api/applications').then(r => r.json());
                const appsTbody = document.getElementById('apps-tbody');
                appsTbody.innerHTML = apps.map(a => `
                    <tr class="hover:bg-white/[0.02]">
                        <td class="px-6 py-4">
                            <div class="font-bold text-white text-sm">${{a.title}}</div>
                            <div class="text-xs text-gray-500">${{a.company}}</div>
                        </td>
                        <td class="px-6 py-4">
                             <div class="flex items-center gap-2">
                                <span class="w-1.5 h-1.5 rounded-full bg-primary-500"></span>
                                <span class="text-xs font-semibold uppercase tracking-tight text-primary-400">${{a.pipeline_stage}}</span>
                             </div>
                        </td>
                        <td class="px-6 py-4 text-xs text-gray-500">
                             ${{a.applied_at.substring(0,10)}}
                        </td>
                        <td class="px-6 py-4 text-xs text-gray-500 max-w-xs truncate">
                            ${{a.notes || '---'}}
                        </td>
                    </tr>
                `).join('');

                // LinkedIn
                const convs = await fetch('/api/conversations').then(r => r.json());
                const convList = document.getElementById('conv-list');
                convList.innerHTML = convs.length ? convs.map(c => `
                    <div class="glass p-5 rounded-2xl flex items-center justify-between group hover:border-primary-500/40 transition-all cursor-pointer">
                        <div class="flex gap-4 items-center">
                            <div class="w-12 h-12 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-500">
                                <i data-lucide="user" class="w-6 h-6"></i>
                            </div>
                            <div>
                                <h4 class="font-bold text-white text-sm">${{c.participant_name}}</h4>
                                <p class="text-xs text-gray-500">${{c.participant_title || 'Recruiter'}}</p>
                            </div>
                        </div>
                        <span class="px-3 py-1 bg-primary-500/10 text-primary-400 text-[10px] font-bold rounded-lg uppercase">${{c.state}}</span>
                    </div>
                `).join('') : '<div class="text-gray-500 text-center py-10 italic">No hay mensajes recientes sin procesar</div>';

                lucide.createIcons();
                document.getElementById('last-update').innerText = new Date().toLocaleTimeString();
            }} catch(e) {{
                console.error("Error cargando datos: ", e);
            }}
        }}

        // -- ACTIONS --
        async function triggerSearch() {{
            await fetch('/trigger/search', {{method:'POST'}});
            alert("Búsqueda iniciada en background");
        }}

        async function triggerApplyAll() {{
            const ok = confirm("¿Aplicar a todos los jobs con match >= 75%?");
            if(ok) {{
                await fetch('/trigger/apply-all', {{method:'POST'}});
                alert("Proceso de aplicaciones masivas iniciado");
            }}
        }}

        // -- CHAT LOGIC --
        function toggleChat() {{
            const c = document.getElementById('chat-container');
            c.classList.toggle('hidden');
            if(!c.classList.contains('hidden')) {{
                document.getElementById('chat-input').focus();
            }}
        }}

        async function sendMessage() {{
            const input = document.getElementById('chat-input');
            const msg = input.value.trim();
            if(!msg) return;

            const chat = document.getElementById('chat-messages');
            
            // Add user message
            chat.innerHTML += `
                <div class="flex flex-row-reverse gap-3 max-w-[85%] ml-auto">
                    <div class="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white flex-shrink-0">
                        <i data-lucide="user" class="w-4 h-4"></i>
                    </div>
                    <div class="bg-primary-600 text-white p-3 rounded-2xl rounded-tr-none text-sm leading-relaxed shadow-lg">
                        ${{msg}}
                    </div>
                </div>
            `;
            input.value = "";
            chat.scrollTop = chat.scrollHeight;
            lucide.createIcons();

            // Loading state
            const loadingId = 'loading-' + Date.now();
            chat.innerHTML += `
                <div id="${{loadingId}}" class="flex gap-3 max-w-[85%]">
                     <div class="w-8 h-8 rounded-full bg-primary-500/10 flex items-center justify-center text-primary-500 flex-shrink-0">
                        <i data-lucide="bot" class="w-4 h-4"></i>
                    </div>
                    <div class="bg-white/5 p-3 rounded-2xl rounded-tl-none text-sm text-gray-400">
                        Escribiendo...
                    </div>
                </div>
            `;
            chat.scrollTop = chat.scrollHeight;

            try {{
                const res = await fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ message: msg }})
                }}).then(r => r.json());

                document.getElementById(loadingId).remove();
                chat.innerHTML += `
                    <div class="flex gap-3 max-w-[85%]">
                        <div class="w-8 h-8 rounded-full bg-primary-500/10 flex items-center justify-center text-primary-500 flex-shrink-0">
                            <i data-lucide="bot" class="w-4 h-4"></i>
                        </div>
                        <div class="bg-white/5 p-4 rounded-2xl rounded-tl-none text-sm leading-relaxed border border-white/5 prose prose-invert">
                            ${{res.response.replace(/\\n/g, '<br>')}}
                        </div>
                    </div>
                `;
            }} catch(e) {{
                document.getElementById(loadingId).remove();
                chat.innerHTML += `<div class="text-red-400 text-xs px-10">Error de conexión.</div>`;
            }}
            
            chat.scrollTop = chat.scrollHeight;
            lucide.createIcons();
        }}

        // Init
        window.addEventListener('load', () => {{
            lucide.createIcons();
            refreshData();
            setInterval(refreshData, 30000);
        }});
        document.addEventListener('keydown', e => {{
            if (e.key === 'Escape') closeJobModal();
        }});
    </script>
</body>
</html>"""
