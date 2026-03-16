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
             <!-- Jobs Table Section -->
             <div class="flex justify-between items-center mb-6">
                <h2 class="text-xl font-bold">Jobs Sugeridos</h2>
                <div class="flex border border-white/10 rounded-xl overflow-hidden glass">
                    <button class="px-4 py-1.5 text-xs bg-primary-600 text-white">Todos</button>
                    <button class="px-4 py-1.5 text-xs hover:bg-white/5 border-l border-white/10">High Score (>=75%)</button>
                </div>
             </div>
             <div class="glass rounded-3xl overflow-hidden mb-10">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="bg-white/5 border-b border-white/5 text-gray-500 uppercase text-[10px] tracking-wider font-bold">
                            <tr>
                                <th class="px-6 py-4">Status</th>
                                <th class="px-6 py-4">Job / Empresa</th>
                                <th class="px-6 py-4">Match</th>
                                <th class="px-6 py-4">Fuente</th>
                                <th class="px-6 py-4">Fecha</th>
                                <th class="px-6 py-4">Acción</th>
                            </tr>
                        </thead>
                        <tbody id="jobs-tbody" class="divide-y divide-white/5">
                            <!-- Se llena dinamico -->
                        </tbody>
                    </table>
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

        // -- DATA LOADING --
        async function refreshData() {{
            try {{
                // Stats
                const stats = await fetch('/api/stats').then(r => r.json());
                document.getElementById('stat-total').innerText = stats.total_found;
                document.getElementById('stat-applied').innerText = stats.applied;
                document.getElementById('stat-interviews').innerText = stats.interviews_scheduled;
                document.getElementById('stat-rejected').innerText = stats.rejected;

                // Jobs
                const jobs = await fetch('/api/jobs').then(r => r.json());
                const jobsTbody = document.getElementById('jobs-tbody');
                jobsTbody.innerHTML = jobs.map(j => `
                    <tr class="hover:bg-white/[0.02]">
                        <td class="px-6 py-4">
                            <span class="text-[10px] px-2 py-1 rounded bg-blue-500/10 text-blue-400 font-bold uppercase">${{j.status}}</span>
                        </td>
                        <td class="px-6 py-4">
                            <div class="font-bold text-white text-sm line-clamp-1">${{j.title}}</div>
                            <div class="text-xs text-gray-500">${{j.company}}</div>
                        </td>
                        <td class="px-6 py-4">
                            <div class="font-bold text-sm ${{j.match_score >= 80 ? 'text-green-500' : 'text-primary-400'}}">${{j.match_score}}%</div>
                        </td>
                        <td class="px-6 py-4 text-xs font-medium text-gray-500 uppercase">
                            ${{j.source}}
                        </td>
                        <td class="px-6 py-4 text-xs text-gray-500">
                            ${{j.found_at.substring(5,16).replace('T', ' ')}}
                        </td>
                        <td class="px-6 py-4">
                            <a href="${{j.url}}" target="_blank" class="p-1 px-3 bg-white/5 rounded-lg text-[10px] hover:bg-white/10 transition-all">Ver URL</a>
                        </td>
                    </tr>
                `).join('');

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
            // Polling
            setInterval(refreshData, 20000);
        }});
    </script>
</body>
</html>"""
