// static/js/gamificacao.js
// Sistema de Gamificação

class GamificacaoSystem {
    constructor() {
        this.init();
    }

    init() {
        console.log('🏆 Sistema de gamificação carregado');
        this.escutarNotificacoes();
    }

    escutarNotificacoes() {
        document.addEventListener('nova-notificacao-recebida', (e) => {
            const notificacao = e.detail;
            if (notificacao.tipo === 'success' && 
                notificacao.titulo && notificacao.titulo.includes('Conquista')) {
                this.efeitoConfete();
            }
        });
    }

    efeitoConfete() {
        const cores = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'];
        
        for (let i = 0; i < 30; i++) {
            setTimeout(() => {
                const confete = document.createElement('div');
                confete.style.position = 'fixed';
                confete.style.width = Math.random() * 8 + 4 + 'px';
                confete.style.height = Math.random() * 8 + 4 + 'px';
                confete.style.backgroundColor = cores[Math.floor(Math.random() * cores.length)];
                confete.style.borderRadius = Math.random() > 0.5 ? '50%' : '0';
                confete.style.left = Math.random() * window.innerWidth + 'px';
                confete.style.top = '-20px';
                confete.style.zIndex = '99999';
                confete.style.pointerEvents = 'none';
                confete.style.opacity = '0.8';
                confete.style.animation = `quedaConfete ${1 + Math.random() * 1.5}s ease-in forwards`;
                
                document.body.appendChild(confete);
                
                setTimeout(() => confete.remove(), 2000);
            }, i * 30);
        }
        
        if (!document.querySelector('#confete-styles')) {
            const style = document.createElement('style');
            style.id = 'confete-styles';
            style.textContent = `
                @keyframes quedaConfete {
                    0% { transform: translateY(0) rotate(0deg); opacity: 1; }
                    100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }
}

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    window.gamificacao = new GamificacaoSystem();
});