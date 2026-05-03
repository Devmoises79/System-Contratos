// static/js/notificacao.js
// Sistema de Notificações em Tempo Real - Versão Corrigida

class SistemaNotificacoes {
    constructor() {
        this.eventSource = null;
        this.ultimoId = 0;
        this.somAtivado = true;
        this.init();
    }

    async init() {
        console.log('🔔 Inicializando sistema de notificações...');
        await this.carregarPreferencias();
        this.conectarSSE();
        this.iniciarPolling();
        this.atualizarBadge();
        
        // Atualizar badge a cada 30 segundos como fallback
        setInterval(() => this.atualizarBadge(), 30000);
    }

    async carregarPreferencias() {
        try {
            const response = await fetch('/notificacoes/preferencias/api');
            if (response.ok) {
                const data = await response.json();
                this.somAtivado = data.som_ativado === true || data.som_ativado === 1;
            }
        } catch(e) {
            console.log('Usando preferências padrão');
        }
        
        const toggle = document.getElementById('toggleSomNotificacoes');
        if (toggle) {
            toggle.checked = this.somAtivado;
            toggle.addEventListener('change', (e) => {
                this.somAtivado = e.target.checked;
                this.salvarPreferencias();
            });
        }
    }

    async salvarPreferencias() {
        try {
            const formData = new FormData();
            formData.append('som_ativado', this.somAtivado ? 'on' : 'off');
            await fetch('/notificacoes/preferencias', { method: 'POST', body: formData });
        } catch(e) {}
    }

    conectarSSE() {
        if (!window.EventSource) {
            console.log('⚠️ SSE não suportado, usando apenas polling');
            return;
        }

        try {
            if (this.eventSource) {
                this.eventSource.close();
            }

            this.eventSource = new EventSource('/notificacoes/stream');
            
            this.eventSource.onopen = () => {
                console.log('📡 Conexão SSE estabelecida');
                this.atualizarStatusConexao(true);
            };
            
            this.eventSource.onmessage = (event) => {
                try {
                    const dados = JSON.parse(event.data);
                    console.log('📨 Mensagem SSE recebida:', dados);
                    
                    if (dados.type === 'nova_notificacao') {
                        this.exibirNotificacao(dados);
                        this.atualizarBadge();
                    } else if (dados.type === 'initial' && dados.notificacoes) {
                        dados.notificacoes.forEach(notif => {
                            if (notif.id > this.ultimoId) {
                                this.ultimoId = notif.id;
                            }
                        });
                        this.atualizarBadge();
                    } else if (dados.id && dados.titulo) {
                        // Formato direto
                        this.exibirNotificacao(dados);
                        this.atualizarBadge();
                    }
                } catch(e) {
                    // Heartbeat ou dados inválidos
                    if (event.data && !event.data.startsWith(':')) {
                        console.log('Mensagem recebida:', event.data);
                    }
                }
            };
            
            this.eventSource.onerror = (error) => {
                console.log('⚠️ Erro no SSE, usando polling');
                this.atualizarStatusConexao(false);
                if (this.eventSource) {
                    this.eventSource.close();
                    this.eventSource = null;
                }
            };
        } catch(e) {
            console.log('Erro ao conectar SSE:', e);
        }
    }
    
    atualizarStatusConexao(conectado) {
        const statusIcon = document.getElementById('sse-status');
        if (statusIcon) {
            statusIcon.className = conectado ? 'fas fa-circle text-success sse-connected' : 'fas fa-circle text-danger sse-disconnected';
            statusIcon.title = conectado ? 'Conectado em tempo real' : 'Desconectado - usando polling';
        }
    }

    iniciarPolling() {
        // Polling a cada 10 segundos como fallback
        setInterval(async () => {
            if (!this.eventSource || this.eventSource.readyState !== EventSource.OPEN) {
                await this.verificarNovasNotificacoes();
            }
        }, 10000);
    }

    async verificarNovasNotificacoes() {
        try {
            const response = await fetch('/notificacoes/ultimas?limite=5');
            const data = await response.json();
            
            if (data.notificacoes && data.notificacoes.length > 0) {
                let maxId = this.ultimoId;
                
                for (const notif of data.notificacoes) {
                    if (notif.id > this.ultimoId) {
                        if (notif.id > maxId) maxId = notif.id;
                        if (!notif.lida) {
                            this.exibirNotificacao(notif);
                        }
                    }
                }
                
                this.ultimoId = maxId;
                this.atualizarBadge(data.nao_lidas);
            }
        } catch(e) {
            console.error('Erro no polling:', e);
        }
    }

    exibirNotificacao(notificacao) {
        console.log(`🔔 NOTIFICAÇÃO: ${notificacao.titulo} - ${notificacao.mensagem}`);
        
        // Tocar som
        if (this.somAtivado) {
            this.tocarSom(notificacao.tipo);
        }
        
        // Mostrar toast
        this.mostrarToast(notificacao);
        
        // Disparar evento para gamificação
        document.dispatchEvent(new CustomEvent('nova-notificacao-recebida', { 
            detail: notificacao 
        }));
    }

    tocarSom(tipo = 'info') {
        try {
            // Usar Web Audio API para beep
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Frequência diferente por tipo
            if (tipo === 'success') {
                oscillator.frequency.value = 880;
            } else if (tipo === 'warning') {
                oscillator.frequency.value = 660;
            } else {
                oscillator.frequency.value = 523.25;
            }
            
            gainNode.gain.value = 0.15;
            
            oscillator.start();
            gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.4);
            oscillator.stop(audioContext.currentTime + 0.4);
            
            setTimeout(() => audioContext.close(), 500);
        } catch(e) {
            console.log('Não foi possível tocar som');
        }
    }

    mostrarToast(notificacao) {
        // Criar container de toast se não existir
        let container = document.querySelector('.toast-container-custom');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container-custom position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1100';
            container.style.top = '70px';
            document.body.appendChild(container);
        }
        
        const cores = {
            success: '#10b981',
            danger: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        
        const icones = {
            success: 'fa-check-circle',
            danger: 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        
        const cor = cores[notificacao.tipo] || cores.info;
        const icone = icones[notificacao.tipo] || icones.info;
        
        const toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 6);
        const titulo = notificacao.titulo || 'Notificação';
        const mensagem = notificacao.mensagem || '';
        
        const toastHtml = `
            <div id="${toastId}" class="toast show mb-2" role="alert" style="background: white; border-left: 4px solid ${cor}; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); min-width: 300px; animation: slideInRight 0.3s ease;">
                <div class="d-flex">
                    <div class="toast-body py-3 px-3">
                        <div class="d-flex gap-3 align-items-center">
                            <div style="background: ${cor}20; width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                                <i class="fas ${icone}" style="color: ${cor}; font-size: 18px;"></i>
                            </div>
                            <div class="flex-grow-1">
                                <strong>${this.escapeHtml(titulo)}</strong>
                                <p class="mb-0 small" style="color: #4a5568;">${this.escapeHtml(mensagem)}</p>
                            </div>
                        </div>
                    </div>
                    <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = document.getElementById(toastId);
        
        if (toastElement && typeof bootstrap !== 'undefined') {
            const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
            toast.show();
            
            toastElement.addEventListener('hidden.bs.toast', () => {
                if (toastElement && toastElement.remove) toastElement.remove();
            });
        }
        
        // Auto-remover fallback
        setTimeout(() => {
            const el = document.getElementById(toastId);
            if (el && el.remove) el.remove();
        }, 5000);
    }

    async atualizarBadge(valor = null) {
        const badge = document.getElementById('notificacaoBadge');
        if (!badge) return;
        
        try {
            let total = valor;
            if (total === null) {
                const response = await fetch('/notificacoes/nao-lidas/count');
                if (!response.ok) throw new Error('Erro na requisição');
                const data = await response.json();
                total = data.total || 0;
            }
            
            if (total > 0) {
                badge.textContent = total > 99 ? '99+' : total;
                badge.style.display = 'inline-flex';
                badge.style.animation = 'pulse 0.5s ease';
                setTimeout(() => {
                    if (badge) badge.style.animation = '';
                }, 500);
            } else {
                badge.style.display = 'none';
            }
        } catch(e) {
            console.error('Erro ao atualizar badge:', e);
        }
    }

    async marcarComoLida(id) {
        try {
            const response = await fetch(`/notificacoes/${id}/marcar-lida`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                this.atualizarBadge();
                return true;
            }
        } catch(e) {
            console.error('Erro ao marcar como lida:', e);
        }
        return false;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicializar quando o DOM estiver pronto
let sistemaNotificacoes;

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Carregando sistema de notificações...');
    sistemaNotificacoes = new SistemaNotificacoes();
    window.sistemaNotificacoes = sistemaNotificacoes;
});