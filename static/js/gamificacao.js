/**
 * Gamificação - Sistema de Reconhecimento Positivo
 * JavaScript para efeitos visuais e notificações
 */

class GamificacaoSystem {
    constructor() {
        this.notificacoesPendentes = [];
        this.init();
    }

    init() {
        this.carregarNotificacoes();
        this.setupEventListeners();
        this.iniciarPolling();
    }

    carregarNotificacoes() {
        // Buscar notificações de conquistas não lidas
        fetch('/gamificacao/notificacoes/pendentes')
            .then(response => response.json())
            .then(data => {
                if (data.conquistas && data.conquistas.length > 0) {
                    data.conquistas.forEach(conquista => {
                        this.mostrarToastConquista(conquista);
                    });
                }
                if (data.nivel && data.nivel.subiu_nivel) {
                    this.mostrarToastNivel(data.nivel);
                }
            })
            .catch(error => console.log('Erro ao carregar notificações:', error));
    }

    mostrarToastConquista(conquista) {
        // Criar elemento do toast
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white border-0 position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.style.backgroundColor = conquista.cor || '#10b981';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <div class="d-flex align-items-center">
                        <div class="display-6 me-3">${conquista.icone || '🏆'}</div>
                        <div>
                            <strong>🏆 Nova Conquista!</strong><br>
                            ${conquista.nome}<br>
                            <small>+${conquista.pontos} pontos</small>
                        </div>
                    </div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Inicializar e mostrar toast
        const bsToast = new bootstrap.Toast(toast, { delay: 8000, autohide: true });
        bsToast.show();
        
        // Remover do DOM após fechar
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
        
        // Tocar som (opcional)
        this.tocarSom('conquista');
        
        // Atualizar contador de notificações
        this.atualizarContadorNotificacoes();
    }

    mostrarToastNivel(nivelData) {
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white border-0 position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.style.backgroundColor = '#6366f1';
        toast.setAttribute('role', 'alert');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <div class="d-flex align-items-center">
                        <div class="display-6 me-3">${nivelData.icone || '✨'}</div>
                        <div>
                            <strong>✨ Você subiu de nível!</strong><br>
                            Agora você é ${nivelData.titulo}<br>
                            <small>Continue assim! 🚀</small>
                        </div>
                    </div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { delay: 10000, autohide: true });
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
        
        this.tocarSom('levelup');
    }

    tocarSom(tipo) {
        // Verificar se o usuário habilitou sons
        const somAtivado = localStorage.getItem('gamificacao_som') !== 'false';
        if (!somAtivado) return;
        
        // Sons opcionais (você pode adicionar arquivos de áudio)
        const sons = {
            conquista: '/static/sounds/achievement.mp3',
            levelup: '/static/sounds/levelup.mp3'
        };
        
        if (sons[tipo]) {
            const audio = new Audio(sons[tipo]);
            audio.volume = 0.3;
            audio.play().catch(e => console.log('Som não disponível'));
        }
    }

    setupEventListeners() {
        // Botão para ativar/desativar sons
        const soundToggle = document.getElementById('toggle-som-gamificacao');
        if (soundToggle) {
            soundToggle.addEventListener('click', () => {
                const ativado = localStorage.getItem('gamificacao_som') !== 'false';
                localStorage.setItem('gamificacao_som', ativado ? 'false' : 'true');
                soundToggle.innerHTML = ativado ? '<i class="bi bi-volume-mute"></i>' : '<i class="bi bi-volume-up"></i>';
            });
        }
    }

    iniciarPolling() {
        // Polling a cada 30 segundos para novas conquistas
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.carregarNotificacoes();
            }
        }, 30000);
    }

    atualizarContadorNotificacoes() {
        // Atualizar o badge do sininho
        fetch('/notificacoes/nao-lidas/count')
            .then(response => response.json())
            .then(data => {
                const badge = document.querySelector('.notification-badge');
                if (badge) {
                    if (data.total > 0) {
                        badge.textContent = data.total;
                        badge.style.display = 'inline-block';
                    } else {
                        badge.style.display = 'none';
                    }
                }
            })
            .catch(error => console.log('Erro ao atualizar contador:', error));
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.gamificacao = new GamificacaoSystem();
});